"""
Vinheria Agnello - PBL Fase 3
Modelo de classificação: prevê se um pedido será pago (venda_sucesso).

    1. Lê a aba base_ml e valida (para se houver falha crítica)
    2. Separa pedidos com rótulo (treino/teste) dos aguardando pagamento (previsão)
    3. Divide 80/20 estratificado
    4. Ajusta a árvore de decisão com validação cruzada (profundidade e tamanho mínimo da folha)
    5. Avalia no teste e compara com a linha de base e com uma Random Forest
    6. Gera regras, figuras e previsões para o dashboard

Saídas em resultados/:
    metricas_modelo.txt, regras_arvore.txt, previsoes.csv
    figuras/matriz_confusao.png, figuras/arvore_decisao.png, figuras/importancia_variaveis.png
"""

import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")   # gera os PNGs sem abrir janela
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, balanced_accuracy_score,
                             classification_report, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree

import parametros as cfg
from validacao import ErroValidacao, validar_base_ml

# =============================================================================
# PARÂMETROS DO MODELO
# =============================================================================

PROPORCAO_TESTE = 0.20
DOBRAS_VALIDACAO = 5

COLUNAS_CATEGORICAS = ["canal", "tipo_cliente", "regiao", "tipo_frete", "forma_pagamento"]
COLUNAS_NUMERICAS = [c for c in cfg.COLUNAS_ENTRADA_MODELO if c not in COLUNAS_CATEGORICAS]

# Busca de hiperparâmetros: árvores rasas e folhas grandes geram regras legíveis e evitam decorar o treino
GRADE_ARVORE = {
    "modelo__max_depth": [3, 4, 5, 6],
    "modelo__min_samples_leaf": [10, 20, 30],
}
GRADE_FLORESTA = {
    "modelo__max_depth": [4, 6, 8],
    "modelo__min_samples_leaf": [5, 10, 20],
}

# Classe de interesse do negócio: o pedido que NÃO será pago (permite agir antes de perder a venda)
NOMES_CLASSES = {0: "Não pago", 1: "Pago"}
LIMITE_RISCO_ALTO = 0.50   # probabilidade de não pagamento
LIMITE_RISCO_MEDIO = 0.30

PASTA_FIGURAS = cfg.PASTA_RESULTADOS / "figuras"
CAMINHO_METRICAS = cfg.PASTA_RESULTADOS / "metricas_modelo.txt"
CAMINHO_REGRAS = cfg.PASTA_RESULTADOS / "regras_arvore.txt"
CAMINHO_PREVISOES = cfg.PASTA_RESULTADOS / "previsoes.csv"


class ErroModelo(Exception):
    """Falha esperada e explicável (arquivo ausente, aberto ou base insuficiente)."""


# =============================================================================
# DADOS
# =============================================================================

def carregar_base() -> pd.DataFrame:
    if not cfg.CAMINHO_SAIDA.exists():
        raise ErroModelo(f"Base não encontrada em {cfg.CAMINHO_SAIDA}. Rode gerar_base.py primeiro.")
    try:
        return pd.read_excel(cfg.CAMINHO_SAIDA, sheet_name="base_ml")
    except PermissionError:
        raise ErroModelo(f"Não foi possível ler {cfg.CAMINHO_SAIDA.name}. Feche o arquivo no Excel.") from None
    except ValueError:
        raise ErroModelo(f"A aba base_ml não existe em {cfg.CAMINHO_SAIDA.name}. Rode gerar_base.py.") from None


def separar(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rotulados = base[base[cfg.ROTULO].notna()].copy()
    aguardando = base[base[cfg.ROTULO].isna()].copy()
    rotulados[cfg.ROTULO] = rotulados[cfg.ROTULO].astype(int)

    menor_classe = rotulados[cfg.ROTULO].value_counts().min()
    if rotulados[cfg.ROTULO].nunique() < 2 or menor_classe < DOBRAS_VALIDACAO * 2:
        raise ErroModelo("Base sem exemplos suficientes das duas classes para treinar e validar o modelo.")
    return rotulados, aguardando


# =============================================================================
# PIPELINES
# =============================================================================

def montar_preprocessamento() -> ColumnTransformer:
    return ColumnTransformer([
        # variacao_pedido_anterior_pct é vazia no primeiro pedido: 0 = sem variação
        # (o caso já fica identificado por pedidos_anteriores = 0)
        ("num", SimpleImputer(strategy="constant", fill_value=0), COLUNAS_NUMERICAS),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), COLUNAS_CATEGORICAS),
    ], verbose_feature_names_out=False)


