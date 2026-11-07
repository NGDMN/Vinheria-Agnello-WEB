"""
Vinheria Agnello - PBL Fase 3
Dicionário de dados: descrição de cada coluna, gravado na aba 'dicionario' do .xlsx.
"""

import pandas as pd

import parametros as cfg

ENTRADA, ROTULO, FILTRO, FORA, IDENTIFICADOR = (
    "Entrada do modelo", "Rótulo", "Filtro / dashboard", "Fora do modelo (vazamento)", "Identificador",
)


def _valores(coluna: str) -> str:
    dominio = cfg.DOMINIOS.get(coluna)
    return ", ".join(str(v) for v in sorted(dominio, key=str)) if dominio else ""


# (tabela, coluna, tipo, descrição, papel no modelo, valores aceitos)
DICIONARIO = [
    # ----------------------------------------------------------------- clientes
    ("clientes", "id_cliente", "Inteiro", "Identificador único do cliente", "", ""),
    ("clientes", "tipo_cliente", "Texto", "PF = pessoa física (varejo); PJ = pessoa jurídica (atacado: "
     "restaurantes, empórios)", "", _valores("tipo_cliente")),
    ("clientes", "uf", "Texto", "UF do endereço de cadastro", "", "27 UFs"),
    ("clientes", "data_cadastro", "Data", "Data de criação da conta (cadastro só para maiores de 18 anos)", "", ""),

    # ----------------------------------------------------------------- produtos
    ("produtos", "id_produto", "Inteiro", "Identificador do vinho (id_vinho da TB_Vinho)", "", ""),
    ("produtos", "nome_vinho", "Texto", "Nome comercial do vinho", "", ""),
    ("produtos", "tipo_vinho", "Texto", "Tipo do vinho, conforme TB_Tipo_Vinho", "", _valores("tipo_vinho")),
    ("produtos", "pais_origem", "Texto", "País de origem", "", ""),
    ("produtos", "preco_unitario", "Decimal (R$)", "Preço de catálogo atual", "", "> 0"),

    # --------------------------------------------------------- rupturas_estoque
    ("rupturas_estoque", "id_produto", "Inteiro", "Vinho sem estoque no período", "", ""),
    ("rupturas_estoque", "data_inicio", "Data", "Primeiro dia sem estoque", "", ""),
    ("rupturas_estoque", "data_fim", "Data", "Último dia sem estoque (inclusive)", "", ""),
    ("rupturas_estoque", "tipo_ruptura", "Texto", "Temporária = estoque já reposto; Atual = ainda esgotado",
     "", _valores("tipo_ruptura")),

    # ------------------------------------------------------------------ pedidos
    ("pedidos", "id_pedido", "Inteiro", "Identificador único do pedido (checkout iniciado)", "", ""),
    ("pedidos", "id_cliente", "Inteiro", "Cliente que fez o pedido", "", ""),
    ("pedidos", "data_pedido", "Data", "Data do checkout", "", f"{cfg.DATA_INICIO:%d/%m/%Y} a {cfg.DATA_FIM:%d/%m/%Y}"),
    ("pedidos", "canal", "Texto", "Canal digital do checkout (loja física fora da base)", "", _valores("canal")),
    ("pedidos", "uf_destino", "Texto", "UF de entrega (igual à UF do cadastro)", "", "27 UFs"),
    ("pedidos", "tipo_frete", "Texto", "Modal de entrega. Same-Day só Sul/Sudeste; Retirada só clientes de "
     f"{cfg.UF_LOJA}", "", _valores("tipo_frete")),
    ("pedidos", "valor_frete", "Decimal (R$)", "Valor cobrado de frete. 0 = Retirada ou frete grátis "
     f"(Econômico em Sul/Sudeste a partir de R$ {cfg.VALOR_MIN_FRETE_GRATIS:.2f})", "", ">= 0"),
    ("pedidos", "prazo_entrega_dias", "Inteiro", "Prazo prometido no checkout; maior em dezembro e na semana "
     "da Black Friday", "", f"0 a {cfg.PRAZO_MAXIMO_DIAS}"),
    ("pedidos", "forma_pagamento", "Texto", "Meio de pagamento escolhido", "", _valores("forma_pagamento")),
    ("pedidos", "pct_desconto", "Decimal (%)", "Desconto aplicado sobre os produtos", "", _valores("pct_desconto")),
    ("pedidos", "valor_total", "Decimal (R$)", "Valor dos produtos com desconto, sem frete", "", "> 0"),
    ("pedidos", "status_pedido", "Texto", "Situação do pagamento", "", _valores("status_pedido")),
    ("pedidos", "status_entrega", "Texto", "Situação da entrega; vazio quando não pago", "",
     _valores("status_entrega")),
    ("pedidos", "venda_sucesso", "Inteiro", "1 = pago; 0 = não pago; vazio = aguardando pagamento", "", "0, 1, vazio"),
    ("pedidos", "motivo_insucesso", "Texto", "Motivo do não pagamento; vazio quando pago ou aguardando", "",
     _valores("motivo_insucesso")),

    # --------------------------------------------------------- produtos_pedidos
    ("produtos_pedidos", "id_pedido", "Inteiro", "Pedido ao qual o item pertence", "", ""),
    ("produtos_pedidos", "id_produto", "Inteiro", "Vinho comprado", "", ""),
    ("produtos_pedidos", "quantidade", "Inteiro", "Garrafas do vinho no pedido", "", ">= 1"),
    ("produtos_pedidos", "preco_unitario", "Decimal (R$)", "Preço no momento da venda (histórico, independe do "
     "catálogo atual)", "", "> 0"),

    # ------------------------------------------------------------------ base_ml
    # ------------------------------------------------------------------ regioes
    ("regioes", "uf", "Texto", "Sigla da UF: liga com pedidos.uf_destino no dashboard", "", "27 UFs"),
    ("regioes", "regiao", "Texto", "Região geográfica da UF: filtro de região do dashboard", FILTRO,
     _valores("regiao")),

    ("base_ml", "id_pedido", "Inteiro", "Liga a linha ao pedido", IDENTIFICADOR, ""),
    ("base_ml", "data_pedido", "Data", "Filtro de período no dashboard; origem de mes e quinzena", FILTRO, ""),
    ("base_ml", "mes", "Inteiro", "Mês do pedido: sazonalidade de datas festivas", ENTRADA, "1 a 12"),
    ("base_ml", "quinzena", "Inteiro", "1 = dias 1 a 15; 2 = dias 16 em diante: poder de compra", ENTRADA, "1, 2"),
    ("base_ml", "canal", "Texto", "Site ou App: experiências de checkout diferentes", ENTRADA, _valores("canal")),
    ("base_ml", "tipo_cliente", "Texto", "PF ou PJ: ticket e comportamento de pagamento diferentes", ENTRADA,
     _valores("tipo_cliente")),
    ("base_ml", "pedidos_anteriores", "Inteiro", "Pedidos pagos do cliente antes deste: recorrência indica "
     "confiança", ENTRADA, ">= 0"),
    ("base_ml", "qtd_itens", "Inteiro", "Vinhos distintos no pedido: pedidos compostos", ENTRADA, ">= 1"),
    ("base_ml", "valor_total", "Decimal (R$)", "Valor dos produtos sem frete: ticket alto gera hesitação",
     ENTRADA, "> 0"),
    ("base_ml", "pct_desconto", "Decimal (%)", "Desconto incentiva o fechamento", ENTRADA, _valores("pct_desconto")),
    ("base_ml", "uf_destino", "Texto", "Mapa e filtro do dashboard; fora do modelo por excesso de categorias",
     FILTRO, "27 UFs"),
    ("base_ml", "regiao", "Texto", "Região da UF: agrupa o efeito de distância em frete e prazo", ENTRADA,
     _valores("regiao")),
    ("base_ml", "tipo_frete", "Texto", "Modal de entrega: quanto melhor, maior a chance de fechar", ENTRADA,
     _valores("tipo_frete")),
    ("base_ml", "valor_frete", "Decimal (R$)", "Frete é a causa clássica de abandono; 0 = grátis ou retirada",
     ENTRADA, ">= 0"),
    ("base_ml", "prazo_entrega_dias", "Inteiro", "Prazo prometido: a partir de 7 dias reduz a conversão",
     ENTRADA, f"0 a {cfg.PRAZO_MAXIMO_DIAS}"),
    ("base_ml", "forma_pagamento", "Texto", "Conversão varia muito por meio de pagamento", ENTRADA,
     _valores("forma_pagamento")),
    ("base_ml", "variacao_pedido_anterior_pct", "Decimal (%)", "Variação do valor sobre o último pedido pago "
     "do cliente; vazio no primeiro pedido", ENTRADA, "> -100"),
    ("base_ml", "venda_sucesso", "Inteiro", "O que o modelo prevê: 1 = pago; 0 = não pago; vazio = aguardando "
     "(fora do treino, recebe a previsão)", ROTULO, "0, 1, vazio"),
    ("base_ml", "motivo_insucesso", "Texto", "Consequência do resultado: entregaria a resposta ao modelo",
     FORA, _valores("motivo_insucesso")),
]


def montar_dicionario() -> pd.DataFrame:
    dicionario = pd.DataFrame(DICIONARIO, columns=[
        "tabela", "coluna", "tipo", "descricao", "papel_no_modelo", "valores_aceitos",
    ])
    _conferir_cobertura(dicionario)
    return dicionario


def _conferir_cobertura(dicionario: pd.DataFrame) -> None:
    """Garante que toda coluna das tabelas está documentada, e nada além delas."""
    documentadas = set(zip(dicionario["tabela"], dicionario["coluna"]))
    esperadas = {(t, c) for t, colunas in cfg.COLUNAS.items() for c in colunas}
    faltando, sobrando = esperadas - documentadas, documentadas - esperadas
    if faltando or sobrando:
        raise ValueError(
            f"Dicionário de dados desatualizado. Sem descrição: {sorted(faltando)}. "
            f"Colunas inexistentes: {sorted(sobrando)}."
        )