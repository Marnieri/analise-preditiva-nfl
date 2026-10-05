"""
11_modelo_previsao.py
--------------------------
Primeiro modelo de previsão: regressão logística para estimar a
probabilidade de o time da casa vencer, usando as features de forma
recente, desempenho na temporada e descanso que já construímos.

Biblioteca nova: scikit-learn (sklearn) - a biblioteca padrão de
machine learning em Python. Instale com: pip install scikit-learn
"""

import sqlite3
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix

conexao = sqlite3.connect("nfl_dados.db")
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)

# ---------------------------------------------------------------------------
# PASSO 1: Transformar a tabela "1 linha por time por jogo" de volta para
# "1 linha por jogo", mas agora com as features de AMBOS os times lado a lado.
# Isso é necessário porque um modelo de previsão precisa comparar os dois
# times de uma vez (ex: "o time da casa está em melhor forma que o visitante?").
# ---------------------------------------------------------------------------
casa = jogos_por_time[jogos_por_time["local"] == "casa"].rename(
    columns={"team": "home_team", "opponent": "away_team"}
)
fora = jogos_por_time[jogos_por_time["local"] == "fora"].rename(
    columns={"team": "away_team", "opponent": "home_team"}
)

# merge com suffixes: colunas que existem nos dois lados (ex: dias_descanso)
# recebem "_casa" ou "_fora" automaticamente para não haver ambiguidade.
jogos_completos = casa.merge(
    fora, on=["season", "week", "home_team", "away_team"], suffixes=("_casa", "_fora")
)

print(f"Total de jogos reconstruídos: {jogos_completos.shape[0]} (deveria bater com o total original)")

# ---------------------------------------------------------------------------
# PASSO 2: Definir as features (X) e o alvo/target (y) que queremos prever.
# ---------------------------------------------------------------------------
# O alvo: o time da casa venceu? (1 = sim, 0 = não)
jogos_completos["home_venceu"] = (
    jogos_completos["pontos_time_casa"] > jogos_completos["pontos_time_fora"]
).astype(int)

# As features: só usamos colunas que representam informação DISPONÍVEL
# ANTES do jogo acontecer (por isso o cuidado com shift/expanding lá atrás
# já garante que essas colunas são seguras de usar).
features = [
    "media_pontos_marcados_temporada_casa",
    "media_pontos_sofridos_temporada_casa",
    "taxa_vitorias_temporada_casa",
    "media_pontos_marcados_temporada_fora",
    "media_pontos_sofridos_temporada_fora",
    "taxa_vitorias_temporada_fora",
    "dias_descanso_casa",
    "dias_descanso_fora",
]

# 3. Removemos jogos onde alguma feature está vazia (NaN) - isso acontece
#    principalmente nas primeiras semanas de cada temporada, onde ainda não
#    há "histórico da temporada" suficiente para calcular as médias.
dados_modelo = jogos_completos.dropna(subset=features + ["home_venceu"])
print(f"Jogos utilizáveis após remover linhas com dados insuficientes: {dados_modelo.shape[0]}")

# ---------------------------------------------------------------------------
# PASSO 3: Divisão treino/teste POR TEMPORADA (não aleatória!)
# ---------------------------------------------------------------------------
treino = dados_modelo[dados_modelo["season"] < 2023]
teste = dados_modelo[dados_modelo["season"] == 2023]

X_treino, y_treino = treino[features], treino["home_venceu"]
X_teste, y_teste = teste[features], teste["home_venceu"]

print(f"\nJogos de treino (2019-2022): {len(X_treino)}")
print(f"Jogos de teste (2023): {len(X_teste)}")

# ---------------------------------------------------------------------------
# PASSO 4: Treinar o modelo.
# ---------------------------------------------------------------------------
# .fit() é o comando que "ensina" o modelo, ajustando seus parâmetros internos
# para minimizar o erro entre as previsões e os resultados reais de treino.
modelo = LogisticRegression()
modelo.fit(X_treino, y_treino)

# ---------------------------------------------------------------------------
# PASSO 5: Avaliar o modelo nos dados de TESTE (jogos que ele nunca viu).
# ---------------------------------------------------------------------------
previsoes = modelo.predict(X_teste)
acuracia_modelo = accuracy_score(y_teste, previsoes)

# BASELINE: o que aconteceria se simplesmente sempre apostássemos
# que o time da casa vence? Isso é o "adversário" que o modelo precisa vencer.
baseline_sempre_casa = accuracy_score(y_teste, [1] * len(y_teste))

print("\n" + "=" * 50)
print("RESULTADOS")
print("=" * 50)
print(f"Acurácia do BASELINE (sempre apostar na casa): {baseline_sempre_casa:.1%}")
print(f"Acurácia do MODELO (regressão logística):      {acuracia_modelo:.1%}")

if acuracia_modelo > baseline_sempre_casa:
    print("\nO modelo superou o baseline! Isso é um bom sinal de que as")
    print("features carregam informação preditiva real.")
else:
    print("\nO modelo NÃO superou o baseline. Isso não é incomum com poucas")
    print("features e pouco dado de treino - vamos investigar e melhorar.")

# 6. Matriz de confusão: mostra os acertos e erros em detalhe.
#    Linhas = realidade, colunas = previsão do modelo.
print("\nMatriz de confusão (linhas=real, colunas=previsto):")
print("                Previsto: Casa perde | Previsto: Casa vence")
matriz = confusion_matrix(y_teste, previsoes)
print(f"Real: Casa perde        {matriz[0][0]:>10}         {matriz[0][1]:>10}")
print(f"Real: Casa vence        {matriz[1][0]:>10}         {matriz[1][1]:>10}")

# 7. Coeficientes do modelo: mostram qual feature "pesa" mais na decisão.
#    Coeficiente positivo = aumenta a chance do time da casa vencer.
#    Coeficiente negativo = diminui a chance do time da casa vencer.
print("\n" + "=" * 50)
print("IMPORTÂNCIA DE CADA FEATURE (coeficientes do modelo)")
print("=" * 50)
coeficientes = pd.Series(modelo.coef_[0], index=features).sort_values(ascending=False)
print(coeficientes.round(3))

conexao.close()