def montar_pipeline(modelo) -> Pipeline:
    return Pipeline([("preparo", montar_preprocessamento()), ("modelo", modelo)])


def ajustar(nome: str, modelo, grade: dict, X: pd.DataFrame, y: pd.Series) -> GridSearchCV:
    """Validação cruzada estratificada; escolhe a combinação com maior AUC média."""
    busca = GridSearchCV(
        montar_pipeline(modelo),
        grade,
        cv=StratifiedKFold(n_splits=DOBRAS_VALIDACAO, shuffle=True, random_state=cfg.SEMENTE),
        scoring={"auc": "roc_auc", "acuracia": "accuracy", "f1_nao_pago": "f1_macro"},
        refit="auc",
    )
    busca.fit(X, y)
    print(f"   {nome}: melhor {formatar_parametros(busca.best_params_)} | "
          f"AUC média na validação cruzada = {busca.best_score_:.3f}")
    return busca


def formatar_parametros(parametros: dict) -> str:
    return ", ".join(f"{k.replace('modelo__', '')}={v}" for k, v in parametros.items())


# =============================================================================
# AVALIAÇÃO
# =============================================================================

def avaliar(modelo, X: pd.DataFrame, y: pd.Series) -> dict:
    previsto = modelo.predict(X)
    prob_pago = modelo.predict_proba(X)[:, 1]
    return {
        "Acurácia": accuracy_score(y, previsto),
        "Acurácia balanceada": balanced_accuracy_score(y, previsto),
        "Precisão (Não pago)": precision_score(y, previsto, pos_label=0, zero_division=0),
        "Recall (Não pago)": recall_score(y, previsto, pos_label=0, zero_division=0),
        "F1 (Não pago)": f1_score(y, previsto, pos_label=0, zero_division=0),
        "Precisão (Pago)": precision_score(y, previsto, pos_label=1, zero_division=0),
        "Recall (Pago)": recall_score(y, previsto, pos_label=1, zero_division=0),
        "AUC": roc_auc_score(y, prob_pago) if len(np.unique(prob_pago)) > 1 else 0.5,
    }


def tabela_resultados_cv(busca: GridSearchCV) -> pd.DataFrame:
    r = pd.DataFrame(busca.cv_results_)
    tabela = pd.DataFrame({
        "parametros": r["params"].map(formatar_parametros),
        "auc_media": r["mean_test_auc"].round(3),
        "auc_desvio": r["std_test_auc"].round(3),
        "acuracia_media": r["mean_test_acuracia"].round(3),
    })
    return tabela.sort_values("auc_media", ascending=False).reset_index(drop=True)


def importancias(pipeline: Pipeline) -> pd.Series:
    nomes = pipeline.named_steps["preparo"].get_feature_names_out()
    valores = pipeline.named_steps["modelo"].feature_importances_
    return pd.Series(valores, index=nomes).sort_values(ascending=False)


# =============================================================================
# SAÍDAS
# =============================================================================

def salvar_matriz_confusao(y: pd.Series, previsto: np.ndarray) -> None:
    fig, eixo = plt.subplots(figsize=(5, 4.5))
    ConfusionMatrixDisplay(confusion_matrix(y, previsto, labels=[0, 1]),
                           display_labels=[NOMES_CLASSES[0], NOMES_CLASSES[1]]).plot(
        ax=eixo, cmap="Reds", colorbar=False, values_format="d")
    eixo.set_title("Matriz de confusão — árvore de decisão (teste)")
    eixo.set_xlabel("Previsto")
    eixo.set_ylabel("Real")
    fig.tight_layout()
    fig.savefig(PASTA_FIGURAS / "matriz_confusao.png", dpi=150)
    plt.close(fig)


def salvar_arvore(pipeline: Pipeline) -> None:
    arvore = pipeline.named_steps["modelo"]
    fig, eixo = plt.subplots(figsize=(min(6 * arvore.get_depth(), 30), 10))
    plot_tree(arvore, feature_names=list(pipeline.named_steps["preparo"].get_feature_names_out()),
              class_names=[NOMES_CLASSES[0], NOMES_CLASSES[1]], filled=True, rounded=True,
              impurity=False, proportion=True, fontsize=8, ax=eixo)
    eixo.set_title("Árvore de decisão — probabilidade de pagamento do pedido")
    fig.tight_layout()
    fig.savefig(PASTA_FIGURAS / "arvore_decisao.png", dpi=150)
    plt.close(fig)


