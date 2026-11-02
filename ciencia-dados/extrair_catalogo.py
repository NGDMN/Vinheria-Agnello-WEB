"""
Vinheria Agnello - PBL Fase 3
Extract: lê a TB_Vinho no Azure SQL e grava o snapshot em data/tb_vinho.csv.

Só precisa ser executado quando o catálogo do banco mudar. O gerar_base.py
consome o CSV versionado, então o restante do grupo e o professor rodam o
projeto sem acesso ao banco.

Credenciais: reutiliza o .env da raiz do repositório (o mesmo da aplicação Web),
com DB_URL (JDBC), DB_USER e DB_PASSWORD. Use o usuário vinheria_app, com
permissões mínimas, nunca o administrador.

Pré-requisitos:
    - pip install pyodbc
    - Microsoft ODBC Driver 18 for SQL Server instalado no Windows
    - IP liberado no firewall do Azure SQL
"""

import os
import re
import sys
import time
from pathlib import Path

import pandas as pd

import parametros as cfg

CAMINHO_ENV = cfg.PASTA_BASE.parent / ".env"   # raiz do repositório Vinheria-Agnello-WEB
VARIAVEIS = ["DB_URL", "DB_USER", "DB_PASSWORD"]
DRIVER_PADRAO = "ODBC Driver 18 for SQL Server"
TENTATIVAS = 2
ESPERA_ENTRE_TENTATIVAS_S = 30   # banco serverless pode estar pausado

CONSULTA = """
    SELECT id_vinho, nome, id_tipo, pais, preco, ativo
    FROM dbo.TB_Vinho
    ORDER BY id_vinho
"""


def carregar_env(caminho: Path) -> None:
    """Lê KEY=VALOR do .env sem sobrescrever variáveis já definidas no sistema."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def ler_url_jdbc(url: str) -> tuple[str, str, str]:
    """Extrai servidor, porta e banco de jdbc:sqlserver://servidor:porta;database=banco;..."""
    correspondencia = re.match(r"jdbc:sqlserver://([^:;/]+)(?::(\d+))?;?(.*)", url.strip(), re.IGNORECASE)
    if not correspondencia:
        raise RuntimeError("DB_URL fora do formato esperado: jdbc:sqlserver://servidor:porta;database=banco;...")
    servidor, porta, propriedades = correspondencia.groups()
    opcoes = {}
    for item in propriedades.split(";"):
        if "=" in item:
            chave, valor = item.split("=", 1)
            opcoes[chave.strip().lower()] = valor.strip()
    banco = opcoes.get("database") or opcoes.get("databasename")
    if not banco:
        raise RuntimeError("DB_URL sem o nome do banco (propriedade database=...).")
    return servidor, porta or "1433", banco


def montar_conexao() -> str:
    carregar_env(CAMINHO_ENV)
    faltando = [v for v in VARIAVEIS if not os.environ.get(v)]
    if faltando:
        raise RuntimeError(
            f"Variáveis ausentes ou vazias: {', '.join(faltando)}. "
            f"Preencha-as no .env da raiz do repositório ({CAMINHO_ENV})."
        )
    servidor, porta, banco = ler_url_jdbc(os.environ["DB_URL"])
    return (
        f"DRIVER={{{os.environ.get('DB_ODBC_DRIVER', DRIVER_PADRAO)}}};"
        f"SERVER=tcp:{servidor},{porta};"
        f"DATABASE={banco};"
        f"UID={os.environ['DB_USER']};"
        f"PWD={os.environ['DB_PASSWORD']};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )


def explicar_erro(erro: Exception) -> str:
    texto = str(erro)
    if "IM002" in texto:
        return (f"Driver ODBC não encontrado. Instale o '{DRIVER_PADRAO}' "
                f"ou informe outro em DB_ODBC_DRIVER no .env.")
    if "40615" in texto:
        return ("IP bloqueado pelo firewall do Azure SQL. Libere seu IP em: servidor SQL > Networking > "
                "Firewall rules.")
    if "18456" in texto or "28000" in texto:
        return "Usuário ou senha inválidos. Confira DB_USER e DB_PASSWORD no .env."
    if "229" in texto and "SELECT" in texto.upper():
        return "O usuário não tem permissão de SELECT na TB_Vinho."
    if "HYT00" in texto or "timeout" in texto.lower():
        return "Tempo de conexão esgotado. O banco serverless pode estar pausado; tente de novo em 1 minuto."
    return f"Erro de conexão: {type(erro).__name__}. Detalhe técnico: {texto[:200]}"


def extrair() -> pd.DataFrame:
    try:
        import pyodbc
    except ImportError as erro:
        raise RuntimeError("Biblioteca pyodbc não instalada. Rode: pip install pyodbc") from erro

    conexao_str = montar_conexao()
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with pyodbc.connect(conexao_str, readonly=True) as conexao:
                cursor = conexao.cursor()
                cursor.execute(CONSULTA)
                colunas = [c[0] for c in cursor.description]
                return pd.DataFrame.from_records(cursor.fetchall(), columns=colunas)
        except pyodbc.Error as erro:
            mensagem = explicar_erro(erro)   # nunca imprime a string de conexão (contém a senha)
            if tentativa < TENTATIVAS and "pausado" in mensagem:
                print(f"{mensagem} Nova tentativa em {ESPERA_ENTRE_TENTATIVAS_S}s...")
                time.sleep(ESPERA_ENTRE_TENTATIVAS_S)
                continue
            raise RuntimeError(mensagem) from None
    raise RuntimeError("Não foi possível extrair o catálogo.")


def gravar(catalogo: pd.DataFrame) -> None:
    if catalogo.empty:
        raise RuntimeError("A TB_Vinho voltou vazia. O CSV atual foi mantido.")
    cfg.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    temporario = cfg.CAMINHO_CATALOGO.with_suffix(".tmp")
    catalogo.to_csv(temporario, sep=";", index=False, encoding="utf-8-sig")
    temporario.replace(cfg.CAMINHO_CATALOGO)   # só substitui o CSV se a gravação terminou


def main() -> int:
    try:
        catalogo = extrair()
        gravar(catalogo)
    except RuntimeError as erro:
        print(f"\nERRO na extração: {erro}")
        return 1
    print(f"Catálogo extraído: {len(catalogo)} vinho(s) -> {cfg.CAMINHO_CATALOGO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())