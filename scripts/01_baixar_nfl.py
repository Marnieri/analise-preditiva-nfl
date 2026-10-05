"""
01_baixar_dados_nfl.py
------------------------
Primeiro script do projeto de análise de dados da NFL.

Objetivo: baixar dados históricos de jogos (placares, times, semanas, temporadas)
usando a biblioteca nflreadpy, e salvar tudo em um arquivo CSV.

ATUALIZAÇÃO IMPORTANTE: este script foi migrado de "nfl_data_py" para
"nflreadpy". A biblioteca antiga foi arquivada (descontinuada) pelo mantenedor
em setembro de 2025, e não recebe mais dados de temporadas novas. A nflreadpy
é a sucessora oficial do mesmo grupo (nflverse), mantida ativamente.

Instale com: pip install "nflreadpy[pandas]"
(o extra "[pandas]" garante que a conversão .to_pandas() funcione)
"""

import pandas as pd
import nflreadpy as nfl

# 1. Definimos quais temporadas (anos) queremos baixar.
#    Atualizado para incluir até a temporada mais recente já concluída (2025).
temporadas = list(range(2019, 2026))  # baixa 2019 até 2025

print(f"Baixando dados de jogos das temporadas: {temporadas}")

# 2. load_schedules() traz o calendário/resultados de jogos.
#    Diferente da biblioteca antiga, esta retorna um DataFrame do Polars
#    (uma alternativa mais rápida ao pandas), não do pandas diretamente.
#    .to_pandas() converte para o formato que já estamos acostumados a usar.
jogos_polars = nfl.load_schedules(temporadas)
jogos = jogos_polars.to_pandas()

# 3. Como mudamos de biblioteca, vamos CONFERIR se os nomes das colunas
#    continuam os mesmos antes de seguir em frente. Isso evita erros
#    silenciosos causados por diferenças sutis de nomenclatura entre fontes.
print("\nColunas disponíveis nesta fonte:")
print(list(jogos.columns))

print(f"\nTotal de jogos baixados: {jogos.shape[0]} linhas, {jogos.shape[1]} colunas")

# 4. Selecionamos as colunas mais importantes para começar.
colunas_interesse = [
    "season", "week", "gameday", "home_team", "away_team",
    "home_score", "away_score", "result", "total",
    # Novas colunas aproveitando a fonte mais rica:
    "home_rest", "away_rest",           # dias de descanso já calculados pela fonte
    "spread_line",                      # linha de handicap do mercado de apostas
    "home_moneyline", "away_moneyline", # odds de vitória direta
    "total_line",                       # linha de total de pontos do mercado
    "div_game",                         # 1 = jogo entre times da mesma divisão
    "roof", "surface",                  # tipo de teto e piso do estádio
    "temp", "wind",                     # temperatura e vento (quando ao ar livre)
]

# Verificação defensiva: só seguimos com as colunas que realmente existem
# nesta fonte. Se alguma esperada não existir, avisamos claramente em vez
# de deixar o script quebrar com um erro confuso.
colunas_existentes = [c for c in colunas_interesse if c in jogos.columns]
colunas_faltando = [c for c in colunas_interesse if c not in jogos.columns]

if colunas_faltando:
    print(f"\nATENÇÃO: as colunas {colunas_faltando} não foram encontradas nesta fonte.")
    print("Isso pode indicar uma mudança de nomenclatura. Confira a lista de")
    print("colunas disponíveis impressa acima para identificar o nome correto.")

jogos_simplificado = jogos[colunas_existentes]

# 5. Salvamos essa tabela simplificada em um arquivo CSV.
nome_arquivo = "jogos_nfl_2019_2025.csv"
jogos_simplificado.to_csv(nome_arquivo, index=False)

print(f"\nPronto! Dados salvos em '{nome_arquivo}'.")
print(jogos_simplificado.head())