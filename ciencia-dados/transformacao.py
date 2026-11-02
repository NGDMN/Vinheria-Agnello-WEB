"""
Vinheria Agnello - PBL Fase 3
Transformação: tratamento das tabelas e derivação da base_ml.

O tratamento é aplicado como se a base fosse real (sistemas de origem com
erro de digitação, duplicidade, tipos inconsistentes e valores fora de faixa).
Cada passo registra quantas linhas alterou ou removeu, para o relatório.

A validação da base BRUTA roda antes do tratamento, em modo diagnóstico:
assim, um erro do gerador aparece no relatório mesmo que o tratamento o corrija.
"""

import unicodedata

import numpy as np
import pandas as pd

import parametros as cfg

VALORES_VERDADEIROS = {"1", "true", "verdadeiro", "sim", "s", "yes", "y"}

class ErroEntrada(Exception):
    """Arquivo de entrada com estrutura inválida (ex.: colunas ausentes no catálogo)."""


class LogTratamento:
    def __init__(self):
        self.itens: list[str] = []

    def registrar(self, tabela: str, acao: str, linhas: int) -> None:
        self.itens.append(f"{tabela:<17} | {acao:<62} | {linhas} linha(s)")

    def imprimir(self) -> None:
        alteracoes = [i for i in self.itens if not i.endswith("| 0 linha(s)")]
        print(f"\nTratamento: {len(self.itens)} passos, {len(alteracoes)} com alteração")
        for item in alteracoes:
            print(f"   {item}")


# =============================================================================
# AUXILIARES
# =============================================================================

def _chave_texto(valor) -> str:
    """Normaliza para comparação: sem acento, sem espaços extras, minúsculo."""
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return " ".join(texto.split()).casefold()


def _limpar_textos(df: pd.DataFrame, tabela: str, log: LogTratamento) -> pd.DataFrame:
    alteradas = 0
    for coluna in df.select_dtypes(include=["object", "string"]).columns:
        original = df[coluna]
        limpo = original.map(lambda x: " ".join(x.split()) if isinstance(x, str) else x)
        limpo = limpo.replace("", np.nan)
        alteradas += int((original.astype(object).ne(limpo.astype(object))
                          & ~(original.isna() & limpo.isna())).sum())
        df[coluna] = limpo
    log.registrar(tabela, "Espaços extras removidos e textos vazios convertidos em nulo", alteradas)
    return df


def _padronizar_categorias(df: pd.DataFrame, tabela: str, log: LogTratamento) -> pd.DataFrame:
    """Converte variações de escrita para o valor canônico ('pix' -> 'PIX', 'Economico' -> 'Econômico')."""
    for coluna in df.columns:
        dominio = cfg.DOMINIOS.get(coluna)
        if not dominio or not all(isinstance(x, str) for x in dominio):
            continue
        canonico = {_chave_texto(x): x for x in dominio}
        original = df[coluna]
        padronizado = original.map(lambda x: canonico.get(_chave_texto(x), x) if isinstance(x, str) else x)
        mudou = original.astype(object).ne(padronizado.astype(object)) & ~(original.isna() & padronizado.isna())
        df[coluna] = padronizado
        alteradas = int(mudou.sum())
        log.registrar(tabela, f"{coluna}: escrita padronizada para o valor canônico", alteradas)
    return df


def _converter_tipos(df: pd.DataFrame, tabela: str, log: LogTratamento) -> pd.DataFrame:
    for coluna in cfg.TIPOS_DATA.get(tabela, []):
        antes = df[coluna].notna()
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce", dayfirst=False).dt.date
        log.registrar(tabela, f"{coluna}: datas inválidas convertidas em nulo",
                      int((antes & df[coluna].isna()).sum()))

    numericas = (cfg.TIPOS_INTEIROS.get(tabela, []) + cfg.TIPOS_MONETARIOS.get(tabela, [])
                 + cfg.TIPOS_DECIMAIS.get(tabela, []))
    for coluna in numericas:
        antes = df[coluna].notna()
        texto = df[coluna].astype(str).str.replace(",", ".", regex=False)
        df[coluna] = pd.to_numeric(texto.where(antes), errors="coerce")
        log.registrar(tabela, f"{coluna}: valores não numéricos convertidos em nulo",
                      int((antes & df[coluna].isna()).sum()))

    for coluna in cfg.TIPOS_MONETARIOS.get(tabela, []):
        arredondado = df[coluna].round(2)
        log.registrar(tabela, f"{coluna}: arredondado para 2 casas",
                      int(((df[coluna] - arredondado).abs() > 1e-9).sum()))
        df[coluna] = arredondado
    return df


def _remover(df: pd.DataFrame, mascara: pd.Series, tabela: str, acao: str,
             log: LogTratamento) -> pd.DataFrame:
    mascara = mascara.fillna(False).astype(bool)
    log.registrar(tabela, acao, int(mascara.sum()))
    return df.loc[~mascara].copy()


