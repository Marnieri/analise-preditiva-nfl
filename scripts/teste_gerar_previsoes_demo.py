"""
teste_gerar_previsoes_demo.py
----------------------------------
Script TEMPORÁRIO, só para testar visualmente a página inicial do
dashboard antes da temporada 2026 começar de verdade.

O que ele faz: pega uma semana JÁ DISPUTADA de 2025 e gera "previsões"
para ela (usando só as features disponíveis ANTES daquela rodada, como
seria numa previsão real) - simulando o formato exato que o pipeline
semanal produz quando a temporada estiver rolando.

Depois que a temporada 2026 começar de verdade, é só rodar o
'00_pipeline_semanal.py' normalmente - ele vai substituir esse arquivo
de demonstração pelas previsões reais.
"""

import sqlite3
from pathlib import Path
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Ancorado na raiz do projeto - este script está em "scripts/", subimos 1 nível.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
DB_PATH = RAIZ_PROJETO / "nfl_dados.db"
ARQUIVO_PREVISOES = RAIZ_PROJETO / "previsoes_proxima_semana.csv"

SEASON_DEMO = 2025
WEEK_DEMO = 10  # qualquer semana no meio da temporada, com histórico suficiente

FEATURES = [
    "taxa_vitorias_temporada_casa", "taxa_vitorias_temporada_fora",
    "dias_descanso_casa", "dias_descanso_fora",
    "epa_ofensivo_temporada_casa", "epa_defensivo_temporada_casa",
    "epa_ofensivo_temporada_fora", "epa_defensivo_temporada_fora",
]

conexao = sqlite3.connect(DB_PATH)
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)
jogos_originais = pd.read_sql("SELECT * FROM jogos", conexao)

casa = jogos_por_time[jogos_por_time["local"] == "casa"].rename(columns={"team": "home_team", "opponent": "away_team"})
fora = jogos_por_time[jogos_por_time["local"] == "fora"].rename(columns={"team": "away_team", "opponent": "home_team"})
jogos_completos = casa.merge(fora, on=["season", "week", "home_team", "away_team"], suffixes=("_casa", "_fora"))
jogos_completos["home_venceu"] = pd.to_numeric(jogos_completos["pontos_time_casa"], errors="coerce") > pd.to_numeric(jogos_completos["pontos_time_fora"], errors="coerce")

# Treinamos com tudo ANTES da semana de demonstração (simula a situação real
# de nunca ter visto o resultado do jogo que estamos "prevendo").
treino = jogos_completos[
    (jogos_completos["season"] < SEASON_DEMO) |
    ((jogos_completos["season"] == SEASON_DEMO) & (jogos_completos["week"] < WEEK_DEMO))
].dropna(subset=FEATURES + ["home_venceu"])

demo = jogos_completos[
    (jogos_completos["season"] == SEASON_DEMO) & (jogos_completos["week"] == WEEK_DEMO)
].dropna(subset=FEATURES).copy()

scaler = StandardScaler()
X_treino = scaler.fit_transform(treino[FEATURES])
modelo = LogisticRegression()
modelo.fit(X_treino, treino["home_venceu"].astype(int))

X_demo = scaler.transform(demo[FEATURES])
demo["probabilidade_casa_vencer"] = modelo.predict_proba(X_demo)[:, 1]
demo["prob_casa_vencer_%"] = (demo["probabilidade_casa_vencer"] * 100).round(1)

odds_cols = ["season", "week", "home_team", "away_team", "spread_line", "home_moneyline", "away_moneyline"]
demo = demo.merge(jogos_originais[odds_cols], on=["season", "week", "home_team", "away_team"], how="left")

resultado_final = demo[["season", "week", "home_team", "away_team", "prob_casa_vencer_%", "spread_line", "home_moneyline", "away_moneyline"]]
resultado_final.to_csv(ARQUIVO_PREVISOES, index=False)

print(f"Previsões de DEMONSTRAÇÃO geradas (temporada {SEASON_DEMO}, semana {WEEK_DEMO}):")
print(resultado_final.to_string(index=False))
print(f"\nSalvo em '{ARQUIVO_PREVISOES}' - recarregue o dashboard para ver.")
print("LEMBRETE: isso é só para teste visual. Quando a temporada 2026 rodar de")
print("verdade, use o '00_pipeline_semanal.py' normal para gerar previsões reais.")

conexao.close()