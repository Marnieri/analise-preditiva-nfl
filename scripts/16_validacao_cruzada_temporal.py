"""
16_validacao_cruzada_temporal.py
-------------------------------------
Substitui o único split treino/teste (que usava só 2023 como teste) por
uma validação cruzada temporal (walk-forward validation): testamos o
modelo em várias temporadas diferentes, treinando sempre só com dados
anteriores a cada uma.

Por que isso importa: com um único teste de 269 jogos, a diferença entre
59,5% e 57,6% de acurácia pode ser em boa parte "sorte" de qual temporada
calhou de testar. Validar em múltiplas temporadas dá uma medida bem mais
confiável da qualidade real do modelo.
"""

import sqlite3
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

conexao = sqlite3.connect("nfl_dados.db")
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)

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
    # "jogadores_out_casa", "jogadores_out_fora" - PAUSADO: a fonte de dados
    # de lesões (nflverse/injuries) parou de ser atualizada após a temporada
    # de 2024, sem previsão de retorno. Manter essa feature agora significa
    # treinar com dado real (2019-2024) e prever com valor sempre igual a
    # zero (2025 em diante) - o que não ajudaria a previsão e poderia até
    # confundir o modelo. Voltar a incluir se a fonte for restabelecida.
]

dados_modelo = jogos_completos.dropna(subset=features + ["home_venceu"])

# ---------------------------------------------------------------------------
# VALIDAÇÃO CRUZADA TEMPORAL (walk-forward)
# ---------------------------------------------------------------------------
# Em vez de um único corte (treino: <2023, teste: 2023), testamos o modelo
# em CADA temporada a partir de 2021, treinando sempre com tudo que veio antes.
# Ex: teste 2021 usa treino 2019-2020. Teste 2022 usa treino 2019-2021. Etc.
# (Começamos em 2021 porque com só 2019 de treino teríamos pouquíssimo dado.)
# Atualizado para incluir as temporadas mais recentes (2024 e 2025).
temporadas_para_testar = [2021, 2022, 2023, 2024, 2025]

resultados = []

for temporada_teste in temporadas_para_testar:
    treino = dados_modelo[dados_modelo["season"] < temporada_teste]
    teste = dados_modelo[dados_modelo["season"] == temporada_teste]

    X_treino, y_treino = treino[features], treino["home_venceu"]
    X_teste, y_teste = teste[features], teste["home_venceu"]

    scaler = StandardScaler()
    X_treino_p = scaler.fit_transform(X_treino)
    X_teste_p = scaler.transform(X_teste)

    modelo = LogisticRegression()
    modelo.fit(X_treino_p, y_treino)
    previsoes = modelo.predict(X_teste_p)

    acuracia_modelo = accuracy_score(y_teste, previsoes)
    acuracia_baseline = accuracy_score(y_teste, [1] * len(y_teste))

    resultados.append({
        "temporada_teste": temporada_teste,
        "jogos_treino": len(X_treino),
        "jogos_teste": len(X_teste),
        "acuracia_modelo": acuracia_modelo,
        "acuracia_baseline": acuracia_baseline,
    })

resultados_df = pd.DataFrame(resultados)

print("=" * 65)
print("RESULTADOS POR TEMPORADA (validação cruzada temporal)")
print("=" * 65)
print(resultados_df.to_string(index=False))

# Médias gerais - a medida mais confiável de performance do modelo.
media_modelo = resultados_df["acuracia_modelo"].mean()
media_baseline = resultados_df["acuracia_baseline"].mean()
desvio_padrao_modelo = resultados_df["acuracia_modelo"].std()

print("\n" + "=" * 65)
print("RESUMO GERAL")
print("=" * 65)
print(f"Acurácia média do MODELO:    {media_modelo:.1%} (desvio padrão: {desvio_padrao_modelo:.1%})")
print(f"Acurácia média do BASELINE:  {media_baseline:.1%}")
print(f"Diferença média:             {(media_modelo - media_baseline) * 100:.1f} pontos percentuais")

print("\nO desvio padrão nos mostra o quanto a performance varia entre")
print("temporadas - um desvio grande é um sinal de que o modelo não é")
print("consistente, e uma única medida de acurácia poderia enganar.")

conexao.close()