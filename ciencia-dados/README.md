# Ciência de dados — PBL Fase 3

Base de vendas simulada, modelo de classificação (o pedido será pago?) e insumos do dashboard.

## Pré-requisitos
- Python 3.10+
- Power BI Desktop (dashboard)

## Ambiente
```powershell
cd ciencia-dados
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Execução
```powershell
python gerar_base.py   # data/vinheria_fase3.xlsx e resultados/relatorio_validacao.txt
python modelo.py       # resultados/: metricas_modelo.txt, regras_arvore.txt, previsoes.csv, figuras/
```

`extrair_catalogo.py` só é necessário se a TB_Vinho mudar. Ele exige o `.env` da raiz, `pyodbc`
e o ODBC Driver 18 for SQL Server. O snapshot `data/tb_vinho.csv` já está versionado.

## Estrutura
| Arquivo | Papel |
|---|---|
| `parametros.py` | Regras de negócio, esquema e caminhos (fonte única) |
| `gerar_base.py` | ETL: catálogo → simulação → tratamento → validação → .xlsx |
| `transformacao.py` | Tratamento das tabelas e derivação da base_ml |
| `validacao.py` | Regras de validação e relatório |
| `dicionario_dados.py` | Aba `dicionario` do .xlsx |
| `modelo.py` | Árvore de decisão, métricas e previsões |
| `dashboard/` | Projeto Power BI (PBIP); a entrega é exportada em .pbix |