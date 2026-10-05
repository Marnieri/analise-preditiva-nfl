"""
13_baixar_lesoes.py
------------------------
Baixa relatórios de lesões (injury reports) usando nflreadpy, e explora
a estrutura desses dados antes de decidir como transformá-los em feature.

ATUALIZAÇÃO IMPORTANTE: migrado de "nfl_data_py" (descontinuada em
setembro de 2025) para "nflreadpy" (sucessora oficial e ativamente mantida).
Instale com: pip install "nflreadpy[pandas]"
"""

import pandas as pd
import nflreadpy as nfl

temporadas = list(range(2019, 2026))

print(f"Baixando dados de lesões das temporadas: {temporadas}")
lesoes_polars = nfl.load_injuries(temporadas)
lesoes = lesoes_polars.to_pandas()

print(f"\nTotal de registros: {lesoes.shape[0]} linhas, {lesoes.shape[1]} colunas")
print("\nColunas disponíveis:")
print(list(lesoes.columns))

print("\nPrimeiras linhas:")
print(lesoes.head(10))

# A coluna de status normalmente indica se o jogador está "Out" (não vai jogar),
# "Questionable" (dúvida) ou "Doubtful" (dificilmente joga). Como mudamos de
# biblioteca, confirmamos de forma defensiva se o nome da coluna continua
# o mesmo antes de tentar usá-la.
if "report_status" in lesoes.columns:
    print("\nValores únicos de status de lesão (coluna 'report_status'):")
    print(lesoes["report_status"].value_counts(dropna=False))
else:
    print("\nATENÇÃO: a coluna 'report_status' não foi encontrada nesta fonte.")
    print("Confira a lista de colunas impressa acima para localizar o nome certo")
    print("(procure por algo como 'status' ou 'game_status') e me avise para ajustarmos.")

lesoes.to_csv("lesoes_2019_2025.csv", index=False)
print("\nSalvo em 'lesoes_2019_2025.csv'.")
