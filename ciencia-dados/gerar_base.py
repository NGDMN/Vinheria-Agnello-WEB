"""
Vinheria Agnello - PBL Fase 3
Geração da base de vendas simulada.

Entrada : data/tb_vinho.csv  (export da TB_Vinho: id_vinho, nome, id_tipo, pais, preco)
Saída   : data/vinheria_fase3.xlsx
          abas: clientes, produtos, pedidos, produtos_pedidos, base_ml

Rótulo (venda_sucesso): 1 = pedido pago | 0 = não pago | vazio = aguardando pagamento
"""

from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# =============================================================================
# PARÂMETROS
# =============================================================================

SEMENTE = 42

DATA_INICIO = date(2024, 10, 1)
DATA_FIM = date(2026, 10, 19)

CAMINHO_CATALOGO = Path("data/tb_vinho.csv")
CAMINHO_SAIDA = Path("data/vinheria_fase3.xlsx")

# Volume mensal: base sorteada x multiplicador sazonal, limitado ao intervalo
PEDIDOS_MES_MIN, PEDIDOS_MES_MAX = 15, 50
BASE_MES_MIN, BASE_MES_MAX = 15, 30
MULTIPLICADOR_MES = {5: 1.3, 6: 1.3, 8: 1.3, 12: 2.0}   # Mães, Namorados, Pais, Natal
MESES_COPA = {(2026, 6), (2026, 7)}
ACRESCIMO_COPA = 0.4
MESES_FESTIVOS = {5, 6, 8, 12}

# Clientes
N_CLIENTES = 250
PCT_PJ = 0.30
DATA_CADASTRO_MIN = date(2023, 1, 1)
PCT_CADASTRO_ANTES_INICIO = 0.40
UF_LOJA = "SP"   # loja física: define quem pode escolher Retirada

UFS = {  # uf: (regiao, peso de distribuição dos clientes)
    "SP": ("Sudeste", 30.0), "RJ": ("Sudeste", 10.0), "MG": ("Sudeste", 9.0), "ES": ("Sudeste", 2.0),
    "PR": ("Sul", 7.0), "SC": ("Sul", 5.0), "RS": ("Sul", 6.0),
    "DF": ("Centro-Oeste", 3.0), "GO": ("Centro-Oeste", 3.0), "MT": ("Centro-Oeste", 1.5), "MS": ("Centro-Oeste", 1.5),
    "BA": ("Nordeste", 4.0), "PE": ("Nordeste", 3.0), "CE": ("Nordeste", 3.0), "RN": ("Nordeste", 1.0),
    "PB": ("Nordeste", 1.0), "AL": ("Nordeste", 1.0), "SE": ("Nordeste", 0.5), "PI": ("Nordeste", 0.5),
    "MA": ("Nordeste", 1.0),
    "AM": ("Norte", 2.0), "PA": ("Norte", 2.5), "RO": ("Norte", 0.5), "TO": ("Norte", 0.5),
    "AC": ("Norte", 0.25), "AP": ("Norte", 0.25), "RR": ("Norte", 0.25),
}
GRUPO_LOGISTICO = {  # agrupamento usado em prazo e valor de frete
    "Sul": "SSE", "Sudeste": "SSE",
    "Centro-Oeste": "CONE", "Nordeste": "CONE",
    "Norte": "N",
}

TIPOS_VINHO = {1: "Tinto", 2: "Branco", 3: "Rosé", 4: "Espumante", 5: "Fortificado"}

# Distribuições do pedido
PROB_CANAL = {"Site": 0.65, "App": 0.35}
PROB_PAGAMENTO = {"Cartão": 0.50, "PIX": 0.30, "Boleto": 0.20}
PROB_DESCONTO = {0: 0.60, 5: 0.40 / 3, 10: 0.40 / 3, 15: 0.40 / 3}

# Frete
PESO_TIPO_FRETE = {"Econômico": 0.55, "Expresso": 0.25, "Same-Day": 0.12, "Retirada": 0.08}
REGIOES_SAME_DAY = {"Sul", "Sudeste"}
REGIOES_FRETE_GRATIS = {"Sul", "Sudeste"}
VALOR_MIN_FRETE_GRATIS = 250.00