def salvar_importancias(imp_arvore: pd.Series, imp_floresta: pd.Series) -> None:
    top = imp_floresta.head(12).index.union(imp_arvore[imp_arvore > 0].index)
    dados = pd.DataFrame({"Árvore de decisão": imp_arvore, "Random Forest": imp_floresta}).loc[top]
    dados = dados.sort_values("Random Forest")
    fig, eixo = plt.subplots(figsize=(8, max(4, 0.35 * len(dados))))
    dados.plot.barh(ax=eixo, color=["#6B1E2E", "#C9A24B"])
    eixo.set_title("Importância das variáveis")
    eixo.set_xlabel("Importância relativa")
    fig.tight_layout()
    fig.savefig(PASTA_FIGURAS / "importancia_variaveis.png", dpi=150)
    plt.close(fig)


def faixa_risco(prob_nao_pago: float) -> str:
    if prob_nao_pago >= LIMITE_RISCO_ALTO:
        return "Alto"
    if prob_nao_pago >= LIMITE_RISCO_MEDIO:
        return "Médio"
    return "Baixo"


def montar_previsoes(pipeline: Pipeline, teste: pd.DataFrame, aguardando: pd.DataFrame) -> pd.DataFrame:
    partes = []
    for conjunto, df in [("Teste", teste), ("Aguardando pagamento", aguardando)]:
        if df.empty:
            continue
        prob_pago = pipeline.predict_proba(df[cfg.COLUNAS_ENTRADA_MODELO])[:, 1]
        previsto = (prob_pago >= 0.5).astype(int)
        parte = pd.DataFrame({
            "id_pedido": df["id_pedido"].to_numpy(),
            "conjunto": conjunto,
            "real": df[cfg.ROTULO].map(NOMES_CLASSES).to_numpy(),
            "previsto": pd.Series(previsto).map(NOMES_CLASSES).to_numpy(),
            "prob_pagamento": prob_pago.round(4),
            "prob_nao_pagamento": (1 - prob_pago).round(4),
        })
        parte["acerto"] = np.where(parte["real"].isna(), None,
                                   np.where(parte["real"] == parte["previsto"], "Sim", "Não"))
        parte["faixa_risco"] = parte["prob_nao_pagamento"].map(faixa_risco)
        partes.append(parte)
    return pd.concat(partes, ignore_index=True)


def escrever_metricas(linhas: list[str]) -> None:
    CAMINHO_METRICAS.write_text("\n".join(linhas), encoding="utf-8")


# =============================================================================
# EXECUÇÃO
# =============================================================================

