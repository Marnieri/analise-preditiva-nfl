"""
04_baixar_estatisticas_jogadores.py
--------------------------------------
Baixa estatísticas de jogadores (passe, corrida, recepção) jogo a jogo,
usando a mesma biblioteca nfl_data_py.
"""

import pandas as pd
import nfl_data_py as nfl

# 1. Mesmas temporadas do script de jogos, para manter tudo consistente.
temporadas = list(range(2019, 2026))

print(f"Baixando estatísticas de jogadores das temporadas: {temporadas}")

# 2. import_weekly_data() traz uma linha por jogador, por semana, por temporada.
#    Isso é bem mais pesado que os dados de jogos (muito mais linhas),
#    então pode demorar um pouco mais para baixar.
jogadores = nfl.import_weekly_data(temporadas)

print(f"\nTotal de registros baixados: {jogadores.shape[0]} linhas, {jogadores.shape[1]} colunas")

# 3. Esse dataset tem DEZENAS de colunas (mais de 50). Para começar,
#    vamos selecionar só as mais relevantes para as três facetas do jogo:
#    passe (passing), corrida (rushing) e recepção (receiving).
colunas_interesse = [
    "player_name",       # nome do jogador
    "player_display_name",
    "position",          # posição (QB, RB, WR, TE, etc)
    "recent_team",       # time naquela semana (jogadores podem trocar de time)
    "season",
    "week",
    # Estatísticas de passe (relevantes para QBs)
    "completions",
    "attempts",
    "passing_yards",
    "passing_tds",
    "interceptions",
    # Estatísticas de corrida (relevantes para RBs, e QBs que correm)
    "carries",
    "rushing_yards",
    "rushing_tds",
    # Estatísticas de recepção (relevantes para WRs, TEs, RBs)
    "receptions",
    "targets",
    "receiving_yards",
    "receiving_tds",
    # Métrica combinada de pontos em formato "fantasy football",
    # útil como um resumo geral de produção do jogador na semana.
    "fantasy_points",
]
jogadores_simplificado = jogadores[colunas_interesse]

# 4. Salvamos em CSV, assim como fizemos com os dados de jogos.
nome_arquivo = "estatisticas_jogadores_2019_2025.csv"
jogadores_simplificado.to_csv(nome_arquivo, index=False)

print(f"\nPronto! Dados salvos em '{nome_arquivo}'.")

# 5. Uma prévia rápida: os 5 jogadores com mais jazidas de passe (passing_yards)
#    em uma única semana, só para conferir que os dados fazem sentido.
print("\nTop 5 performances de passe em uma única semana:")
top_passe = jogadores_simplificado.sort_values("passing_yards", ascending=False).head(5)
print(top_passe[["player_display_name", "season", "week", "passing_yards", "passing_tds"]])