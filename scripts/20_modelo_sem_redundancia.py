"""
20_modelo_sem_redundancia.py
----------------------------------
Compara o modelo anterior (pontos brutos + EPA) com uma versão enxuta que
remove as features de pontos brutos, já que EPA carrega informação
parecida (e mais sofisticada) - a esperança é que a versão enxuta seja
igualmente boa ou até um pouco melhor, com coeficientes mais interpretáveis.
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

# Versão COMPLETA (igual ao script 19).
features_completo = [
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

# Versão ENXUTA: removemos média de pontos marcados/sofridos (redundante com EPA),
# mantendo taxa de vitórias (que captura algo distinto: resultado final, não
# só eficiência por jogada) e descanso.
features_enxuto = [
    "taxa_vitorias_temporada_casa",
    "taxa_vitorias_temporada_fora",
    "dias_descanso_casa",
    "dias_descanso_fora",
    "epa_ofensivo_temporada_casa",
    "epa_defensivo_temporada_casa",
    "epa_ofensivo_temporada_fora",
    "epa_defensivo_temporada_fora",
]

temporadas_para_testar = [2021, 2022, 2023, 2024, 2025]


def validar_walk_forward(features, nome_versao):
    dados_modelo = jogos_completos.dropna(subset=features + ["home_venceu"])
    resultados = []

    for temporada_teste in temporadas_para_testar:
        treino = dados_modelo[dados_modelo["season"] < temporada_teste]
        teste = dados_modelo[dados_modelo["season"] == temporada_teste]
        if len(teste) == 0:
            continue

        X_treino, y_treino = treino[features], treino["home_venceu"]
        X_teste, y_teste = teste[features], teste["home_venceu"]

        scaler = StandardScaler()
        X_treino_p = scaler.fit_transform(X_treino)
        X_teste_p = scaler.transform(X_teste)

        modelo = LogisticRegression()
        modelo.fit(X_treino_p, y_treino)
        previsoes = modelo.predict(X_teste_p)

        resultados.append({
            "temporada_teste": temporada_teste,
            "acuracia": accuracy_score(y_teste, previsoes),
        })

    resultados_df = pd.DataFrame(resultados)
    media = resultados_df["acuracia"].mean()
    desvio = resultados_df["acuracia"].std()
    print(f"\n[{nome_versao}] - {len(features)} features")
    print(resultados_df.to_string(index=False))
    print(f"Média: {media:.1%}  |  Desvio padrão: {desvio:.1%}")

    # Treinamos uma última vez com TODOS os dados disponíveis, só para
    # extrair coeficientes finais e interpretar a importância das features.
    scaler_final = StandardScaler()
    X_final = scaler_final.fit_transform(dados_modelo[features])
    modelo_final = LogisticRegression()
    modelo_final.fit(X_final, dados_modelo["home_venceu"])
    coeficientes = pd.Series(modelo_final.coef_[0], index=features).sort_values(key=abs, ascending=False)

    return media, desvio, coeficientes


print("=" * 70)
print("COMPARAÇÃO: modelo completo vs. modelo enxuto (sem pontos brutos)")
print("=" * 70)

media_completo, desvio_completo, coef_completo = validar_walk_forward(features_completo, "COMPLETO")
media_enxuto, desvio_enxuto, coef_enxuto = validar_walk_forward(features_enxuto, "ENXUTO")

print("\n" + "=" * 70)
print("RESUMO COMPARATIVO")
print("=" * 70)
print(f"Completo ({len(features_completo)} features): {media_completo:.1%} (desvio {desvio_completo:.1%})")
print(f"Enxuto   ({len(features_enxuto)} features): {media_enxuto:.1%} (desvio {desvio_enxuto:.1%})")

diferenca = (media_enxuto - media_completo) * 100
if abs(diferenca) < 0.5:
    print(f"\nPraticamente empatados (diferença de {diferenca:+.1f} p.p.) - a versão enxuta")
    print("entrega a mesma performance com menos features, o que é preferível")
    print("(modelo mais simples, mais rápido, e mais fácil de interpretar).")
elif diferenca > 0:
    print(f"\nA versão ENXUTA superou a completa em {diferenca:.1f} p.p.")
else:
    print(f"\nA versão completa ainda leva vantagem por {abs(diferenca):.1f} p.p.")

print("\n" + "=" * 70)
print("COEFICIENTES DA VERSÃO ENXUTA (devem ficar mais fáceis de interpretar)")
print("=" * 70)
print(coef_enxuto.round(3))

conexao.close()