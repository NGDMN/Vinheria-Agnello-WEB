"""
Vinheria Agnello - PBL Fase 3
Parâmetros centralizados do pipeline (geração, tratamento, validação e modelo).

Qualquer regra de negócio usada em mais de um script fica aqui, para que
gerador e validação nunca divirjam.
"""

from datetime import date, timedelta
from pathlib import Path

VERSAO_PIPELINE = "1.0.0"

# =============================================================================
# CAMINHOS (relativos a este arquivo)
# =============================================================================

PASTA_BASE = Path(__file__).resolve().parent
PASTA_DADOS = PASTA_BASE / "data"
PASTA_RESULTADOS = PASTA_BASE / "resultados"

CAMINHO_CATALOGO = PASTA_DADOS / "tb_vinho.csv"
CAMINHO_SAIDA = PASTA_DADOS / "vinheria_fase3.xlsx"
CAMINHO_RELATORIO = PASTA_RESULTADOS / "relatorio_validacao.txt"

# =============================================================================
# GERAÇÃO
# =============================================================================

SEMENTE = 42

DATA_INICIO = date(2024, 10, 1)
DATA_FIM = date(2026, 10, 19)
MES_EM_ANDAMENTO = (DATA_FIM.year, DATA_FIM.month)

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

# Rupturas de estoque: produto fica no catálogo, mas não pode ser vendido no período
RUPTURAS_POR_PRODUTO = (1, 2)            # quantidade de janelas aleatórias por produto
DURACAO_RUPTURA_DIAS = (14, 42)          # 2 a 6 semanas
RUPTURAS_ATUAIS = {4: date(2026, 8, 1)}  # Miolo Lote 43: esgotado de agosto/2026 até o fim da base

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

# Mês em andamento (outubro/2026)
PCT_AGUARDANDO_PAGAMENTO_OUT = 0.40
FAIXA_EM_TRANSITO_OUT = (0.40, 0.60)

# Probabilidade de pagamento (pontos percentuais)
PROB_BASE = 70
PROB_PISO = 20
PROB_TETO = 90

# =============================================================================
# DOMÍNIOS (valores aceitos por coluna categórica)
# =============================================================================

DOMINIOS = {
    "tipo_cliente": {"PF", "PJ"},
    "canal": set(PROB_CANAL),
    "forma_pagamento": set(PROB_PAGAMENTO),
    "tipo_frete": set(PESO_TIPO_FRETE),
    "pct_desconto": set(PROB_DESCONTO),
    "uf": set(UFS),
    "uf_destino": set(UFS),
    "regiao": set(GRUPO_LOGISTICO),
    "tipo_vinho": set(TIPOS_VINHO.values()),
    "status_pedido": {"Pago", "Não pago", "Aguardando pagamento"},
    "status_entrega": {"Entregue", "Em trânsito"},
    "motivo_insucesso": {"Pagamento recusado", "PIX expirado", "Boleto expirado", "Desistência"},
    "tipo_ruptura": {"Temporária", "Atual"},
}

MOTIVO_POR_PAGAMENTO = {  # motivo específico permitido para cada forma de pagamento
    "Cartão": "Pagamento recusado",
    "PIX": "PIX expirado",
    "Boleto": "Boleto expirado",
}

# =============================================================================
# ESQUEMA DAS TABELAS
# =============================================================================

COLUNAS = {
    "clientes": ["id_cliente", "tipo_cliente", "uf", "data_cadastro"],
    "produtos": ["id_produto", "nome_vinho", "tipo_vinho", "pais_origem", "preco_unitario"],
    "rupturas_estoque": ["id_produto", "data_inicio", "data_fim", "tipo_ruptura"],
    "pedidos": [
        "id_pedido", "id_cliente", "data_pedido", "canal", "uf_destino", "tipo_frete",
        "valor_frete", "prazo_entrega_dias", "forma_pagamento", "pct_desconto",
        "valor_total", "status_pedido", "status_entrega", "venda_sucesso", "motivo_insucesso",
    ],
    "produtos_pedidos": ["id_pedido", "id_produto", "quantidade", "preco_unitario"],
    "base_ml": [
        "id_pedido", "data_pedido", "mes", "quinzena", "canal", "tipo_cliente",
        "pedidos_anteriores", "qtd_itens", "valor_total", "pct_desconto",
        "uf_destino", "regiao", "tipo_frete", "valor_frete", "prazo_entrega_dias",
        "forma_pagamento", "variacao_pedido_anterior_pct",
        "venda_sucesso", "motivo_insucesso",
    ],
}

