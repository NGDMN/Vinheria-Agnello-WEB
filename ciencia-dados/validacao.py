"""
Vinheria Agnello - PBL Fase 3
Validação das tabelas: regras, mensagens claras, parada controlada e relatório.

Cada regra recebe um código (ex.: B03) formado pelo grupo + número sequencial:
    E esquema | N nulos | U unicidade | D domínio | F faixa | R referencial
    B negócio | K cálculo | V vazamento | A calibração

Severidade:
    CRÍTICA -> reprova a validação; o pipeline não grava a saída
    ALERTA  -> registrada no relatório, não interrompe
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import parametros as cfg

CRITICA = "CRÍTICA"
ALERTA = "ALERTA"

NOMES_GRUPOS = {
    "E": "Esquema", "N": "Nulos", "U": "Unicidade", "D": "Domínio", "F": "Faixa",
    "R": "Referencial", "B": "Negócio", "K": "Cálculo", "V": "Vazamento", "A": "Calibração",
}

MAX_EXEMPLOS = 5


def _formatar_exemplo(valor):
    """Mostra ids como inteiros (4 em vez de 4.0) e datas sem horário."""
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, pd.Timestamp):
        return valor.date()
    if isinstance(valor, tuple):
        return tuple(_formatar_exemplo(x) for x in valor)
    return valor


class ErroValidacao(Exception):
    """Validação reprovada: pelo menos uma regra crítica falhou."""


@dataclass
class ResultadoRegra:
    codigo: str
    grupo: str
    descricao: str
    severidade: str
    ocorrencias: int
    exemplos: list = field(default_factory=list)

    @property
    def passou(self) -> bool:
        return self.ocorrencias == 0

    @property
    def status(self) -> str:
        if self.passou:
            return "OK"
        return "FALHA" if self.severidade == CRITICA else "ALERTA"

    def linha(self) -> str:
        texto = f"[{self.status:<6}] {self.codigo} {NOMES_GRUPOS[self.grupo]:<11} | {self.descricao}"
        if not self.passou:
            texto += f" -> {self.ocorrencias} ocorrência(s)"
            if self.exemplos:
                texto += f"; exemplos: {', '.join(str(e) for e in self.exemplos)}"
        return texto


class Validador:
    """Acumula os resultados de uma etapa de validação."""

    def __init__(self, etapa: str, interromper: bool = True):
        self.etapa = etapa
        self.interromper = interromper
        self.resultados: list[ResultadoRegra] = []
        self._contador = defaultdict(int)

    # ------------------------------------------------------------------ núcleo
    def registrar(self, grupo: str, descricao: str, ocorrencias: int,
                  exemplos=None, severidade: str = CRITICA) -> ResultadoRegra:
        self._contador[grupo] += 1
        resultado = ResultadoRegra(
            codigo=f"{grupo}{self._contador[grupo]:02d}",
            grupo=grupo,
            descricao=descricao,
            severidade=severidade,
            ocorrencias=int(ocorrencias),
            exemplos=[_formatar_exemplo(e) for e in list(exemplos or [])[:MAX_EXEMPLOS]],
        )
        self.resultados.append(resultado)
        return resultado

    def verificar(self, grupo: str, descricao: str, df: pd.DataFrame, violacoes: pd.Series,
                  coluna_id: str | None = None, severidade: str = CRITICA) -> ResultadoRegra:
        """violacoes: série booleana alinhada ao df (True = linha viola a regra)."""
        violacoes = violacoes.fillna(False).astype(bool)
        exemplos = (df.loc[violacoes, coluna_id] if coluna_id else df.index[violacoes]).tolist()
        return self.registrar(grupo, descricao, violacoes.sum(), exemplos, severidade)

    # ---------------------------------------------------------------- atalhos
    def colunas_obrigatorias(self, tabela: str, df: pd.DataFrame) -> bool:
        faltando = [c for c in cfg.COLUNAS[tabela] if c not in df.columns]
        self.registrar("E", f"{tabela}: colunas obrigatórias presentes", len(faltando), faltando)
        return not faltando

    def sem_nulos(self, tabela: str, df: pd.DataFrame, coluna_id: str | None = None) -> None:
        anulaveis = cfg.COLUNAS_ANULAVEIS.get(tabela, set())
        for coluna in cfg.COLUNAS[tabela]:
            if coluna not in anulaveis:
                self.verificar("N", f"{tabela}.{coluna} sem valores vazios",
                               df, df[coluna].isna(), coluna_id)

    def chave_unica(self, tabela: str, df: pd.DataFrame) -> None:
        chaves = cfg.CHAVES[tabela]
        duplicados = df.duplicated(subset=chaves, keep=False)
        exemplos = df.loc[duplicados, chaves].drop_duplicates().head(MAX_EXEMPLOS)
        self.registrar("U", f"{tabela}: chave ({', '.join(chaves)}) sem duplicidade",
                       duplicados.sum(), [tuple(x) if len(x) > 1 else x[0] for x in exemplos.values])

    def dominio(self, tabela: str, df: pd.DataFrame, coluna: str,
                coluna_id: str | None = None, valores=None) -> None:
        valores = valores if valores is not None else cfg.DOMINIOS[coluna]
        fora = df[coluna].notna() & ~df[coluna].isin(valores)
        self.verificar("D", f"{tabela}.{coluna} dentro dos valores aceitos", df, fora, coluna_id)

    def faixa(self, tabela: str, df: pd.DataFrame, coluna: str, minimo=None, maximo=None,
              coluna_id: str | None = None, minimo_exclusivo: bool = False) -> None:
        serie = df[coluna]
        fora = pd.Series(False, index=df.index)
        partes = []
        if minimo is not None:
            fora |= (serie <= minimo) if minimo_exclusivo else (serie < minimo)
            partes.append(f"{'>' if minimo_exclusivo else '>='} {_formatar_exemplo(minimo)}")
        if maximo is not None:
            fora |= serie > maximo
            partes.append(f"<= {_formatar_exemplo(maximo)}")
        self.verificar("F", f"{tabela}.{coluna} {' e '.join(partes)}",
                       df, fora & serie.notna(), coluna_id)

    def referencia(self, tabela: str, df: pd.DataFrame, coluna: str,
                   tabela_ref: str, df_ref: pd.DataFrame, coluna_ref: str | None = None) -> None:
        coluna_ref = coluna_ref or coluna
        orfaos = ~df[coluna].isin(df_ref[coluna_ref])
        self.verificar("R", f"{tabela}.{coluna} existe em {tabela_ref}.{coluna_ref}",
                       df, orfaos, coluna)

    # --------------------------------------------------------------- resumo
    @property
    def falhas_criticas(self) -> list[ResultadoRegra]:
        return [r for r in self.resultados if r.status == "FALHA"]

    @property
    def alertas(self) -> list[ResultadoRegra]:
        return [r for r in self.resultados if r.status == "ALERTA"]

    @property
    def aprovada(self) -> bool:
        return not self.falhas_criticas

    def resumo(self) -> str:
        ok = sum(r.passou for r in self.resultados)
        return (f"{len(self.resultados)} regras | {ok} OK | "
                f"{len(self.falhas_criticas)} falha(s) crítica(s) | {len(self.alertas)} alerta(s)")

    def linhas_relatorio(self) -> list[str]:
        situacao = "APROVADA" if self.aprovada else "REPROVADA"
        if not self.interromper:
            situacao = "DIAGNÓSTICO (não interrompe)"
        linhas = [f"== Validação: {self.etapa} — {situacao}", f"   {self.resumo()}", ""]
        linhas += [f"   {r.linha()}" for r in self.resultados]
        return linhas + [""]

    def finalizar(self) -> "Validador":
        """Imprime o resultado e interrompe o pipeline se houver falha crítica."""
        print(f"\nValidação: {self.etapa} -> {self.resumo()}")
        for r in self.falhas_criticas + self.alertas:
            print(f"   {r.linha()}")
        if self.interromper and self.falhas_criticas:
            raise ErroValidacao(
                f"Validação '{self.etapa}' reprovada: {len(self.falhas_criticas)} regra(s) crítica(s) "
                f"falharam. Veja os detalhes acima e em {cfg.CAMINHO_RELATORIO.name}."
            )
        return self


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def _datas(serie: pd.Series) -> pd.Series:
    return pd.to_datetime(serie, errors="coerce")


def _diferente(a: pd.Series, b: pd.Series, tolerancia: float | None = None) -> pd.Series:
    """Compara duas séries tratando vazio = vazio como igual."""
    ambos_vazios = a.isna() & b.isna()
    if tolerancia is not None:
        diferente = (pd.to_numeric(a, errors="coerce") - pd.to_numeric(b, errors="coerce")).abs() > tolerancia
        diferente |= a.isna() ^ b.isna()
    else:
        diferente = a.astype(object).ne(b.astype(object))
    return diferente & ~ambos_vazios


# =============================================================================
# CATÁLOGO
# =============================================================================

def validar_catalogo(produtos: pd.DataFrame, interromper: bool = True) -> Validador:
    v = Validador("Catálogo (produtos)", interromper)
    if v.colunas_obrigatorias("produtos", produtos):
        v.registrar("E", "produtos: catálogo com pelo menos 1 vinho", int(produtos.empty))
        v.sem_nulos("produtos", produtos, "id_produto")
        v.chave_unica("produtos", produtos)
        v.dominio("produtos", produtos, "tipo_vinho", "id_produto")
        v.faixa("produtos", produtos, "preco_unitario", minimo=0, minimo_exclusivo=True,
                coluna_id="id_produto")
    return v.finalizar()


# =============================================================================
# BASE COMPLETA
# =============================================================================

def validar_base(tabelas: dict, etapa: str, interromper: bool = True) -> Validador:
    """Valida as tabelas transacionais e, se presente, a base_ml."""
    v = Validador(etapa, interromper)

    presentes = {nome: df for nome, df in tabelas.items() if nome in cfg.COLUNAS}
    esquema_ok = {nome: v.colunas_obrigatorias(nome, df) for nome, df in presentes.items()}
    if not all(esquema_ok.values()):
        return v.finalizar()   # sem as colunas, as demais regras não fazem sentido

    tipadas = {nome: _validar_tipos(v, nome, df) for nome, df in presentes.items()}
    clientes = tipadas["clientes"]
    produtos = tipadas["produtos"]
    rupturas = tipadas["rupturas_estoque"]
    pedidos = tipadas["pedidos"]
    itens = tipadas["produtos_pedidos"]
    base_ml = tipadas.get("base_ml")

    _validar_estrutura(v, clientes, produtos, rupturas, pedidos, itens)
    _validar_faixas(v, clientes, produtos, rupturas, pedidos, itens)
    _validar_referencias(v, clientes, produtos, rupturas, pedidos, itens)
    _validar_negocio(v, clientes, produtos, rupturas, pedidos, itens)
    _validar_calculos(v, produtos, pedidos, itens)
    if base_ml is not None:
        _validar_base_ml(v, base_ml, pedidos, clientes, itens)
    _validar_calibracao(v, clientes, pedidos)
    return v.finalizar()


def _validar_tipos(v: Validador, tabela: str, df: pd.DataFrame) -> pd.DataFrame:
    """Converte cópias para o tipo esperado; valor que não converte é registrado como violação.
    Assim as demais regras rodam mesmo sobre uma base bruta suja, sem quebrar o pipeline."""
    df = df.copy()
    coluna_id = cfg.CHAVES.get(tabela, [None])[0]
    for coluna in cfg.TIPOS_DATA.get(tabela, []):
        convertido = _datas(df[coluna])
        v.verificar("E", f"{tabela}.{coluna} é data válida", df,
                    df[coluna].notna() & convertido.isna(), coluna_id)
        df[coluna] = convertido
    numericas = (cfg.TIPOS_INTEIROS.get(tabela, []) + cfg.TIPOS_MONETARIOS.get(tabela, [])
                 + cfg.TIPOS_DECIMAIS.get(tabela, []))
    for coluna in numericas:
        convertido = pd.to_numeric(df[coluna].astype(object), errors="coerce").astype(float)
        v.verificar("E", f"{tabela}.{coluna} é numérico", df,
                    df[coluna].notna() & convertido.isna(), coluna_id)
        df[coluna] = convertido
    for coluna in cfg.TIPOS_INTEIROS.get(tabela, []):
        nao_inteiro = df[coluna].notna() & (df[coluna] % 1 != 0)
        v.verificar("E", f"{tabela}.{coluna} é inteiro", df, nao_inteiro, coluna_id)
    return df


def _validar_estrutura(v, clientes, produtos, rupturas, pedidos, itens):
    v.sem_nulos("clientes", clientes, "id_cliente")
    v.sem_nulos("produtos", produtos, "id_produto")
    v.sem_nulos("pedidos", pedidos, "id_pedido")
    v.sem_nulos("produtos_pedidos", itens, "id_pedido")
    v.verificar("N", "rupturas_estoque sem valores vazios", rupturas, rupturas.isna().any(axis=1))

    for tabela, df in [("clientes", clientes), ("produtos", produtos),
                       ("pedidos", pedidos), ("produtos_pedidos", itens)]:
        v.chave_unica(tabela, df)

    v.dominio("clientes", clientes, "tipo_cliente", "id_cliente")
    v.dominio("clientes", clientes, "uf", "id_cliente")
    v.dominio("produtos", produtos, "tipo_vinho", "id_produto")
    v.dominio("rupturas_estoque", rupturas, "tipo_ruptura")
    for coluna in ["canal", "uf_destino", "tipo_frete", "forma_pagamento", "pct_desconto",
                   "status_pedido", "status_entrega", "motivo_insucesso"]:
        v.dominio("pedidos", pedidos, coluna, "id_pedido")
    v.dominio("pedidos", pedidos, "venda_sucesso", "id_pedido", valores={0, 1})


def _validar_faixas(v, clientes, produtos, rupturas, pedidos, itens):
    inicio, fim = pd.Timestamp(cfg.DATA_INICIO), pd.Timestamp(cfg.DATA_FIM)
    v.faixa("clientes", clientes, "data_cadastro",
            pd.Timestamp(cfg.DATA_CADASTRO_MIN), fim, "id_cliente")
    v.faixa("produtos", produtos, "preco_unitario", 0, coluna_id="id_produto", minimo_exclusivo=True)
    v.faixa("rupturas_estoque", rupturas, "data_inicio", inicio, fim)
    v.faixa("rupturas_estoque", rupturas, "data_fim", inicio, fim)
    v.faixa("pedidos", pedidos, "data_pedido", inicio, fim, "id_pedido")
    v.faixa("pedidos", pedidos, "valor_total", 0, coluna_id="id_pedido", minimo_exclusivo=True)
    v.faixa("pedidos", pedidos, "valor_frete", 0, coluna_id="id_pedido")
    v.faixa("pedidos", pedidos, "prazo_entrega_dias", 0, cfg.PRAZO_MAXIMO_DIAS, "id_pedido")
    v.faixa("produtos_pedidos", itens, "quantidade", 1, coluna_id="id_pedido")
    v.faixa("produtos_pedidos", itens, "preco_unitario", 0, coluna_id="id_pedido", minimo_exclusivo=True)


def _validar_referencias(v, clientes, produtos, rupturas, pedidos, itens):
    v.referencia("pedidos", pedidos, "id_cliente", "clientes", clientes)
    v.referencia("produtos_pedidos", itens, "id_pedido", "pedidos", pedidos)
    v.referencia("produtos_pedidos", itens, "id_produto", "produtos", produtos)
    v.referencia("rupturas_estoque", rupturas, "id_produto", "produtos", produtos)
    sem_itens = ~pedidos["id_pedido"].isin(itens["id_pedido"])
    v.verificar("R", "pedidos: todo pedido tem pelo menos 1 item", pedidos, sem_itens, "id_pedido")


def _validar_negocio(v, clientes, produtos, rupturas, pedidos, itens):
    p = pedidos.merge(clientes[["id_cliente", "uf", "data_cadastro"]], on="id_cliente", how="left")
    p["regiao"] = p["uf_destino"].map(lambda uf: cfg.UFS.get(uf, (None,))[0])
    p["grupo"] = p["regiao"].map(cfg.GRUPO_LOGISTICO)

    v.verificar("B", "Pedido feito após o cadastro do cliente",
                p, p["data_pedido"] < p["data_cadastro"], "id_pedido")
    v.verificar("B", "UF de destino igual à UF do cliente",
                p, p["uf_destino"] != p["uf"], "id_pedido")
    v.verificar("B", "Same-Day apenas em Sul/Sudeste",
                p, (p["tipo_frete"] == "Same-Day") & ~p["regiao"].isin(cfg.REGIOES_SAME_DAY), "id_pedido")
    v.verificar("B", f"Retirada apenas para clientes de {cfg.UF_LOJA} (UF da loja)",
                p, (p["tipo_frete"] == "Retirada") & (p["uf_destino"] != cfg.UF_LOJA), "id_pedido")
    v.verificar("B", "Retirada sem custo de frete",
                p, (p["tipo_frete"] == "Retirada") & (p["valor_frete"] != 0), "id_pedido")
    v.verificar("B", "Expresso e Same-Day sempre com frete cobrado",
                p, p["tipo_frete"].isin(["Expresso", "Same-Day"]) & (p["valor_frete"] <= 0), "id_pedido")

    elegivel_gratis = ((p["tipo_frete"] == "Econômico")
                       & p["regiao"].isin(cfg.REGIOES_FRETE_GRATIS)
                       & (p["valor_total"] >= cfg.VALOR_MIN_FRETE_GRATIS))
    gratis = (p["tipo_frete"] == "Econômico") & (p["valor_frete"] == 0)
    v.verificar("B", f"Frete grátis só no Econômico em Sul/Sudeste a partir de "
                     f"R$ {cfg.VALOR_MIN_FRETE_GRATIS:.2f}, e sempre que elegível",
                p, gratis != elegivel_gratis, "id_pedido")

    pico = p["data_pedido"].map(lambda d: cfg.eh_periodo_pico(d.date()) if pd.notna(d) else False)

    def fora_do_prazo(linha) -> bool:
        faixa = cfg.PRAZO_DIAS.get((linha["tipo_frete"], linha["grupo"]))
        if faixa is None:
            return True
        acrescimo = cfg.ACRESCIMO_PRAZO_PICO.get(linha["tipo_frete"], 0) if linha["pico"] else 0
        return not (faixa[0] + acrescimo <= linha["prazo_entrega_dias"] <= faixa[1] + acrescimo)

    p["pico"] = pico
    v.verificar("B", "Prazo dentro da faixa do modal, da região e da época",
                p, p.apply(fora_do_prazo, axis=1), "id_pedido")

    status_esperado = p["venda_sucesso"].map({1: "Pago", 0: "Não pago"}).fillna("Aguardando pagamento")
    v.verificar("B", "status_pedido coerente com venda_sucesso",
                p, p["status_pedido"] != status_esperado, "id_pedido")
    v.verificar("B", "Motivo de insucesso preenchido se, e somente se, a venda não foi paga",
                p, p["motivo_insucesso"].notna() != (p["venda_sucesso"] == 0), "id_pedido")
    motivo_permitido = p.apply(
        lambda x: pd.isna(x["motivo_insucesso"])
        or x["motivo_insucesso"] in {cfg.MOTIVO_POR_PAGAMENTO.get(x["forma_pagamento"]), "Desistência"},
        axis=1,
    )
    v.verificar("B", "Motivo de insucesso coerente com a forma de pagamento",
                p, ~motivo_permitido, "id_pedido")

    andamento = p["data_pedido"].map(lambda d: cfg.eh_mes_em_andamento(d.date()) if pd.notna(d) else False)
    v.verificar("B", "Aguardando pagamento apenas no mês em andamento",
                p, p["venda_sucesso"].isna() & ~andamento, "id_pedido")
    v.verificar("B", "Status de entrega preenchido se, e somente se, a venda foi paga",
                p, p["status_entrega"].notna() != (p["venda_sucesso"] == 1), "id_pedido")
    v.verificar("B", "Em trânsito apenas no mês em andamento",
                p, (p["status_entrega"] == "Em trânsito") & ~andamento, "id_pedido")

    v.verificar("B", "Ruptura com data final igual ou posterior à inicial",
                rupturas, rupturas["data_fim"] < rupturas["data_inicio"])
    r = rupturas.sort_values(["id_produto", "data_inicio"])
    sobreposta = (r["id_produto"] == r["id_produto"].shift()) & (r["data_inicio"] <= r["data_fim"].shift())
    v.verificar("B", "Janelas de ruptura sem sobreposição no mesmo produto", r, sobreposta, "id_produto")

    vendas = itens.merge(pedidos[["id_pedido", "data_pedido"]], on="id_pedido")
    cruzamento = vendas.merge(rupturas, on="id_produto")
    em_ruptura = cruzamento[(cruzamento["data_pedido"] >= cruzamento["data_inicio"])
                            & (cruzamento["data_pedido"] <= cruzamento["data_fim"])]
    v.registrar("B", "Nenhuma venda de produto em período de ruptura",
                len(em_ruptura), em_ruptura["id_pedido"].tolist())


def _validar_calculos(v, produtos, pedidos, itens):
    subtotal = (itens["quantidade"] * itens["preco_unitario"]).groupby(itens["id_pedido"]).sum()
    p = pedidos.set_index("id_pedido")
    esperado = (subtotal.reindex(p.index) * (1 - p["pct_desconto"] / 100)).round(2)
    divergente = (p["valor_total"] - esperado).abs() > cfg.TOLERANCIA_VALOR
    v.registrar("K", "valor_total = soma dos itens x (1 - desconto)",
                divergente.sum(), p.index[divergente].tolist())


def _validar_base_ml(v, base_ml, pedidos, clientes, itens):
    validar_estrutura_base_ml(v, base_ml)

    b = base_ml

    v.registrar("R", "base_ml contém exatamente os pedidos da tabela pedidos",
                len(set(b["id_pedido"]) ^ set(pedidos["id_pedido"])),
                sorted(set(b["id_pedido"]) ^ set(pedidos["id_pedido"])))

    m = b.merge(pedidos, on="id_pedido", how="inner", suffixes=("", "_ped"))
    for coluna in ["data_pedido", "canal", "uf_destino", "tipo_frete", "forma_pagamento",
                   "pct_desconto", "prazo_entrega_dias", "motivo_insucesso"]:
        v.verificar("K", f"base_ml.{coluna} igual a pedidos.{coluna}",
                    m, _diferente(m[coluna], m[f"{coluna}_ped"]), "id_pedido")
    for coluna in ["valor_total", "valor_frete", "venda_sucesso"]:
        v.verificar("K", f"base_ml.{coluna} igual a pedidos.{coluna}",
                    m, _diferente(m[coluna], m[f"{coluna}_ped"], cfg.TOLERANCIA_VALOR), "id_pedido")

    m = m.merge(clientes[["id_cliente", "tipo_cliente"]], on="id_cliente", how="left",
                suffixes=("", "_cli"))
    v.verificar("K", "base_ml.tipo_cliente igual ao cadastro do cliente",
                m, m["tipo_cliente"] != m["tipo_cliente_cli"], "id_pedido")
    v.verificar("K", "base_ml.regiao corresponde à UF de destino",
                m, m["regiao"] != m["uf_destino"].map(lambda uf: cfg.UFS.get(uf, (None,))[0]), "id_pedido")
    v.verificar("K", "base_ml.mes e quinzena derivados de data_pedido",
                m, (m["mes"] != m["data_pedido"].dt.month)
                | (m["quinzena"] != np.where(m["data_pedido"].dt.day <= 15, 1, 2)), "id_pedido")
    qtd = itens.groupby("id_pedido").size()
    v.verificar("K", "base_ml.qtd_itens igual ao número de itens do pedido",
                m, m["qtd_itens"] != m["id_pedido"].map(qtd), "id_pedido")

    # Recalcula histórico do cliente por um caminho independente da derivação
    h = m.sort_values(["data_pedido", "id_pedido"]).copy()
    h["pago"] = (h["venda_sucesso"] == 1).astype(int)
    h["anteriores_esperado"] = h.groupby("id_cliente")["pago"].transform(
        lambda s: s.cumsum().shift(fill_value=0))
    ultimo_pago = h["valor_total"].where(h["pago"] == 1)
    h["ultimo_pago"] = ultimo_pago.groupby(h["id_cliente"]).transform(lambda s: s.shift().ffill())
    h["variacao_esperada"] = ((h["valor_total"] / h["ultimo_pago"] - 1) * 100).round(2)
    v.verificar("K", "pedidos_anteriores = pedidos pagos do cliente antes deste",
                h, h["pedidos_anteriores"] != h["anteriores_esperado"], "id_pedido")
    v.verificar("K", "variacao_pedido_anterior_pct = variação sobre o último pedido pago",
                h, _diferente(h["variacao_pedido_anterior_pct"], h["variacao_esperada"], 0.01), "id_pedido")


def validar_estrutura_base_ml(v: Validador, base_ml: pd.DataFrame) -> None:
    """Regras da base_ml que não dependem das outras tabelas (reutilizadas pelo modelo)."""
    v.sem_nulos("base_ml", base_ml, "id_pedido")
    v.chave_unica("base_ml", base_ml)
    for coluna in ["canal", "tipo_cliente", "uf_destino", "regiao", "tipo_frete",
                   "forma_pagamento", "pct_desconto", "motivo_insucesso"]:
        v.dominio("base_ml", base_ml, coluna, "id_pedido")
    v.dominio("base_ml", base_ml, cfg.ROTULO, "id_pedido", valores={0, 1})
    v.dominio("base_ml", base_ml, "quinzena", "id_pedido", valores={1, 2})
    v.faixa("base_ml", base_ml, "mes", 1, 12, "id_pedido")
    v.faixa("base_ml", base_ml, "pedidos_anteriores", 0, coluna_id="id_pedido")
    v.faixa("base_ml", base_ml, "qtd_itens", 1, coluna_id="id_pedido")
    v.faixa("base_ml", base_ml, "variacao_pedido_anterior_pct", -100, coluna_id="id_pedido",
            minimo_exclusivo=True)

    vazamento = sorted(set(cfg.COLUNAS_ENTRADA_MODELO) & cfg.COLUNAS_PROIBIDAS_MODELO)
    v.registrar("V", "Entradas do modelo sem colunas posteriores ao checkout ou identificadores",
                len(vazamento), vazamento)
    ausentes = [c for c in cfg.COLUNAS_ENTRADA_MODELO if c not in base_ml.columns]
    v.registrar("V", "Todas as entradas do modelo existem na base_ml", len(ausentes), ausentes)


def validar_base_ml(base_ml: pd.DataFrame, interromper: bool = True) -> Validador:
    """Validação isolada da base_ml, para uso antes de treinar o modelo."""
    v = Validador("Base para o modelo (base_ml)", interromper)
    if v.colunas_obrigatorias("base_ml", base_ml):
        validar_estrutura_base_ml(v, _validar_tipos(v, "base_ml", base_ml))
    return v.finalizar()


def _validar_calibracao(v, clientes, pedidos):
    fechados = pedidos["venda_sucesso"].dropna()
    conversao = fechados.mean() if len(fechados) else 0
    minimo, maximo = cfg.FAIXA_CONVERSAO_ESPERADA
    v.registrar("A", f"Conversão geral entre {minimo:.0%} e {maximo:.0%} (atual: {conversao:.1%})",
                int(not minimo <= conversao <= maximo), severidade=ALERTA)

    minoritaria = min(fechados.mean(), 1 - fechados.mean()) if len(fechados) else 0
    v.registrar("A", f"Classe minoritária com pelo menos {cfg.PROPORCAO_MINIMA_CLASSE:.0%} "
                     f"(atual: {minoritaria:.1%})",
                int(minoritaria < cfg.PROPORCAO_MINIMA_CLASSE), severidade=ALERTA)

    pct_pj = (clientes["tipo_cliente"] == "PJ").mean()
    minimo, maximo = cfg.FAIXA_PCT_PJ_CLIENTES
    v.registrar("A", f"Clientes PJ entre {minimo:.0%} e {maximo:.0%} (atual: {pct_pj:.1%})",
                int(not minimo <= pct_pj <= maximo), severidade=ALERTA)

    mes = pedidos["data_pedido"].dt.to_period("M")
    por_mes = pedidos.groupby(mes).size()
    andamento = pd.Period(f"{cfg.MES_EM_ANDAMENTO[0]}-{cfg.MES_EM_ANDAMENTO[1]:02d}", "M")
    completos = por_mes.drop(andamento, errors="ignore")
    fora = completos[(completos < cfg.PEDIDOS_MES_MIN) | (completos > cfg.PEDIDOS_MES_MAX)]
    v.registrar("A", f"Volume mensal entre {cfg.PEDIDOS_MES_MIN} e {cfg.PEDIDOS_MES_MAX} "
                     f"pedidos (meses completos)",
                len(fora), [str(m) for m in fora.index], severidade=ALERTA)


# =============================================================================
# RELATÓRIO
# =============================================================================

def escrever_relatorio(caminho: Path, metadados: dict, log_tratamento: list[str],
                       validadores: list[Validador]) -> None:
    aprovado = all(v.aprovada for v in validadores if v.interromper)
    linhas = [
        "RELATÓRIO DE VALIDAÇÃO — Vinheria Agnello (PBL Fase 3)",
        "=" * 72,
        f"Gerado em: {datetime.now():%d/%m/%Y %H:%M:%S}",
    ]
    linhas += [f"{chave}: {valor}" for chave, valor in metadados.items()]
    linhas += [
        f"RESULTADO FINAL: {'APROVADO — base gravada' if aprovado else 'REPROVADO — base NÃO gravada'}",
        "",
        "Legenda: [OK] regra atendida | [FALHA] regra crítica violada (interrompe) | "
        "[ALERTA] fora do esperado (não interrompe)",
        "Grupos: " + " | ".join(f"{k} {n}" for k, n in NOMES_GRUPOS.items()),
        "",
        "== Tratamento aplicado",
    ]
    linhas += [f"   {item}" for item in log_tratamento] or ["   (nenhum)"]
    linhas.append("")
    for v in validadores:
        linhas += v.linhas_relatorio()

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(linhas), encoding="utf-8")