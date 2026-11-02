"""
Vinheria Agnello - PBL Fase 3
Pipeline ETL da base de vendas simulada.

    Extract   : lê o snapshot do catálogo (data/tb_vinho.csv, gerado por extrair_catalogo.py)
    Transform : trata o catálogo -> valida -> simula vendas -> valida base bruta (diagnóstico)
                -> trata as tabelas -> deriva base_ml -> valida base tratada (interrompe se falhar)
    Load      : grava data/vinheria_fase3.xlsx e resultados/relatorio_validacao.txt

Abas do .xlsx: dicionario, clientes, produtos, rupturas_estoque, pedidos,
               produtos_pedidos, base_ml, metadados

Rótulo (venda_sucesso): 1 = pedido pago | 0 = não pago | vazio = aguardando pagamento
"""

import sys
from calendar import monthrange
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

import parametros as cfg
from dicionario_dados import montar_dicionario
from transformacao import ErroEntrada, LogTratamento, derivar_base_ml, tratar_catalogo, tratar_tabelas
from validacao import ErroValidacao, escrever_relatorio, validar_base, validar_catalogo

rng = np.random.default_rng(cfg.SEMENTE)


# =============================================================================
# EXTRACT
# =============================================================================

def ler_catalogo() -> pd.DataFrame:
    if not cfg.CAMINHO_CATALOGO.exists():
        raise FileNotFoundError(
            f"Catálogo não encontrado em {cfg.CAMINHO_CATALOGO}. "
            f"Rode extrair_catalogo.py ou exporte a TB_Vinho para esse arquivo."
        )
    with open(cfg.CAMINHO_CATALOGO, encoding="utf-8-sig") as arquivo:
        cabecalho = arquivo.readline()
    separador = "\t" if "\t" in cabecalho else ";" if ";" in cabecalho else ","
    return pd.read_csv(cfg.CAMINHO_CATALOGO, sep=separador, dtype=str, encoding="utf-8-sig",
                       keep_default_na=False, na_values=["", "NULL", "null", "NaN"])


# =============================================================================
# SIMULAÇÃO: AUXILIARES
# =============================================================================

def sortear(opcoes: dict):
    chaves = list(opcoes.keys())
    pesos = np.array(list(opcoes.values()), dtype=float)
    return chaves[rng.choice(len(chaves), p=pesos / pesos.sum())]


def data_aleatoria(inicio: date, fim: date) -> date:
    return inicio + timedelta(days=int(rng.integers(0, (fim - inicio).days + 1)))


# =============================================================================
# SIMULAÇÃO: CLIENTES, RUPTURAS E DATAS
# =============================================================================

def gerar_clientes() -> tuple[pd.DataFrame, dict]:
    ufs = list(cfg.UFS.keys())
    pesos_uf = np.array([cfg.UFS[u][1] for u in ufs])
    pesos_uf = pesos_uf / pesos_uf.sum()

    registros, perfil = [], {}
    for id_cliente in range(1, cfg.N_CLIENTES + 1):
        tipo = "PJ" if rng.random() < cfg.PCT_PJ else "PF"
        if rng.random() < cfg.PCT_CADASTRO_ANTES_INICIO:
            cadastro = data_aleatoria(cfg.DATA_CADASTRO_MIN, cfg.DATA_INICIO - timedelta(days=1))
        else:
            cadastro = data_aleatoria(cfg.DATA_INICIO, cfg.DATA_FIM - timedelta(days=30))

        registros.append({
            "id_cliente": id_cliente,
            "tipo_cliente": tipo,
            "uf": ufs[rng.choice(len(ufs), p=pesos_uf)],
            "data_cadastro": cadastro,
        })
        # Atributos internos da simulação (não exportados)
        perfil[id_cliente] = {
            "frequencia": rng.lognormal(0, 0.8) * (3.0 if tipo == "PJ" else 1.0),
            "qtd_base_pj": int(rng.choice([6, 12])),
            "itens_base_pj": int(rng.integers(2, 6)),
        }
    return pd.DataFrame(registros), perfil


