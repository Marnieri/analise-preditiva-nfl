"""
12_padronizar_features.py
------------------------------
Corrige a comparação de coeficientes do modelo anterior, padronizando
as features antes de treinar. Isso permite comparar de forma justa
qual feature realmente tem mais peso na decisão do modelo.

Biblioteca nova: StandardScaler (já vem dentro do scikit-learn, não
precisa instalar nada novo).
"""

import sqlite3
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

conexao = sqlite3.connect("nfl_dados.db")
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)

# Reconstrução da tabela em nível de jogo - igual ao script anterior.
casa = jogos_por_time[jogos_por_time["local"] == "casa"].rename(
    columns={"team": "home_team", "opponent": "away_team"}
)
fora = jogos_por_time[jogos_por_time["local"] == "fora"].rename(
    columns={"team": "away_team", "opponent": "home_team"}
)
jogos_completos = casa.merge(
    fora, on=["season", "week", "home_team", "away_team"], suffixes=("_casa", "_fora")
)
jogos_completos["home_venceu"] = (
    jogos_completos["pontos_time_casa"] > jogos_completos["pontos_time_fora"]
).astype(int)

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

dados_modelo = jogos_completos.dropna(subset=features + ["home_venceu"])
treino = dados_modelo[dados_modelo["season"] < 2023]
teste = dados_modelo[dados_modelo["season"] == 2023]

X_treino, y_treino = treino[features], treino["home_venceu"]
X_teste, y_teste = teste[features], teste["home_venceu"]

# ---------------------------------------------------------------------------
# PADRONIZAÇÃO
# ---------------------------------------------------------------------------
# .fit() no scaler CALCULA a média e o desvio padrão de cada feature,
# olhando SÓ para os dados de treino.
# .transform() APLICA essa transformação (usando a média/desvio já calculados)
# tanto no treino quanto no teste.
#
# Por que não usar .fit() no teste também? Porque isso significaria calcular
# a média/desvio olhando para dados que, na vida real, ainda não existem
# no momento da previsão (jogos de 2023 no futuro). Usar só as estatísticas
# do treino simula corretamente a situação real de fazer uma previsão nova.
scaler = StandardScaler()
X_treino_padronizado = scaler.fit_transform(X_treino)
X_teste_padronizado = scaler.transform(X_teste)

# Treinamos o modelo igual antes, mas agora com os dados padronizados.
modelo = LogisticRegression()
modelo.fit(X_treino_padronizado, y_treino)

previsoes = modelo.predict(X_teste_padronizado)
acuracia = accuracy_score(y_teste, previsoes)
baseline = accuracy_score(y_teste, [1] * len(y_teste))

print("=" * 50)
print("ACURÁCIA (com features padronizadas)")
print("=" * 50)
print(f"Baseline (sempre casa):  {baseline:.1%}")
print(f"Modelo padronizado:      {acuracia:.1%}")
print("\n(Pequenas diferenças na acurácia em relação à versão anterior são")
print("esperadas - a padronização interage com a regularização interna do")
print("modelo, mas o efeito costuma ser pequeno.)")

# ---------------------------------------------------------------------------
# COMPARAÇÃO JUSTA DOS COEFICIENTES
# ---------------------------------------------------------------------------
# Agora que todas as features estão na mesma escala, o TAMANHO do coeficiente
# reflete de verdade o quanto cada uma influencia a previsão.
print("\n" + "=" * 50)
print("IMPORTÂNCIA DAS FEATURES (agora comparável de verdade)")
print("=" * 50)
coeficientes = pd.Series(modelo.coef_[0], index=features).sort_values(key=abs, ascending=False)
print(coeficientes.round(3))