PRAZO_DIAS = {  # (tipo_frete, grupo): (mín, máx)
    ("Econômico", "SSE"): (4, 7), ("Econômico", "CONE"): (7, 11), ("Econômico", "N"): (10, 15),
    ("Expresso", "SSE"): (2, 3), ("Expresso", "CONE"): (3, 5), ("Expresso", "N"): (5, 7),
    ("Same-Day", "SSE"): (0, 1),
    ("Retirada", "SSE"): (1, 2),
}
ACRESCIMO_PRAZO_PICO = {"Econômico": 3, "Expresso": 1}   # dezembro e semana da Black Friday

VALOR_FRETE = {  # (tipo_frete, grupo): (mín, máx) em R$
    ("Econômico", "SSE"): (15, 30), ("Econômico", "CONE"): (25, 45), ("Econômico", "N"): (35, 60),
    ("Expresso", "SSE"): (27, 54), ("Expresso", "CONE"): (45, 81), ("Expresso", "N"): (63, 108),
    ("Same-Day", "SSE"): (30, 50),
}

# Outubro/2026: pedidos ainda em andamento
PCT_AGUARDANDO_PAGAMENTO_OUT = 0.40
FAIXA_EM_TRANSITO_OUT = (0.40, 0.60)
MES_EM_ANDAMENTO = (DATA_FIM.year, DATA_FIM.month)

# Probabilidade de pagamento (pontos percentuais)
PROB_BASE = 70
PROB_PISO = 20
PROB_TETO = 90

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

rng = np.random.default_rng(SEMENTE)


def sortear(opcoes: dict):
    chaves = list(opcoes.keys())
    pesos = np.array(list(opcoes.values()), dtype=float)
    return chaves[rng.choice(len(chaves), p=pesos / pesos.sum())]


def data_aleatoria(inicio: date, fim: date) -> date:
    return inicio + timedelta(days=int(rng.integers(0, (fim - inicio).days + 1)))


def black_friday(ano: int) -> date:
    primeiro_nov = date(ano, 11, 1)
    primeira_quinta = primeiro_nov + timedelta(days=(3 - primeiro_nov.weekday()) % 7)
    return primeira_quinta + timedelta(days=22)   # sexta após a 4ª quinta-feira


def eh_periodo_pico(d: date) -> bool:
    if d.month == 12:
        return True
    bf = black_friday(d.year)
    return bf - timedelta(days=4) <= d <= bf + timedelta(days=2)   # segunda a domingo


def eh_mes_em_andamento(d: date) -> bool:
    return (d.year, d.month) == MES_EM_ANDAMENTO


# =============================================================================
# CATÁLOGO
# =============================================================================

def carregar_catalogo() -> pd.DataFrame:
    df = pd.read_csv(CAMINHO_CATALOGO, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]

    obrigatorias = {"id_vinho", "nome", "id_tipo", "pais", "preco"}
    faltando = obrigatorias - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes em {CAMINHO_CATALOGO}: {sorted(faltando)}")

    if "ativo" in df.columns:
        df = df[df["ativo"].astype(str).isin(["1", "True", "true"])]

    df["preco"] = pd.to_numeric(df["preco"].astype(str).str.replace(",", ".", regex=False))
    df["id_tipo"] = df["id_tipo"].astype(int)

    return pd.DataFrame({
        "id_produto": df["id_vinho"].astype(int),
        "nome_vinho": df["nome"],
        "tipo_vinho": df["id_tipo"].map(TIPOS_VINHO),
        "pais_origem": df["pais"],
        "preco_unitario": df["preco"].round(2),
    }).reset_index(drop=True)


# =============================================================================
# CLIENTES
# =============================================================================

def gerar_clientes() -> tuple[pd.DataFrame, dict]:
    ufs = list(UFS.keys())
    pesos_uf = np.array([UFS[u][1] for u in ufs])
    pesos_uf = pesos_uf / pesos_uf.sum()

    registros, perfil = [], {}
    for id_cliente in range(1, N_CLIENTES + 1):
        tipo = "PJ" if rng.random() < PCT_PJ else "PF"

        if rng.random() < PCT_CADASTRO_ANTES_INICIO:
            cadastro = data_aleatoria(DATA_CADASTRO_MIN, DATA_INICIO - timedelta(days=1))
        else:
            cadastro = data_aleatoria(DATA_INICIO, DATA_FIM - timedelta(days=30))

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


