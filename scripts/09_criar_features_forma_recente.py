"""
09_criar_features_forma_recente.py
--------------------------------------
Cria features de "forma recente" por time: média móvel de pontos marcados,
pontos sofridos e taxa de vitórias nos últimos N jogos.

CONCEITO CRÍTICO: VAZAMENTO DE DADOS (data leakage)
-----------------------------------------------------
Se estamos tentando prever o resultado de um jogo ANTES dele acontecer,
a "forma recente" de um time só pode usar informações de jogos ANTERIORES
àquele jogo — nunca informações do próprio jogo que queremos prever.

Erro comum de iniciante: calcular a média móvel incluindo o jogo atual.
Isso "vaza" informação do futuro para o passado e faz o modelo parecer
ótimo em teste, mas inútil na prática (porque na vida real você não sabe
o placar do jogo antes dele acontecer).

Para evitar isso, usamos .shift(1) — que "empurra" os valores uma posição
para frente, garantindo que a média móvel de um jogo só olhe para os
jogos ANTERIORES a ele, nunca para ele mesmo.
"""

import sqlite3
import pandas as pd

conexao = sqlite3.connect("nfl_dados.db")

# 1. Carregamos a tabela de jogos direto do banco (em vez do CSV, já que
#    agora o banco é nossa fonte principal).
jogos = pd.read_sql("SELECT * FROM jogos", conexao)

# 2. Reformatamos para "1 linha por time por jogo", igual fizemos antes,
#    mas agora corrigindo também a sigla OAK -> LV para manter consistência.
jogos["home_team"] = jogos["home_team"].replace({"OAK": "LV"})
jogos["away_team"] = jogos["away_team"].replace({"OAK": "LV"})

casa = jogos.rename(columns={
    "home_team": "team", "away_team": "opponent",
    "home_score": "pontos_time", "away_score": "pontos_adversario",
})
casa["local"] = "casa"

fora = jogos.rename(columns={
    "away_team": "team", "home_team": "opponent",
    "away_score": "pontos_time", "home_score": "pontos_adversario",
})
fora["local"] = "fora"

colunas = ["season", "week", "team", "opponent", "pontos_time", "pontos_adversario", "local"]
jogos_por_time = pd.concat([casa[colunas], fora[colunas]], ignore_index=True)

jogos_por_time["vitoria"] = (jogos_por_time["pontos_time"] > jogos_por_time["pontos_adversario"]).astype(int)

# 3. ORDENAÇÃO É ESSENCIAL: para calcular "os últimos 3 jogos" corretamente,
#    os dados precisam estar em ordem cronológica dentro de cada time.
jogos_por_time = jogos_por_time.sort_values(["team", "season", "week"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# 4. Calculamos as médias móveis, POR TIME E POR TEMPORADA (groupby),
#    usando uma janela (window) dos últimos 3 jogos.
# ---------------------------------------------------------------------------
# .groupby(["team", "season"]) garante que a média móvel não "vaze" de uma
# temporada para outra (o elenco muda bastante de uma temporada pra outra).
#
# .shift(1) empurra os valores uma linha para baixo ANTES de calcular a média,
# garantindo que o jogo da linha atual não entre na própria média.
#
# .rolling(window=3, min_periods=1).mean() calcula a média dos últimos 3
# valores disponíveis. min_periods=1 permite calcular mesmo com menos de 3
# jogos anteriores (ex: na semana 2, só temos 1 jogo anterior — melhor ter
# uma média com 1 jogo do que não ter nada, o NaN das primeiras semanas
# ainda vai aparecer, e isso é esperado e correto).

grupo = jogos_por_time.groupby(["team", "season"])

jogos_por_time["media_pontos_marcados_ult3"] = (
    grupo["pontos_time"].transform(lambda s: s.shift(1).rolling(window=3, min_periods=1).mean())
)
jogos_por_time["media_pontos_sofridos_ult3"] = (
    grupo["pontos_adversario"].transform(lambda s: s.shift(1).rolling(window=3, min_periods=1).mean())
)
jogos_por_time["taxa_vitorias_ult3"] = (
    grupo["vitoria"].transform(lambda s: s.shift(1).rolling(window=3, min_periods=1).mean())
)

# 5. Vamos conferir com um time específico, olhando as primeiras semanas de
#    uma temporada, para confirmar visualmente que o shift funcionou certo.
print("=" * 60)
print("CONFERÊNCIA: Kansas City Chiefs (KC) na temporada 2023")
print("=" * 60)
exemplo = jogos_por_time[(jogos_por_time["team"] == "KC") & (jogos_por_time["season"] == 2023)]
colunas_mostrar = ["week", "opponent", "pontos_time", "pontos_adversario", "vitoria",
                   "media_pontos_marcados_ult3", "taxa_vitorias_ult3"]
print(exemplo[colunas_mostrar].head(8).to_string(index=False))

print("\nRepare: na semana 1, as médias aparecem como NaN (vazio) —")
print("é esperado, porque não existe jogo anterior para calcular a média.")
print("Na semana 2, a média usa só o jogo da semana 1. Na semana 4 em diante,")
print("já usa a média dos 3 jogos anteriores. Nunca inclui o jogo da própria linha.")

# 6. Salvamos essa tabela enriquecida como uma nova tabela no banco.
jogos_por_time.to_sql("jogos_com_forma_recente", conexao, if_exists="replace", index=False)
print("\nSalvo como tabela 'jogos_com_forma_recente' no banco de dados.")

conexao.close()