def _remover_duplicados(df: pd.DataFrame, tabela: str, log: LogTratamento) -> pd.DataFrame:
    df = _remover(df, df.duplicated(keep="first"), tabela, "Linhas idênticas duplicadas removidas", log)
    chaves = cfg.CHAVES.get(tabela)
    if chaves:
        df = _remover(df, df.duplicated(subset=chaves, keep="first"), tabela,
                      f"Chave ({', '.join(chaves)}) repetida: mantida a 1ª ocorrência", log)
    return df


def _remover_nulos_obrigatorios(df: pd.DataFrame, tabela: str, log: LogTratamento) -> pd.DataFrame:
    anulaveis = cfg.COLUNAS_ANULAVEIS.get(tabela, set())
    obrigatorias = [c for c in cfg.COLUNAS[tabela] if c not in anulaveis]
    return _remover(df, df[obrigatorias].isna().any(axis=1), tabela,
                    "Linhas com campo obrigatório vazio removidas", log)


def _remover_fora_do_dominio(df: pd.DataFrame, tabela: str, log: LogTratamento) -> pd.DataFrame:
    for coluna in df.columns:
        dominio = cfg.DOMINIOS.get(coluna)
        if dominio is None:
            continue
        fora = df[coluna].notna() & ~df[coluna].isin(dominio)
        df = _remover(df, fora, tabela, f"{coluna}: valor fora do domínio, linha removida", log)
    return df


# =============================================================================
# CATÁLOGO
# =============================================================================