# =============================================================================
# DATAS DOS PEDIDOS
# =============================================================================

def gerar_datas_pedidos() -> list[date]:
    datas = []
    ano, mes = DATA_INICIO.year, DATA_INICIO.month

    while (ano, mes) <= (DATA_FIM.year, DATA_FIM.month):
        dias_no_mes = monthrange(ano, mes)[1]
        ultimo_dia = DATA_FIM.day if (ano, mes) == (DATA_FIM.year, DATA_FIM.month) else dias_no_mes

        multiplicador = MULTIPLICADOR_MES.get(mes, 1.0)
        if (ano, mes) in MESES_COPA:
            multiplicador += ACRESCIMO_COPA

        qtd = int(round(rng.uniform(BASE_MES_MIN, BASE_MES_MAX) * multiplicador))
        qtd = int(np.clip(qtd, PEDIDOS_MES_MIN, PEDIDOS_MES_MAX))
        qtd = int(round(qtd * ultimo_dia / dias_no_mes))   # mês parcial (outubro/2026)

        dias = rng.integers(1, ultimo_dia + 1, size=qtd)
        datas.extend(date(ano, mes, int(d)) for d in dias)

        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1

    return sorted(datas)


# =============================================================================
# REGRAS DE NEGÓCIO DO PEDIDO
# =============================================================================

def opcoes_frete(uf: str, regiao: str) -> dict:
    opcoes = {"Econômico": PESO_TIPO_FRETE["Econômico"], "Expresso": PESO_TIPO_FRETE["Expresso"]}
    if regiao in REGIOES_SAME_DAY:
        opcoes["Same-Day"] = PESO_TIPO_FRETE["Same-Day"]
    if uf == UF_LOJA:
        opcoes["Retirada"] = PESO_TIPO_FRETE["Retirada"]
    return opcoes


def calcular_prazo(tipo_frete: str, grupo: str, d: date) -> int:
    minimo, maximo = PRAZO_DIAS[(tipo_frete, grupo)]
    prazo = int(rng.integers(minimo, maximo + 1))
    if eh_periodo_pico(d):
        prazo += ACRESCIMO_PRAZO_PICO.get(tipo_frete, 0)
    return prazo


def calcular_valor_frete(tipo_frete: str, grupo: str, frete_gratis: bool) -> float:
    if tipo_frete == "Retirada" or frete_gratis:
        return 0.0
    minimo, maximo = VALOR_FRETE[(tipo_frete, grupo)]
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
    prob = PROB_BASE

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
    if p["data_pedido"].month in MESES_FESTIVOS and p["valor_total"] < 200:
        prob += 10
    if p["tipo_cliente"] == "PJ":
        prob += 5
        prob += penalidade_variacao_pj(p["variacao_pedido_anterior_pct"])

    return float(np.clip(prob, PROB_PISO, PROB_TETO)) / 100


def sortear_motivo_insucesso(forma_pagamento: str) -> str:
    motivo_pagamento = {
        "Cartão": "Pagamento recusado",
        "PIX": "PIX expirado",
        "Boleto": "Boleto expirado",
    }[forma_pagamento]
    return motivo_pagamento if rng.random() < 0.60 else "Desistência"


def sortear_itens(tipo_cliente: str, perfil_cliente: dict, catalogo: pd.DataFrame) -> list[tuple]:
    if tipo_cliente == "PF":
        n_itens = int(rng.choice([1, 2, 3, 4], p=[0.50, 0.30, 0.15, 0.05]))
        candidatos = np.arange(len(catalogo))
    else:
        variacao_itens = int(rng.choice([-1, 0, 1], p=[0.2, 0.6, 0.2]))
        n_itens = max(1, perfil_cliente["itens_base_pj"] + variacao_itens)
        candidatos = perfil_cliente["produtos_preferidos"]
    n_itens = min(n_itens, len(candidatos))

    indices = rng.choice(candidatos, size=n_itens, replace=False)
    itens = []
    for i in indices:
        produto = catalogo.iloc[int(i)]
        if tipo_cliente == "PF":
            quantidade = int(rng.integers(1, 4))
        else:
            quantidade = max(1, int(round(perfil_cliente["qtd_base_pj"] * rng.lognormal(0, 0.2))))
        itens.append((int(produto["id_produto"]), quantidade, float(produto["preco_unitario"])))
    return itens


