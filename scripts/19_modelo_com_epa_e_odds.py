"""
19_modelo_com_epa_e_odds.py
--------------------------------
Versão expandida do modelo de previsão (substitui o script 16 como versão
principal), agora incluindo:
- Features de EPA ofensivo/defensivo (mais sofisticadas que pontos brutos)
- Comparação direta com as odds do mercado de apostas (benchmark externo)

Conceito novo: PROBABILIDADE IMPLÍCITA DE MERCADO
----------------------------------------------------
Odds de apostas ("moneyline") podem ser convertidas na probabilidade que
o mercado atribui a cada resultado. Casas de apostas cobram uma margem
("vig" ou "overround") embutida nas odds, então a soma das probabilidades
brutas passa de 100% - por isso normalizamos (dividimos pela soma) para
obter a probabilidade "limpa" de verdade.
"""

import sqlite3
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

conexao = sqlite3.connect("nfl_dados.db")
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)
jogos_originais = pd.read_sql("SELECT * FROM jogos", conexao)

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

# ---------------------------------------------------------------------------
# TRAZENDO AS ODDS DE APOSTAS (moneyline) do jogo, e convertendo em
# probabilidade implícita do mercado.
# ---------------------------------------------------------------------------
odds = jogos_originais[["season", "week", "home_team", "away_team", "home_moneyline", "away_moneyline", "spread_line"]]
jogos_completos = jogos_completos.merge(odds, on=["season", "week", "home_team", "away_team"], how="left")


def moneyline_para_probabilidade(moneyline):
    """Converte odds americanas (moneyline) em probabilidade bruta (0 a 1).
    Odds negativas (ex: -150) indicam favorito; positivas (ex: +130) azarão."""
    if pd.isna(moneyline):
        return None
    if moneyline < 0:
        return -moneyline / (-moneyline + 100)
    else:
        return 100 / (moneyline + 100)


jogos_completos["prob_bruta_casa"] = jogos_completos["home_moneyline"].apply(moneyline_para_probabilidade)
jogos_completos["prob_bruta_fora"] = jogos_completos["away_moneyline"].apply(moneyline_para_probabilidade)

# Normalização (remoção do "vig"): a soma das duas probabilidades brutas
# passa de 100% (é assim que a casa de apostas garante lucro). Dividimos
# pela soma para obter a probabilidade "justa" implícita pelo mercado.
soma_probs = jogos_completos["prob_bruta_casa"] + jogos_completos["prob_bruta_fora"]
jogos_completos["probabilidade_mercado_casa"] = jogos_completos["prob_bruta_casa"] / soma_probs

# ---------------------------------------------------------------------------
# Lista de features - agora incluindo EPA e a probabilidade de mercado.
# ---------------------------------------------------------------------------
features_modelo = [
    "media_pontos_marcados_temporada_casa",
    "media_pontos_sofridos_temporada_casa",
    "taxa_vitorias_temporada_casa",
    "media_pontos_marcados_temporada_fora",
    "media_pontos_sofridos_temporada_fora",
    "taxa_vitorias_temporada_fora",
    "dias_descanso_casa",
    "dias_descanso_fora",
    "epa_ofensivo_temporada_casa",
    "epa_defensivo_temporada_casa",
    "epa_ofensivo_temporada_fora",
    "epa_defensivo_temporada_fora",
]

dados_modelo = jogos_completos.dropna(subset=features_modelo + ["home_venceu"])
# Para a comparação com o mercado, usamos só os jogos que também têm odds
# disponíveis (temporadas mais antigas podem não ter esse dado completo).
dados_com_odds = dados_modelo.dropna(subset=["probabilidade_mercado_casa"])

print(f"Jogos com features completas: {len(dados_modelo)}")
print(f"Desses, jogos que também têm odds de mercado: {len(dados_com_odds)}")

# ---------------------------------------------------------------------------
# Validação cruzada temporal (igual ao script anterior), agora com as
# features novas E comparando com o mercado.
# ---------------------------------------------------------------------------
temporadas_para_testar = [2021, 2022, 2023, 2024, 2025]
resultados = []

for temporada_teste in temporadas_para_testar:
    treino = dados_modelo[dados_modelo["season"] < temporada_teste]
    teste = dados_modelo[dados_modelo["season"] == temporada_teste]

    if len(teste) == 0:
        continue

    X_treino, y_treino = treino[features_modelo], treino["home_venceu"]
    X_teste, y_teste = teste[features_modelo], teste["home_venceu"]

    scaler = StandardScaler()
    X_treino_p = scaler.fit_transform(X_treino)
    X_teste_p = scaler.transform(X_teste)

    modelo = LogisticRegression()
    modelo.fit(X_treino_p, y_treino)
    previsoes = modelo.predict(X_teste_p)

    acuracia_modelo = accuracy_score(y_teste, previsoes)
    acuracia_baseline = accuracy_score(y_teste, [1] * len(y_teste))

    # Previsão do "mercado": se probabilidade_mercado_casa > 0.5, o mercado
    # está apostando na casa. Comparamos só nos jogos onde temos essa odd.
    teste_com_odds = teste.dropna(subset=["probabilidade_mercado_casa"])
    if len(teste_com_odds) > 0:
        previsao_mercado = (teste_com_odds["probabilidade_mercado_casa"] > 0.5).astype(int)
        acuracia_mercado = accuracy_score(teste_com_odds["home_venceu"], previsao_mercado)
    else:
        acuracia_mercado = None

    resultados.append({
        "temporada_teste": temporada_teste,
        "jogos_teste": len(X_teste),
        "acuracia_modelo": acuracia_modelo,
        "acuracia_baseline": acuracia_baseline,
        "acuracia_mercado": acuracia_mercado,
    })

resultados_df = pd.DataFrame(resultados)

print("\n" + "=" * 75)
print("RESULTADOS POR TEMPORADA")
print("=" * 75)
print(resultados_df.to_string(index=False))

print("\n" + "=" * 75)
print("RESUMO GERAL")
print("=" * 75)
print(f"Acurácia média do MODELO:    {resultados_df['acuracia_modelo'].mean():.1%}")
print(f"Acurácia média do BASELINE:  {resultados_df['acuracia_baseline'].mean():.1%}")
if resultados_df["acuracia_mercado"].notna().any():
    print(f"Acurácia média do MERCADO:   {resultados_df['acuracia_mercado'].mean():.1%}")
    print("\nO mercado de apostas incorpora informação que não temos (lesões de última")
    print("hora, notícias, análise de especialistas) - por isso costuma superar")
    print("modelos estatísticos simples como o nosso. Ficar PRÓXIMO do mercado já é")
    print("um resultado respeitável para um modelo com poucas features.")

# Coeficientes finais, para entender o que o modelo mais valoriza agora.
scaler_final = StandardScaler()
X_final = scaler_final.fit_transform(dados_modelo[features_modelo])
modelo_final = LogisticRegression()
modelo_final.fit(X_final, dados_modelo["home_venceu"])

print("\n" + "=" * 75)
print("IMPORTÂNCIA DAS FEATURES (modelo treinado com todos os dados disponíveis)")
print("=" * 75)
coeficientes = pd.Series(modelo_final.coef_[0], index=features_modelo).sort_values(key=abs, ascending=False)
print(coeficientes.round(3))

conexao.close()