def tratar_catalogo(bruto: pd.DataFrame, log: LogTratamento) -> pd.DataFrame:
    """Converte o export da TB_Vinho para a tabela produtos, já tratada."""
    tabela = "produtos"
    df = bruto.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    obrigatorias = {"id_vinho", "nome", "id_tipo", "pais", "preco"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ErroEntrada(
            f"O catálogo não tem as colunas obrigatórias: {sorted(faltando)}. "
            f"Exporte a TB_Vinho com id_vinho, nome, id_tipo, pais e preco."
        )

    df = _limpar_textos(df, tabela, log)
    if "ativo" in df.columns:
        inativo = ~df["ativo"].map(_chave_texto).isin(VALORES_VERDADEIROS)
        df = _remover(df, inativo, tabela, "Vinhos inativos (ativo = falso) removidos", log)

    df["id_tipo"] = pd.to_numeric(df["id_tipo"], errors="coerce")
    produtos = pd.DataFrame({
        "id_produto": df["id_vinho"],
        "nome_vinho": df["nome"],
        "tipo_vinho": df["id_tipo"].map(cfg.TIPOS_VINHO),
        "pais_origem": df["pais"],
        "preco_unitario": df["preco"],
    })
    log.registrar(tabela, "id_tipo sem correspondência em TIPOS_VINHO",
                  int((df["id_tipo"].notna() & produtos["tipo_vinho"].isna()).sum()))

    produtos = _converter_tipos(produtos, tabela, log)
    produtos = _remover_duplicados(produtos, tabela, log)
    produtos = _remover_nulos_obrigatorios(produtos, tabela, log)
    produtos = _remover(produtos, produtos["preco_unitario"] <= 0, tabela,
                        "Preço menor ou igual a zero, linha removida", log)
    produtos["id_produto"] = produtos["id_produto"].astype(int)
    return produtos.reset_index(drop=True)


# =============================================================================
# TABELAS TRANSACIONAIS
# =============================================================================

def tratar_tabelas(tabelas: dict, log: LogTratamento) -> dict:
    tratadas = {}
    for tabela in ["clientes", "produtos", "rupturas_estoque", "pedidos", "produtos_pedidos"]:
        df = tabelas[tabela][cfg.COLUNAS[tabela]].copy()
        df = _limpar_textos(df, tabela, log)
        df = _padronizar_categorias(df, tabela, log)
        df = _converter_tipos(df, tabela, log)
        df = _remover_duplicados(df, tabela, log)
        df = _remover_nulos_obrigatorios(df, tabela, log)
        df = _remover_fora_do_dominio(df, tabela, log)
        tratadas[tabela] = df

    tratadas = _remover_fora_de_faixa(tratadas, log)
    tratadas = _garantir_integridade(tratadas, log)

    for tabela, df in tratadas.items():
        for coluna in cfg.TIPOS_INTEIROS.get(tabela, []):
            df[coluna] = df[coluna].astype(int)
        if tabela == "pedidos":
            df["venda_sucesso"] = df["venda_sucesso"].astype("Int64")
        tratadas[tabela] = df.reset_index(drop=True)
    return tratadas


def _remover_fora_de_faixa(t: dict, log: LogTratamento) -> dict:
    inicio, fim = cfg.DATA_INICIO, cfg.DATA_FIM

    c = t["clientes"]
    t["clientes"] = _remover(c, (c["data_cadastro"] < cfg.DATA_CADASTRO_MIN) | (c["data_cadastro"] > fim),
                             "clientes", "data_cadastro fora do período aceito", log)

    r = t["rupturas_estoque"]
    t["rupturas_estoque"] = _remover(r, r["data_fim"] < r["data_inicio"], "rupturas_estoque",
                                     "data_fim anterior a data_inicio", log)

    p = t["pedidos"]
    p = _remover(p, (p["data_pedido"] < inicio) | (p["data_pedido"] > fim), "pedidos",
                 "data_pedido fora do período da base", log)
    p = _remover(p, p["valor_total"] <= 0, "pedidos", "valor_total menor ou igual a zero", log)
    p = _remover(p, p["valor_frete"] < 0, "pedidos", "valor_frete negativo", log)
    p = _remover(p, (p["prazo_entrega_dias"] < 0) | (p["prazo_entrega_dias"] > cfg.PRAZO_MAXIMO_DIAS),
                 "pedidos", f"prazo_entrega_dias fora de 0 a {cfg.PRAZO_MAXIMO_DIAS}", log)
    p = _remover(p, p["venda_sucesso"].notna() & ~p["venda_sucesso"].isin([0, 1]), "pedidos",
                 "venda_sucesso diferente de 0, 1 ou vazio", log)
    t["pedidos"] = p

    i = t["produtos_pedidos"]
    i = _remover(i, i["quantidade"] < 1, "produtos_pedidos", "quantidade menor que 1", log)
    t["produtos_pedidos"] = _remover(i, i["preco_unitario"] <= 0, "produtos_pedidos",
                                     "preco_unitario menor ou igual a zero", log)

    pr = t["produtos"]
    t["produtos"] = _remover(pr, pr["preco_unitario"] <= 0, "produtos",
                             "preco_unitario menor ou igual a zero", log)
    return t


def _garantir_integridade(t: dict, log: LogTratamento) -> dict:
    """Remove registros órfãos em cascata (cliente -> pedido -> item)."""
    p = t["pedidos"]
    p = _remover(p, ~p["id_cliente"].isin(t["clientes"]["id_cliente"]), "pedidos",
                 "Cliente inexistente: pedido removido", log)

    i = t["produtos_pedidos"]
    i = _remover(i, ~i["id_produto"].isin(t["produtos"]["id_produto"]), "produtos_pedidos",
                 "Produto inexistente: item removido", log)
    i = _remover(i, ~i["id_pedido"].isin(p["id_pedido"]), "produtos_pedidos",
                 "Pedido inexistente ou removido: item removido", log)

    p = _remover(p, ~p["id_pedido"].isin(i["id_pedido"]), "pedidos",
                 "Pedido sem itens válidos removido", log)

    r = t["rupturas_estoque"]
    t["rupturas_estoque"] = _remover(r, ~r["id_produto"].isin(t["produtos"]["id_produto"]),
                                     "rupturas_estoque", "Produto inexistente: ruptura removida", log)
    t["pedidos"], t["produtos_pedidos"] = p, i
    return t


# =============================================================================
# DERIVAÇÃO DA BASE_ML (a partir das tabelas tratadas)
# =============================================================================

def derivar_base_ml(t: dict) -> pd.DataFrame:
    pedidos = t["pedidos"].merge(t["clientes"][["id_cliente", "tipo_cliente"]], on="id_cliente")
    pedidos = pedidos.sort_values(["data_pedido", "id_pedido"]).reset_index(drop=True)

    data = pd.to_datetime(pedidos["data_pedido"])
    pedidos["mes"] = data.dt.month
    pedidos["quinzena"] = np.where(data.dt.day <= 15, 1, 2)
    pedidos["regiao"] = pedidos["uf_destino"].map(lambda uf: cfg.UFS[uf][0])
    pedidos["qtd_itens"] = pedidos["id_pedido"].map(t["produtos_pedidos"].groupby("id_pedido").size())

    # Histórico do cliente: só pedidos pagos ANTES deste contam
    anteriores, variacoes = [], []
    historico: dict[int, list[float]] = {}
    for linha in pedidos.itertuples(index=False):
        pagos = historico.setdefault(linha.id_cliente, [])
        anteriores.append(len(pagos))
        variacoes.append(round((linha.valor_total / pagos[-1] - 1) * 100, 2) if pagos else np.nan)
        if pd.notna(linha.venda_sucesso) and linha.venda_sucesso == 1:
            pagos.append(linha.valor_total)
    pedidos["pedidos_anteriores"] = anteriores
    pedidos["variacao_pedido_anterior_pct"] = variacoes

    base = pedidos[cfg.COLUNAS["base_ml"]].sort_values("id_pedido").reset_index(drop=True)
    base["venda_sucesso"] = base["venda_sucesso"].astype("Int64")
    return base