# =============================================================================
# GERAÇÃO DOS PEDIDOS
# =============================================================================

def gerar_pedidos(clientes: pd.DataFrame, perfil: dict, catalogo: pd.DataFrame):
    datas = gerar_datas_pedidos()

    # Outubro/2026: os 40% mais recentes ficam aguardando pagamento
    indices_andamento = [i for i, d in enumerate(datas) if eh_mes_em_andamento(d)]
    qtd_aguardando = int(round(len(indices_andamento) * PCT_AGUARDANDO_PAGAMENTO_OUT))
    indices_aguardando = set(indices_andamento[len(indices_andamento) - qtd_aguardando:])

    clientes_idx = clientes.set_index("id_cliente")
    historico_pagos = {c: [] for c in clientes["id_cliente"]}   # valores dos pedidos pagos

    pedidos, itens_pedidos = [], []
    for i, d in enumerate(datas):
        id_pedido = i + 1

        elegiveis = clientes[clientes["data_cadastro"] <= d]["id_cliente"].to_numpy()
        pesos = np.array([perfil[c]["frequencia"] for c in elegiveis])
        id_cliente = int(elegiveis[rng.choice(len(elegiveis), p=pesos / pesos.sum())])

        cliente = clientes_idx.loc[id_cliente]
        tipo_cliente, uf = cliente["tipo_cliente"], cliente["uf"]
        regiao = UFS[uf][0]
        grupo = GRUPO_LOGISTICO[regiao]

        itens = sortear_itens(tipo_cliente, perfil[id_cliente], catalogo)
        subtotal = sum(q * preco for _, q, preco in itens)
        pct_desconto = sortear(PROB_DESCONTO)
        valor_total = round(subtotal * (1 - pct_desconto / 100), 2)

        tipo_frete = sortear(opcoes_frete(uf, regiao))
        frete_gratis = (
            tipo_frete == "Econômico"
            and regiao in REGIOES_FRETE_GRATIS
            and valor_total >= VALOR_MIN_FRETE_GRATIS
        )

        pagos_anteriores = historico_pagos[id_cliente]
        variacao = (
            round((valor_total / pagos_anteriores[-1] - 1) * 100, 2)
            if pagos_anteriores else np.nan
        )

        pedido = {
            "id_pedido": id_pedido,
            "id_cliente": id_cliente,
            "data_pedido": d,
            "canal": sortear(PROB_CANAL),
            "tipo_cliente": tipo_cliente,
            "pedidos_anteriores": len(pagos_anteriores),
            "qtd_itens": len(itens),
            "valor_total": valor_total,
            "pct_desconto": pct_desconto,
            "uf_destino": uf,
            "regiao": regiao,
            "tipo_frete": tipo_frete,
            "frete_gratis": frete_gratis,
            "valor_frete": calcular_valor_frete(tipo_frete, grupo, frete_gratis),
            "prazo_entrega_dias": calcular_prazo(tipo_frete, grupo, d),
            "forma_pagamento": sortear(PROB_PAGAMENTO),
            "variacao_pedido_anterior_pct": variacao,
        }

        if i in indices_aguardando:
            pedido.update(venda_sucesso=None, motivo_insucesso=None, status_pedido="Aguardando pagamento")
        elif rng.random() < calcular_probabilidade(pedido):
            pedido.update(venda_sucesso=1, motivo_insucesso=None, status_pedido="Pago")
            historico_pagos[id_cliente].append(valor_total)
        else:
            pedido.update(
                venda_sucesso=0,
                motivo_insucesso=sortear_motivo_insucesso(pedido["forma_pagamento"]),
                status_pedido="Não pago",
            )

        pedidos.append(pedido)
        itens_pedidos.extend(
            {"id_pedido": id_pedido, "id_produto": id_prod, "quantidade": q, "preco_unitario": preco}
            for id_prod, q, preco in itens
        )

    df_pedidos = pd.DataFrame(pedidos)
    df_pedidos["status_entrega"] = definir_status_entrega(df_pedidos)
    return df_pedidos, pd.DataFrame(itens_pedidos)