def definir_produtos_preferidos(perfil: dict, clientes: pd.DataFrame, catalogo: pd.DataFrame) -> None:
    """PJ (restaurantes, empórios) recompra um mix fixo de rótulos."""
    for id_cliente in clientes.loc[clientes["tipo_cliente"] == "PJ", "id_cliente"]:
        tamanho = min(len(catalogo), perfil[id_cliente]["itens_base_pj"] + 2)
        perfil[id_cliente]["produtos_preferidos"] = rng.choice(len(catalogo), size=tamanho, replace=False)


def gerar_rupturas(catalogo: pd.DataFrame) -> pd.DataFrame:
    ids_catalogo = set(catalogo["id_produto"])
    janelas = {id_produto: [] for id_produto in ids_catalogo}
    registros = []

    for id_produto, inicio in cfg.RUPTURAS_ATUAIS.items():
        if id_produto in ids_catalogo:
            janelas[id_produto].append((inicio, cfg.DATA_FIM))
            registros.append({"id_produto": id_produto, "data_inicio": inicio,
                              "data_fim": cfg.DATA_FIM, "tipo_ruptura": "Atual"})

    for id_produto in sorted(ids_catalogo):
        qtd = int(rng.integers(cfg.RUPTURAS_POR_PRODUTO[0], cfg.RUPTURAS_POR_PRODUTO[1] + 1))
        for _ in range(qtd):
            for _tentativa in range(20):   # evita janelas sobrepostas no mesmo produto
                duracao = int(rng.integers(cfg.DURACAO_RUPTURA_DIAS[0], cfg.DURACAO_RUPTURA_DIAS[1] + 1))
                inicio = data_aleatoria(cfg.DATA_INICIO, cfg.DATA_FIM - timedelta(days=duracao))
                fim = inicio + timedelta(days=duracao - 1)
                if all(fim < ini or inicio > f for ini, f in janelas[id_produto]):
                    janelas[id_produto].append((inicio, fim))
                    registros.append({"id_produto": int(id_produto), "data_inicio": inicio,
                                      "data_fim": fim, "tipo_ruptura": "Temporária"})
                    break

    return (pd.DataFrame(registros, columns=cfg.COLUNAS["rupturas_estoque"])
            .sort_values(["id_produto", "data_inicio"])
            .reset_index(drop=True))


def indices_disponiveis(d: date, catalogo: pd.DataFrame, rupturas: pd.DataFrame) -> np.ndarray:
    em_ruptura = rupturas[(rupturas["data_inicio"] <= d) & (rupturas["data_fim"] >= d)]["id_produto"]
    return np.flatnonzero(~catalogo["id_produto"].isin(em_ruptura).to_numpy())


def gerar_datas_pedidos() -> list[date]:
    datas = []
    ano, mes = cfg.DATA_INICIO.year, cfg.DATA_INICIO.month
    while (ano, mes) <= (cfg.DATA_FIM.year, cfg.DATA_FIM.month):
        dias_no_mes = monthrange(ano, mes)[1]
        ultimo_dia = cfg.DATA_FIM.day if (ano, mes) == cfg.MES_EM_ANDAMENTO else dias_no_mes

        multiplicador = cfg.MULTIPLICADOR_MES.get(mes, 1.0)
        if (ano, mes) in cfg.MESES_COPA:
            multiplicador += cfg.ACRESCIMO_COPA

        qtd = int(round(rng.uniform(cfg.BASE_MES_MIN, cfg.BASE_MES_MAX) * multiplicador))
        qtd = int(np.clip(qtd, cfg.PEDIDOS_MES_MIN, cfg.PEDIDOS_MES_MAX))
        qtd = int(round(qtd * ultimo_dia / dias_no_mes))   # mês parcial (outubro/2026)

        dias = rng.integers(1, ultimo_dia + 1, size=qtd)
        datas.extend(date(ano, mes, int(d)) for d in dias)

        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1
    return sorted(datas)