def main() -> int:
    try:
        print("[1/6] Lendo e validando a base_ml")
        base = carregar_base()
        validar_base_ml(base)
        rotulados, aguardando = separar(base)

        print("[2/6] Dividindo treino (80%) e teste (20%), estratificado")
        treino, teste = train_test_split(rotulados, test_size=PROPORCAO_TESTE,
                                         stratify=rotulados[cfg.ROTULO], random_state=cfg.SEMENTE)
        X_treino, y_treino = treino[cfg.COLUNAS_ENTRADA_MODELO], treino[cfg.ROTULO]
        X_teste, y_teste = teste[cfg.COLUNAS_ENTRADA_MODELO], teste[cfg.ROTULO]

        print(f"[3/6] Validação cruzada ({DOBRAS_VALIDACAO} dobras) para escolher os hiperparâmetros")
        busca_arvore = ajustar("Árvore de decisão",
                               DecisionTreeClassifier(class_weight="balanced", random_state=cfg.SEMENTE),
                               GRADE_ARVORE, X_treino, y_treino)
        busca_floresta = ajustar("Random Forest",
                                 RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                                        random_state=cfg.SEMENTE, n_jobs=-1),
                                 GRADE_FLORESTA, X_treino, y_treino)
        arvore, floresta = busca_arvore.best_estimator_, busca_floresta.best_estimator_
        linha_base = montar_pipeline(DummyClassifier(strategy="most_frequent")).fit(X_treino, y_treino)

        print("[4/6] Avaliando no conjunto de teste")
        resultados = pd.DataFrame({
            "Linha de base (sempre 'Pago')": avaliar(linha_base, X_teste, y_teste),
            "Árvore de decisão": avaliar(arvore, X_teste, y_teste),
            "Random Forest": avaliar(floresta, X_teste, y_teste),
        }).round(3)
        print(resultados.to_string())

        print("[5/6] Gerando regras e figuras")
        cfg.PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
        previsto_teste = arvore.predict(X_teste)
        salvar_matriz_confusao(y_teste, previsto_teste)
        salvar_arvore(arvore)
        imp_arvore, imp_floresta = importancias(arvore), importancias(floresta)
        salvar_importancias(imp_arvore, imp_floresta)
        regras = export_text(arvore.named_steps["modelo"],
                             feature_names=list(arvore.named_steps["preparo"].get_feature_names_out()),
                             class_names=[NOMES_CLASSES[0], NOMES_CLASSES[1]], show_weights=True)
        CAMINHO_REGRAS.write_text(
            "Regras da árvore de decisão (weights = [peso Não pago, peso Pago], com class_weight='balanced')\n\n"
            + regras, encoding="utf-8")

        print("[6/6] Gerando previsões")
        previsoes = montar_previsoes(arvore, teste, aguardando)
        previsoes.to_csv(CAMINHO_PREVISOES, sep=";", decimal=",", index=False, encoding="utf-8-sig")

        proporcao = rotulados[cfg.ROTULO].value_counts(normalize=True)
        escrever_metricas([
            "MÉTRICAS DO MODELO — Vinheria Agnello (PBL Fase 3)",
            "=" * 72,
            f"Gerado em: {datetime.now():%d/%m/%Y %H:%M:%S} | Semente: {cfg.SEMENTE}",
            f"Pedidos com rótulo: {len(rotulados)} (Pago {proporcao.get(1, 0):.1%} | "
            f"Não pago {proporcao.get(0, 0):.1%}) | Aguardando pagamento: {len(aguardando)}",
            f"Treino: {len(treino)} | Teste: {len(teste)} (divisão estratificada {1 - PROPORCAO_TESTE:.0%}/"
            f"{PROPORCAO_TESTE:.0%})",
            f"Entradas ({len(cfg.COLUNAS_ENTRADA_MODELO)}): {', '.join(cfg.COLUNAS_ENTRADA_MODELO)}",
            "",
            "== Validação cruzada — árvore de decisão (ordenada por AUC média)",
            tabela_resultados_cv(busca_arvore).to_string(index=False),
            "",
            "== Validação cruzada — Random Forest (5 melhores)",
            tabela_resultados_cv(busca_floresta).head(5).to_string(index=False),
            "",
            f"Árvore escolhida: {formatar_parametros(busca_arvore.best_params_)} | "
            f"profundidade real {arvore.named_steps['modelo'].get_depth()} | "
            f"{arvore.named_steps['modelo'].get_n_leaves()} folhas",
            f"Random Forest escolhida: {formatar_parametros(busca_floresta.best_params_)}",
            "",
            "== Resultados no conjunto de teste",
            resultados.to_string(),
            "",
            "== Relatório de classificação — árvore de decisão (teste)",
            classification_report(y_teste, previsto_teste,
                                  target_names=[NOMES_CLASSES[0], NOMES_CLASSES[1]], digits=3),
            "== Variáveis mais importantes — árvore de decisão",
            imp_arvore[imp_arvore > 0].round(3).to_string(),
            "",
            "== Variáveis mais importantes — Random Forest (10 primeiras)",
            imp_floresta.head(10).round(3).to_string(),
            "",
            "Notas:",
            "- A linha de base sempre prevê 'Pago'. Um modelo útil precisa superá-la em AUC, acurácia",
            "  balanceada e recall de 'Não pago'; acurácia simples sozinha engana com classes desbalanceadas.",
            "- class_weight='balanced' compensa o desbalanceamento e prioriza encontrar pedidos não pagos.",
        ])

        print(f"\nModelo final: árvore de decisão ({formatar_parametros(busca_arvore.best_params_)})")
        print(f"Saídas em: {cfg.PASTA_RESULTADOS}")
        return 0

    except ErroValidacao as erro:
        print(f"\nMODELO NÃO TREINADO: {erro}")
        return 1
    except ErroModelo as erro:
        print(f"\nERRO: {erro}")
        return 1


if __name__ == "__main__":
    sys.exit(main())