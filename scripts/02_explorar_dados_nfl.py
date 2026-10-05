"""
02_explorar_dados_nfl.py
--------------------------
Análise Exploratória de Dados (EDA) básica do dataset de jogos da NFL
gerado pelo script 01_baixar_dados_nfl.py.

Objetivo: entender a estrutura dos dados antes de fazer gráficos ou modelos.
"""

import pandas as pd

# 1. Carregamos o CSV que geramos no script anterior.
#    Isso recria o DataFrame a partir do arquivo salvo em disco.
df = pd.read_csv("jogos_nfl_2019_2025.csv")

# 2. .shape mostra (número de linhas, número de colunas).
print("=" * 50)
print("TAMANHO DO DATASET")
print("=" * 50)
print(f"Linhas (jogos): {df.shape[0]}")
print(f"Colunas (informações por jogo): {df.shape[1]}")

# 3. .info() mostra o nome de cada coluna, quantos valores não-nulos ela tem,
#    e o tipo de dado (número inteiro, texto, decimal, etc).
#    É o primeiro comando que qualquer analista roda ao abrir um dataset novo.
print("\n" + "=" * 50)
print("INFORMAÇÕES GERAIS DAS COLUNAS")
print("=" * 50)
print(df.info())

# 4. .isnull().sum() conta quantos valores estão faltando (NaN) em cada coluna.
#    Dados faltando são normais (ex: jogos que ainda não aconteceram não têm placar).
print("\n" + "=" * 50)
print("VALORES FALTANTES POR COLUNA")
print("=" * 50)
print(df.isnull().sum())

# 5. .describe() gera estatísticas básicas (média, mínimo, máximo, etc)
#    de todas as colunas numéricas. Ótimo para ter uma primeira noção
#    de pontuações: qual foi o placar mais alto, a média de pontos, etc.
print("\n" + "=" * 50)
print("ESTATÍSTICAS DESCRITIVAS (colunas numéricas)")
print("=" * 50)
print(df.describe())

# 6. Vamos descobrir: qual foi o jogo com mais pontos combinados (total)?
#    .sort_values() ordena o DataFrame por uma coluna. ascending=False = do maior pro menor.
#    .head(5) pega só as 5 primeiras linhas depois de ordenado.
print("\n" + "=" * 50)
print("TOP 5 JOGOS COM MAIS PONTOS NO TOTAL")
print("=" * 50)
colunas_mostrar = ["season", "week", "home_team", "away_team", "home_score", "away_score", "total"]
top_jogos = df.sort_values("total", ascending=False).head(5)
print(top_jogos[colunas_mostrar])

# 7. Vamos calcular a média de pontos marcados por temporada.
#    .groupby("season") agrupa todas as linhas pelo valor da coluna "season".
#    ["total"].mean() calcula a média da coluna "total" dentro de cada grupo.
print("\n" + "=" * 50)
print("MÉDIA DE PONTOS TOTAIS POR TEMPORADA")
print("=" * 50)
media_por_temporada = df.groupby("season")["total"].mean().round(1)
print(media_por_temporada)

# 8. Quantos jogos cada time jogou como mandante (casa)?
#    .value_counts() conta quantas vezes cada valor aparece numa coluna.
print("\n" + "=" * 50)
print("JOGOS EM CASA POR TIME (top 10)")
print("=" * 50)
print(df["home_team"].value_counts().head(10))

print("\nEDA básica concluída. Use essas informações para decidir quais")
print("perguntas você quer investigar mais a fundo com gráficos.")