# =============================================================================
# SIMULAÇÃO: REGRAS DO PEDIDO
# =============================================================================

def opcoes_frete(uf: str, regiao: str) -> dict:
    opcoes = {"Econômico": cfg.PESO_TIPO_FRETE["Econômico"], "Expresso": cfg.PESO_TIPO_FRETE["Expresso"]}
    if regiao in cfg.REGIOES_SAME_DAY:
        opcoes["Same-Day"] = cfg.PESO_TIPO_FRETE["Same-Day"]
    if uf == cfg.UF_LOJA:
        opcoes["Retirada"] = cfg.PESO_TIPO_FRETE["Retirada"]
    return opcoes


def calcular_prazo(tipo_frete: str, grupo: str, d: date) -> int:
    minimo, maximo = cfg.PRAZO_DIAS[(tipo_frete, grupo)]
    prazo = int(rng.integers(minimo, maximo + 1))
    if cfg.eh_periodo_pico(d):
        prazo += cfg.ACRESCIMO_PRAZO_PICO.get(tipo_frete, 0)
    return prazo


def calcular_valor_frete(tipo_frete: str, grupo: str, frete_gratis: bool) -> float:
    if tipo_frete == "Retirada" or frete_gratis:
        return 0.0
    minimo, maximo = cfg.VALOR_FRETE[(tipo_frete, grupo)]
    return round(float(rng.uniform(minimo, maximo)), 2)


