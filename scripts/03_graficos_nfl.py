"""
03_graficos_nfl.py
--------------------
Primeiros gráficos de exploração visual do dataset de jogos da NFL.

Bibliotecas novas usadas aqui:
- matplotlib: biblioteca base para criar gráficos em Python
- seaborn: construída sobre o matplotlib, deixa os gráficos mais bonitos
  e facilita alguns tipos de gráfico estatístico comuns
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Carregamos o mesmo CSV de sempre.
df = pd.read_csv("jogos_nfl_2019_2025.csv")

# 2. Um "estilo" visual pronto do seaborn, para os gráficos ficarem mais legíveis.
sns.set_style("whitegrid")


# ---------------------------------------------------------------------------
# GRÁFICO 1: Média de pontos totais por temporada (gráfico de linha)
# ---------------------------------------------------------------------------
# Reaproveitamos o groupby que já tínhamos feito na EDA.
media_por_temporada = df.groupby("season")["total"].mean()

plt.figure(figsize=(8, 5))  # figsize define o tamanho da imagem (largura, altura em polegadas)
plt.plot(media_por_temporada.index, media_por_temporada.values, marker="o")
plt.title("Média de pontos totais por jogo, por temporada")
plt.xlabel("Temporada")
plt.ylabel("Média de pontos (casa + visitante)")
plt.xticks(media_por_temporada.index)  # garante que todo ano apareça no eixo X
plt.tight_layout()  # ajusta as margens para nada ficar cortado
plt.savefig("grafico_1_media_pontos_por_temporada.png")  # salva a imagem em disco
print("Gráfico 1 salvo: grafico_1_media_pontos_por_temporada.png")
plt.show()  # abre uma janela mostrando o gráfico


# ---------------------------------------------------------------------------
# GRÁFICO 2: Distribuição do total de pontos por jogo (histograma)
# ---------------------------------------------------------------------------
# Um histograma mostra quantos jogos caem em cada "faixa" de pontuação total.
# Isso ajuda a visualizar se a maioria dos jogos é equilibrada em pontos
# ou se há muitos extremos (jogos muito baixos ou muito altos em pontuação).
plt.figure(figsize=(8, 5))
sns.histplot(df["total"], bins=20, kde=True)
# bins=20 divide os dados em 20 faixas. kde=True desenha uma curva suave
# por cima, mostrando a tendência geral da distribuição.
plt.title("Distribuição do total de pontos por jogo (2019-2023)")
plt.xlabel("Total de pontos no jogo")
plt.ylabel("Quantidade de jogos")
plt.tight_layout()
plt.savefig("grafico_2_distribuicao_pontos.png")
print("Gráfico 2 salvo: grafico_2_distribuicao_pontos.png")
plt.show()


# ---------------------------------------------------------------------------
# GRÁFICO 3: Top 10 times com mais vitórias em casa (gráfico de barras)
# ---------------------------------------------------------------------------
# Primeiro precisamos calcular quem venceu cada jogo.
# Se home_score > away_score, o time da casa venceu.
df["vencedor_casa"] = df["home_score"] > df["away_score"]

# Filtramos só os jogos em que o time da casa venceu,
# depois contamos quantas vitórias em casa cada time teve.
vitorias_em_casa = df[df["vencedor_casa"]]["home_team"].value_counts().head(10)

plt.figure(figsize=(8, 5))
sns.barplot(x=vitorias_em_casa.values, y=vitorias_em_casa.index, orient="h")
plt.title("Top 10 times com mais vitórias em casa (2019-2023)")
plt.xlabel("Número de vitórias em casa")
plt.ylabel("Time")
plt.tight_layout()
plt.savefig("grafico_3_top_vitorias_casa.png")
print("Gráfico 3 salvo: grafico_3_top_vitorias_casa.png")
plt.show()

print("\nTodos os gráficos foram gerados e salvos como imagens .png na pasta do projeto.")