TIPOS_DATA = {
    "clientes": ["data_cadastro"],
    "rupturas_estoque": ["data_inicio", "data_fim"],
    "pedidos": ["data_pedido"],
    "base_ml": ["data_pedido"],
}
TIPOS_INTEIROS = {
    "clientes": ["id_cliente"],
    "produtos": ["id_produto"],
    "rupturas_estoque": ["id_produto"],
    "pedidos": ["id_pedido", "id_cliente", "prazo_entrega_dias"],
    "produtos_pedidos": ["id_pedido", "id_produto", "quantidade"],
    "base_ml": ["id_pedido", "mes", "quinzena", "pedidos_anteriores", "qtd_itens", "prazo_entrega_dias"],
}
TIPOS_MONETARIOS = {
    "produtos": ["preco_unitario"],
    "pedidos": ["valor_frete", "valor_total"],
    "produtos_pedidos": ["preco_unitario"],
    "base_ml": ["valor_total", "valor_frete"],
}
TIPOS_DECIMAIS = {
    "pedidos": ["pct_desconto", "venda_sucesso"],
    "base_ml": ["pct_desconto", "variacao_pedido_anterior_pct", "venda_sucesso"],
}

CHAVES = {  # colunas que não podem se repetir
    "clientes": ["id_cliente"],
    "produtos": ["id_produto"],
    "pedidos": ["id_pedido"],
    "produtos_pedidos": ["id_pedido", "id_produto"],
    "base_ml": ["id_pedido"],
}

COLUNAS_ANULAVEIS = {  # únicas colunas que podem ficar vazias, com o motivo
    "pedidos": {"status_entrega", "venda_sucesso", "motivo_insucesso"},
    "base_ml": {"venda_sucesso", "motivo_insucesso", "variacao_pedido_anterior_pct"},
}

# =============================================================================
# MODELO
# =============================================================================

ROTULO = "venda_sucesso"

COLUNAS_ENTRADA_MODELO = [
    "mes", "quinzena", "canal", "tipo_cliente", "pedidos_anteriores", "qtd_itens",
    "valor_total", "pct_desconto", "regiao", "tipo_frete", "valor_frete",
    "prazo_entrega_dias", "forma_pagamento", "variacao_pedido_anterior_pct",
]

COLUNAS_PROIBIDAS_MODELO = {  # posteriores ao checkout ou identificadores: vazam a resposta
    "id_pedido", "data_pedido", "uf_destino", "motivo_insucesso",
    "status_pedido", "status_entrega", ROTULO,
}

# =============================================================================
# CALIBRAÇÃO (geram ALERTA, não interrompem)
# =============================================================================

FAIXA_CONVERSAO_ESPERADA = (0.65, 0.85)
FAIXA_PCT_PJ_CLIENTES = (0.20, 0.40)
PROPORCAO_MINIMA_CLASSE = 0.15
PRAZO_MAXIMO_DIAS = max(f[1] for f in PRAZO_DIAS.values()) + max(ACRESCIMO_PRAZO_PICO.values())
TOLERANCIA_VALOR = 0.05   # R$, para arredondamentos em cálculos de valor


# =============================================================================
# REGRAS DE CALENDÁRIO (usadas pelo gerador e pela validação)
# =============================================================================

def black_friday(ano: int) -> date:
    primeiro_nov = date(ano, 11, 1)
    primeira_quinta = primeiro_nov + timedelta(days=(3 - primeiro_nov.weekday()) % 7)
    return primeira_quinta + timedelta(days=22)   # sexta após a 4ª quinta-feira


def eh_periodo_pico(d: date) -> bool:
    """Dezembro ou semana da Black Friday (segunda a domingo): prazos maiores."""
    if d.month == 12:
        return True
    bf = black_friday(d.year)
    return bf - timedelta(days=4) <= d <= bf + timedelta(days=2)


def eh_mes_em_andamento(d: date) -> bool:
    return (d.year, d.month) == MES_EM_ANDAMENTO