def penalidade_prazo(prazo: int) -> int:
    if prazo < 7:
        return 0
    return -3 * ((prazo - 7) // 2 + 1)   # 7-8: -3 | 9-10: -6 | 11-12: -9 ...


def penalidade_variacao_pj(variacao_pct: float) -> int:
    if variacao_pct is None or np.isnan(variacao_pct) or variacao_pct < 15:
        return 0
    if variacao_pct >= 50:
        return -60
    return -2 * (int((variacao_pct - 15) // 3) + 1)   # 15%: -2 | 18%: -4 | ... 48%: -24


def efeito_tipo_frete(tipo_frete: str) -> float:
    if tipo_frete == "Econômico":
        return float(rng.uniform(-5, 5))
    return {"Retirada": 5, "Expresso": 8, "Same-Day": 12}[tipo_frete]


def calcular_probabilidade(p: dict) -> float:
    prob = cfg.PROB_BASE
    prob += {"Cartão": 0, "PIX": -5, "Boleto": -20}[p["forma_pagamento"]]
    prob += 10 if p["pedidos_anteriores"] >= 1 else 0
    prob += efeito_tipo_frete(p["tipo_frete"])
    prob += 8 if p["frete_gratis"] else 0
    prob += penalidade_prazo(p["prazo_entrega_dias"])
    prob += p["pct_desconto"]
    prob += 5 if p["qtd_itens"] >= 3 else 0
    prob += 5 if p["canal"] == "App" else 0
    if p["tipo_cliente"] == "PF" and p["valor_total"] > 500:
        prob -= 10
    if p["data_pedido"].month in cfg.MESES_FESTIVOS and p["valor_total"] < 200:
        prob += 10
    if p["tipo_cliente"] == "PJ":
        prob += 5
        prob += penalidade_variacao_pj(p["variacao_pedido_anterior_pct"])
    return float(np.clip(prob, cfg.PROB_PISO, cfg.PROB_TETO)) / 100


def sortear_motivo_insucesso(forma_pagamento: str) -> str:
    return cfg.MOTIVO_POR_PAGAMENTO[forma_pagamento] if rng.random() < 0.60 else "Desistência"


def sortear_itens(tipo_cliente: str, perfil_cliente: dict, catalogo: pd.DataFrame,
                  disponiveis: np.ndarray) -> list[tuple]:
    if tipo_cliente == "PF":
        n_itens = int(rng.choice([1, 2, 3, 4], p=[0.50, 0.30, 0.15, 0.05]))
        candidatos = disponiveis
    else:
        variacao_itens = int(rng.choice([-1, 0, 1], p=[0.2, 0.6, 0.2]))
        n_itens = max(1, perfil_cliente["itens_base_pj"] + variacao_itens)
        candidatos = np.intersect1d(perfil_cliente["produtos_preferidos"], disponiveis)
        if len(candidatos) == 0:   # todo o mix em ruptura: compra de outros rótulos
            candidatos = disponiveis
    n_itens = min(n_itens, len(candidatos))

    itens = []
    for i in rng.choice(candidatos, size=n_itens, replace=False):
        produto = catalogo.iloc[int(i)]
        if tipo_cliente == "PF":
            quantidade = int(rng.integers(1, 4))
        else:
            quantidade = max(1, int(round(perfil_cliente["qtd_base_pj"] * rng.lognormal(0, 0.2))))
        itens.append((int(produto["id_produto"]), quantidade, float(produto["preco_unitario"])))
    return itens


# =============================================================================
# SIMULAÇÃO: PEDIDOS
# =============================================================================

def gerar_pedidos(clientes: pd.DataFrame, perfil: dict, catalogo: pd.DataFrame,
                  rupturas: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    datas = gerar_datas_pedidos()

    # Mês em andamento: os pedidos mais recentes ficam aguardando pagamento
    indices_andamento = [i for i, d in enumerate(datas) if cfg.eh_mes_em_andamento(d)]
    qtd_aguardando = int(round(len(indices_andamento) * cfg.PCT_AGUARDANDO_PAGAMENTO_OUT))
    indices_aguardando = set(indices_andamento[len(indices_andamento) - qtd_aguardando:])

    clientes_idx = clientes.set_index("id_cliente")
    historico_pagos = {c: [] for c in clientes["id_cliente"]}

    pedidos, itens_pedidos = [], []
    id_pedido = 0
    for i, d in enumerate(datas):
        disponiveis = indices_disponiveis(d, catalogo, rupturas)
        if len(disponiveis) == 0:   # catálogo inteiro em ruptura: não há venda possível
            continue
        id_pedido += 1

        elegiveis = clientes[clientes["data_cadastro"] <= d]["id_cliente"].to_numpy()
        pesos = np.array([perfil[c]["frequencia"] for c in elegiveis])
        id_cliente = int(elegiveis[rng.choice(len(elegiveis), p=pesos / pesos.sum())])

        cliente = clientes_idx.loc[id_cliente]
        tipo_cliente, uf = cliente["tipo_cliente"], cliente["uf"]
        regiao = cfg.UFS[uf][0]
        grupo = cfg.GRUPO_LOGISTICO[regiao]

        itens = sortear_itens(tipo_cliente, perfil[id_cliente], catalogo, disponiveis)
        subtotal = sum(q * preco for _, q, preco in itens)
        pct_desconto = sortear(cfg.PROB_DESCONTO)
        valor_total = round(subtotal * (1 - pct_desconto / 100), 2)

        tipo_frete = sortear(opcoes_frete(uf, regiao))
        frete_gratis = (tipo_frete == "Econômico"
                        and regiao in cfg.REGIOES_FRETE_GRATIS
                        and valor_total >= cfg.VALOR_MIN_FRETE_GRATIS)

        pagos_anteriores = historico_pagos[id_cliente]
        variacao = (round((valor_total / pagos_anteriores[-1] - 1) * 100, 2)
                    if pagos_anteriores else np.nan)

        pedido = {
            "id_pedido": id_pedido,
            "id_cliente": id_cliente,
            "data_pedido": d,
            "canal": sortear(cfg.PROB_CANAL),
            "uf_destino": uf,
            "tipo_frete": tipo_frete,
            "valor_frete": calcular_valor_frete(tipo_frete, grupo, frete_gratis),
            "prazo_entrega_dias": calcular_prazo(tipo_frete, grupo, d),
            "forma_pagamento": sortear(cfg.PROB_PAGAMENTO),
            "pct_desconto": pct_desconto,
            "valor_total": valor_total,
        }
        contexto = {**pedido, "tipo_cliente": tipo_cliente, "frete_gratis": frete_gratis,
                    "pedidos_anteriores": len(pagos_anteriores), "qtd_itens": len(itens),
                    "variacao_pedido_anterior_pct": variacao}

        if i in indices_aguardando:
            pedido.update(venda_sucesso=None, motivo_insucesso=None, status_pedido="Aguardando pagamento")
        elif rng.random() < calcular_probabilidade(contexto):
            pedido.update(venda_sucesso=1, motivo_insucesso=None, status_pedido="Pago")
            historico_pagos[id_cliente].append(valor_total)
        else:
            pedido.update(venda_sucesso=0, status_pedido="Não pago",
                          motivo_insucesso=sortear_motivo_insucesso(pedido["forma_pagamento"]))

        pedidos.append(pedido)
        itens_pedidos.extend(
            {"id_pedido": id_pedido, "id_produto": id_prod, "quantidade": q, "preco_unitario": preco}
            for id_prod, q, preco in itens
        )

    df_pedidos = pd.DataFrame(pedidos)
    df_pedidos["status_entrega"] = definir_status_entrega(df_pedidos)
    return df_pedidos[cfg.COLUNAS["pedidos"]], pd.DataFrame(itens_pedidos)


def definir_status_entrega(pedidos: pd.DataFrame) -> pd.Series:
    status = pd.Series([None] * len(pedidos), index=pedidos.index, dtype=object)
    pagos = pedidos["venda_sucesso"] == 1
    status[pagos] = "Entregue"

    # Mês em andamento: parte dos pagos ainda em trânsito (os mais recentes)
    pagos_andamento = pedidos[pagos & pedidos["data_pedido"].map(cfg.eh_mes_em_andamento)]
    pagos_andamento = pagos_andamento.sort_values("data_pedido")
    qtd_transito = int(round(len(pagos_andamento) * rng.uniform(*cfg.FAIXA_EM_TRANSITO_OUT)))
    if qtd_transito:
        status[pagos_andamento.index[-qtd_transito:]] = "Em trânsito"
    return status


def simular(catalogo: pd.DataFrame) -> dict:
    clientes, perfil = gerar_clientes()
    definir_produtos_preferidos(perfil, clientes, catalogo)
    rupturas = gerar_rupturas(catalogo)
    pedidos, produtos_pedidos = gerar_pedidos(clientes, perfil, catalogo, rupturas)
    return {
        "clientes": clientes,
        "produtos": catalogo,
        "rupturas_estoque": rupturas,
        "pedidos": pedidos,
        "produtos_pedidos": produtos_pedidos,
    }


# =============================================================================
# LOAD
# =============================================================================

CARACTERES_FORMULA = ("=", "+", "-", "@")


def sanitizar_para_excel(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Impede que texto iniciado por =, +, - ou @ seja gravado como fórmula no Excel."""
    df = df.copy()
    alterados = 0
    for coluna in df.select_dtypes(include=["object", "string"]).columns:
        risco = df[coluna].map(lambda x: isinstance(x, str) and x.startswith(CARACTERES_FORMULA))
        alterados += int(risco.sum())
        df.loc[risco, coluna] = "'" + df.loc[risco, coluna]
    return df, alterados


def montar_metadados(tabelas: dict, inicio_execucao: datetime) -> dict:
    metadados = {
        "Versão do pipeline": cfg.VERSAO_PIPELINE,
        "Semente aleatória": cfg.SEMENTE,
        "Período da base": f"{cfg.DATA_INICIO:%d/%m/%Y} a {cfg.DATA_FIM:%d/%m/%Y}",
        "Catálogo de origem": f"{cfg.CAMINHO_CATALOGO.name} (export da TB_Vinho)",
        "Data da geração": f"{inicio_execucao:%d/%m/%Y %H:%M:%S}",
    }
    for nome, df in tabelas.items():
        metadados[f"Linhas em {nome}"] = len(df)
    return metadados


def gravar_excel(tabelas: dict, dicionario: pd.DataFrame, metadados: dict, log: LogTratamento) -> None:
    abas = {"dicionario": dicionario, **tabelas,
            "metadados": pd.DataFrame(list(metadados.items()), columns=["item", "valor"])}
    sanitizadas, total_sanitizado = {}, 0
    for nome, df in abas.items():
        sanitizadas[nome], alterados = sanitizar_para_excel(df)
        total_sanitizado += alterados
    log.registrar("todas", "Textos iniciados por =, +, - ou @ protegidos contra fórmula", total_sanitizado)

    cfg.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    try:
        with pd.ExcelWriter(cfg.CAMINHO_SAIDA, engine="openpyxl") as writer:
            for nome, df in sanitizadas.items():
                df.to_excel(writer, sheet_name=nome, index=False)
    except PermissionError:
        raise PermissionError(
            f"Não foi possível gravar {cfg.CAMINHO_SAIDA.name}. "
            f"Feche o arquivo no Excel (ou no Power BI) e rode de novo."
        ) from None


# =============================================================================
# RESUMO
# =============================================================================

def imprimir_resumo(base: pd.DataFrame) -> None:
    fechados = base[base["venda_sucesso"].notna()]
    print(f"\nPedidos: {len(base)} | fechados: {len(fechados)} | "
          f"aguardando: {base['venda_sucesso'].isna().sum()}")
    print(f"Conversão geral: {fechados['venda_sucesso'].astype(float).mean():.1%}")
    for coluna in ["forma_pagamento", "tipo_frete", "tipo_cliente", "canal", "regiao"]:
        taxa = fechados.groupby(coluna)["venda_sucesso"].agg(lambda s: s.astype(float).mean())
        tamanho = fechados.groupby(coluna).size()
        linhas = " | ".join(f"{k}: {taxa[k]:.1%} ({tamanho[k]})" for k in taxa.index)
        print(f"Conversão por {coluna}: {linhas}")


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main() -> int:
    inicio_execucao = datetime.now()
    log = LogTratamento()
    validadores = []
    metadados = {"Versão do pipeline": cfg.VERSAO_PIPELINE, "Semente aleatória": cfg.SEMENTE}
    codigo_saida = 0

    try:
        print("[1/6] Extract: lendo o catálogo")
        catalogo = tratar_catalogo(ler_catalogo(), log)

        print("[2/6] Validando o catálogo")
        validadores.append(validar_catalogo(catalogo))

        print("[3/6] Simulando as vendas")
        brutas = simular(catalogo)

        print("[4/6] Validando a base bruta (diagnóstico)")
        validadores.append(validar_base(brutas, "Base bruta (antes do tratamento)", interromper=False))

        print("[5/6] Tratando as tabelas e derivando a base_ml")
        tratadas = tratar_tabelas(brutas, log)
        tratadas["base_ml"] = derivar_base_ml(tratadas)
        log.imprimir()
        validadores.append(validar_base(tratadas, "Base tratada (antes de gravar)"))

        print("\n[6/6] Load: gravando o .xlsx")
        metadados = montar_metadados(tratadas, inicio_execucao)
        metadados["Validação"] = " | ".join(f"{v.etapa}: {v.resumo()}" for v in validadores)
        gravar_excel(tratadas, montar_dicionario(), metadados, log)

        imprimir_resumo(tratadas["base_ml"])
        print(f"\nBase gravada: {cfg.CAMINHO_SAIDA}")

    except ErroValidacao as erro:
        print(f"\nPIPELINE INTERROMPIDO: {erro}\nO arquivo {cfg.CAMINHO_SAIDA.name} NÃO foi gravado.")
        codigo_saida = 1
    except (ErroEntrada, FileNotFoundError, PermissionError) as erro:
        print(f"\nERRO: {erro}")
        codigo_saida = 1
    finally:
        escrever_relatorio(cfg.CAMINHO_RELATORIO, metadados, log.itens, validadores)
        print(f"Relatório de validação: {cfg.CAMINHO_RELATORIO}")

    return codigo_saida


if __name__ == "__main__":
    sys.exit(main())