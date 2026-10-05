"""
06_diagnosticar_merge_nfl.py
--------------------------------
Investiga por que 169 linhas do merge anterior não encontraram
correspondência entre as tabelas de jogadores e de jogos.
"""

import pandas as pd

jogos = pd.read_csv("jogos_nfl_2019_2025.csv")
jogadores = pd.read_csv("estatisticas_jogadores_2019_2025.csv")

# Recriamos a mesma reformatação do script anterior.
casa = jogos.rename(columns={"home_team": "team", "away_team": "opponent"})
fora = jogos.rename(columns={"away_team": "team", "home_team": "opponent"})
jogos_por_time = pd.concat([casa[["season", "week", "team"]], fora[["season", "week", "team"]]], ignore_index=True)

# 1. Primeiro, vamos comparar os CONJUNTOS de siglas de times em cada tabela.
#    set() remove duplicatas e nos dá só os valores únicos.
times_jogos = set(jogos_por_time["team"].unique())
times_jogadores = set(jogadores["recent_team"].unique())

# 2. A diferença entre os dois conjuntos (-) nos mostra o que existe
#    em um lado e não no outro. Isso é o coração do diagnóstico.
so_em_jogadores = times_jogadores - times_jogos
so_em_jogos = times_jogos - times_jogadores

print("Siglas que aparecem em JOGADORES mas não em JOGOS:")
print(so_em_jogadores)
print("\nSiglas que aparecem em JOGOS mas não em JOGADORES:")
print(so_em_jogos)

# 3. Vamos ver quantas linhas de jogadores usam cada uma dessas siglas "órfãs".
print("\nQuantidade de linhas de jogadores por sigla problemática:")
for sigla in so_em_jogadores:
    qtd = (jogadores["recent_team"] == sigla).sum()
    print(f"  {sigla}: {qtd} linhas")