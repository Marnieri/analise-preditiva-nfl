"""
15_modelo_com_lesoes.py
----------------------------
Retreina o modelo de previsão incluindo a nova feature de lesões
(jogadores_out), e compara a acurácia com a versão anterior (sem lesões).
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

# Features anteriores + as duas novas colunas de lesões.
features_sem_lesoes = [
    "media_pontos_marcados_temporada_casa",
    "media_pontos_sofridos_temporada_casa",
    "taxa_vitorias_temporada_casa",
    "media_pontos_marcados_temporada_fora",
    "media_pontos_sofridos_temporada_fora",
    "taxa_vitorias_temporada_fora",
    "dias_descanso_casa",
    "dias_descanso_fora",
]
features_com_lesoes = features_sem_lesoes + ["jogadores_out_casa", "jogadores_out_fora"]


def treinar_e_avaliar(features, nome_versao):
    """Função reutilizável: treina o modelo com um conjunto de features
    e imprime a acurácia. Criamos essa função para não repetir o mesmo
    bloco de código duas vezes (uma vez sem lesões, outra com lesões)."""
    dados_modelo = jogos_completos.dropna(subset=features + ["home_venceu"])
    treino = dados_modelo[dados_modelo["season"] < 2023]
    teste = dados_modelo[dados_modelo["season"] == 2023]

    X_treino, y_treino = treino[features], treino["home_venceu"]
    X_teste, y_teste = teste[features], teste["home_venceu"]

    scaler = StandardScaler()
    X_treino_p = scaler.fit_transform(X_treino)
    X_teste_p = scaler.transform(X_teste)

    modelo = LogisticRegression()
    modelo.fit(X_treino_p, y_treino)
    previsoes = modelo.predict(X_teste_p)
    acuracia = accuracy_score(y_teste, previsoes)

    print(f"\n[{nome_versao}]")
    print(f"  Jogos de teste utilizados: {len(y_teste)}")
    print(f"  Acurácia: {acuracia:.1%}")

    return modelo, features, acuracia


# Comparamos as duas versões lado a lado.
print("=" * 55)
print("COMPARAÇÃO: modelo sem lesões vs. modelo com lesões")
print("=" * 55)
modelo_sem, _, acc_sem = treinar_e_avaliar(features_sem_lesoes, "SEM dados de lesão")
modelo_com, _, acc_com = treinar_e_avaliar(features_com_lesoes, "COM dados de lesão")

print("\n" + "=" * 55)
diferenca = (acc_com - acc_sem) * 100
if diferenca > 0:
    print(f"A feature de lesões MELHOROU a acurácia em {diferenca:.1f} pontos percentuais.")
elif diferenca < 0:
    print(f"A feature de lesões PIOROU a acurácia em {abs(diferenca):.1f} pontos percentuais.")
else:
    print("A feature de lesões não mudou a acurácia.")

print("\nCoeficientes do modelo COM lesões (padronizados, comparáveis entre si):")
coeficientes = pd.Series(modelo_com.coef_[0], index=features_com_lesoes).sort_values(key=abs, ascending=False)
print(coeficientes.round(3))

conexao.close()