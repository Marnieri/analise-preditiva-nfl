"""
17_baixar_estatisticas_time.py
------------------------------------
Baixa estatísticas AVANÇADAS em nível de TIME (não de jogador individual),
incluindo EPA (Expected Points Added) - a métrica mais respeitada hoje em
análise de futebol americano para medir eficiência ofensiva e defensiva.

Por que em nível de time, e não somar os dados de jogador que já temos?
Porque EPA de passe é atribuído tanto ao QB quanto ao recebedor na mesma
jogada (visões complementares da mesma jogada) - somar as duas contaria
o mesmo ponto de eficiência duas vezes. Usar dados já agregados por time
evita esse problema de dupla contagem.
"""

import pandas as pd
import nflreadpy as nfl

temporadas = list(range(2019, 2026))

print(f"Baixando estatísticas de time das temporadas: {temporadas}")
time_stats_polars = nfl.load_team_stats(temporadas, summary_level="week")
time_stats = time_stats_polars.to_pandas()

print(f"\nTotal de registros: {time_stats.shape[0]} linhas, {time_stats.shape[1]} colunas")
print("\nColunas disponíveis:")
print(list(time_stats.columns))

# Procuramos, de forma defensiva, as colunas de EPA ofensivo e defensivo.
# Nomes possíveis variam entre fontes, por isso testamos alternativas.
candidatos_epa_ofensivo = ["off_epa", "offense_epa", "epa_offense", "epa"]
candidatos_epa_defensivo = ["def_epa", "defense_epa", "epa_defense", "epa_allowed"]

epa_off_encontrado = next((c for c in candidatos_epa_ofensivo if c in time_stats.columns), None)
epa_def_encontrado = next((c for c in candidatos_epa_defensivo if c in time_stats.columns), None)

print(f"\nColuna de EPA ofensivo encontrada: {epa_off_encontrado}")
print(f"Coluna de EPA defensivo encontrada: {epa_def_encontrado}")

if not epa_off_encontrado or not epa_def_encontrado:
    print("\nATENÇÃO: não encontramos automaticamente as colunas de EPA.")
    print("Isso não é um erro fatal - só significa que precisamos olhar a lista")
    print("de colunas acima manualmente e ajustar os nomes no script.")

time_stats.to_csv("estatisticas_time_2019_2025.csv", index=False)
print("\nSalvo em 'estatisticas_time_2019_2025.csv' (dataset completo, sem filtrar colunas ainda -")
print("vamos decidir quais usar depois de ver a lista completa).")