def definir_status_entrega(pedidos: pd.DataFrame) -> pd.Series:
    status = pd.Series([None] * len(pedidos), index=pedidos.index, dtype=object)
    pagos = pedidos["venda_sucesso"] == 1
    status[pagos] = "Entregue"

    # Outubro/2026: entre 40% e 60% dos pagos ainda em trânsito (os mais recentes)
    pagos_andamento = pedidos[pagos & pedidos["data_pedido"].map(eh_mes_em_andamento)]
    pagos_andamento = pagos_andamento.sort_values("data_pedido")
    pct_transito = rng.uniform(*FAIXA_EM_TRANSITO_OUT)
    qtd_transito = int(round(len(pagos_andamento) * pct_transito))
    if qtd_transito:
        status[pagos_andamento.index[-qtd_transito:]] = "Em trânsito"
    return status


# =============================================================================
# BASE PARA O MODELO
# =============================================================================

def montar_base_ml(pedidos: pd.DataFrame) -> pd.DataFrame:
    base = pedidos.copy()
    base["mes"] = base["data_pedido"].map(lambda d: d.month)
    base["quinzena"] = base["data_pedido"].map(lambda d: 1 if d.day <= 15 else 2)
    base["venda_sucesso"] = base["venda_sucesso"].astype("Int64")

    colunas = [
        "id_pedido", "data_pedido", "mes", "quinzena", "canal", "tipo_cliente",
        "pedidos_anteriores", "qtd_itens", "valor_total", "pct_desconto",
        "uf_destino", "regiao", "tipo_frete", "valor_frete", "prazo_entrega_dias",
        "forma_pagamento", "variacao_pedido_anterior_pct",
        "venda_sucesso", "motivo_insucesso",
    ]
    return base[colunas]


# =============================================================================
# RESUMO PARA VALIDAÇÃO
# =============================================================================

def imprimir_resumo(base: pd.DataFrame) -> None:
    fechados = base[base["venda_sucesso"].notna()]
    print(f"Pedidos: {len(base)} | fechados: {len(fechados)} | "
          f"aguardando: {base['venda_sucesso'].isna().sum()}")
    print(f"Conversão geral: {fechados['venda_sucesso'].mean():.1%}")

    por_mes = base.groupby(base["data_pedido"].map(lambda d: (d.year, d.month))).size()
    print(f"Pedidos por mês: mín {por_mes.min()} | máx {por_mes.max()}")

    for coluna in ["forma_pagamento", "tipo_frete", "tipo_cliente", "canal", "regiao"]:
        taxa = fechados.groupby(coluna)["venda_sucesso"].agg(["mean", "size"])
        taxa["mean"] = taxa["mean"].map("{:.1%}".format)
        print(f"\nConversão por {coluna}:\n{taxa.rename(columns={'mean': 'conversao', 'size': 'pedidos'})}")


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main() -> None:
    catalogo = carregar_catalogo()
    clientes, perfil = gerar_clientes()
    definir_produtos_preferidos(perfil, clientes, catalogo)
    pedidos, produtos_pedidos = gerar_pedidos(clientes, perfil, catalogo)
    base_ml = montar_base_ml(pedidos)

    colunas_pedidos = [
        "id_pedido", "id_cliente", "data_pedido", "canal", "uf_destino", "tipo_frete",
        "valor_frete", "prazo_entrega_dias", "forma_pagamento", "pct_desconto",
        "valor_total", "status_pedido", "status_entrega", "venda_sucesso", "motivo_insucesso",
    ]
    pedidos_saida = pedidos[colunas_pedidos].copy()
    pedidos_saida["venda_sucesso"] = pedidos_saida["venda_sucesso"].astype("Int64")

    CAMINHO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(CAMINHO_SAIDA, engine="openpyxl") as writer:
        clientes.to_excel(writer, sheet_name="clientes", index=False)
        catalogo.to_excel(writer, sheet_name="produtos", index=False)
        pedidos_saida.to_excel(writer, sheet_name="pedidos", index=False)
        produtos_pedidos.to_excel(writer, sheet_name="produtos_pedidos", index=False)
        base_ml.to_excel(writer, sheet_name="base_ml", index=False)

    imprimir_resumo(base_ml)
    print(f"\nArquivo gerado: {CAMINHO_SAIDA}")


if __name__ == "__main__":
    main()