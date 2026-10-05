"""
10_features_completas.py
----------------------------
Consolida todas as features de time num único script:
- Forma recente (média móvel dos últimos 3 jogos) - já tínhamos
- Média acumulada da temporada até aquele jogo (nova)
- Dias de descanso desde o último jogo (nova)
- Flag de "semana curta" (jogo com pouco descanso, ex: quinta-feira) (nova)

Mantemos o mesmo cuidado com VAZAMENTO DE DADOS de antes: tudo que descreve
"como o time está indo" só pode olhar para jogos ANTERIORES ao jogo da linha.
"""

import sqlite3
import pandas as pd

conexao = sqlite3.connect("nfl_dados.db")

jogos = pd.read_sql("SELECT * FROM jogos", conexao)
jogos["home_team"] = jogos["home_team"].replace({"OAK": "LV"})
jogos["away_team"] = jogos["away_team"].replace({"OAK": "LV"})

# 1. Convertemos a coluna de data de texto para um tipo "data" de verdade.
#    Sem isso, o pandas não sabe calcular diferenças entre datas.
jogos["gameday"] = pd.to_datetime(jogos["gameday"])

# 2. Reformatação de sempre: 1 linha por time por jogo. Agora incluindo "gameday".
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

colunas = ["season", "week", "gameday", "team", "opponent", "pontos_time", "pontos_adversario", "local"]
jogos_por_time = pd.concat([casa[colunas], fora[colunas]], ignore_index=True)
jogos_por_time["vitoria"] = (jogos_por_time["pontos_time"] > jogos_por_time["pontos_adversario"]).astype(int)

# 3. Ordenação cronológica por time - essencial para tudo que vem a seguir.
jogos_por_time = jogos_por_time.sort_values(["team", "gameday"]).reset_index(drop=True)

grupo_temporada = jogos_por_time.groupby(["team", "season"])

# ---------------------------------------------------------------------------
# FEATURE 1 (já tínhamos): forma recente - média móvel dos últimos 3 jogos
# ---------------------------------------------------------------------------
jogos_por_time["media_pontos_marcados_ult3"] = (
    grupo_temporada["pontos_time"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
)
jogos_por_time["media_pontos_sofridos_ult3"] = (
    grupo_temporada["pontos_adversario"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
)
jogos_por_time["taxa_vitorias_ult3"] = (
    grupo_temporada["vitoria"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
)

# ---------------------------------------------------------------------------
# FEATURE 2 (nova): média da temporada até aqui (expanding, não rolling)
# ---------------------------------------------------------------------------
# .expanding() é parecido com .rolling(), mas em vez de uma janela de
# tamanho fixo (ex: 3 jogos), ela usa TODOS os jogos anteriores disponíveis.
# É o jeito certo de calcular "a média da temporada até agora".
jogos_por_time["media_pontos_marcados_temporada"] = (
    grupo_temporada["pontos_time"].transform(lambda s: s.shift(1).expanding().mean())
)
jogos_por_time["media_pontos_sofridos_temporada"] = (
    grupo_temporada["pontos_adversario"].transform(lambda s: s.shift(1).expanding().mean())
)
jogos_por_time["taxa_vitorias_temporada"] = (
    grupo_temporada["vitoria"].transform(lambda s: s.shift(1).expanding().mean())
)

# ---------------------------------------------------------------------------
# FEATURE 3 (nova): dias de descanso desde o último jogo
# ---------------------------------------------------------------------------
# .diff() calcula a diferença entre uma linha e a linha anterior.
# Como já ordenamos por team + gameday, isso nos dá "dias desde o jogo anterior
# DESSE MESMO TIME" (o groupby garante que não misture times diferentes).
jogos_por_time["dias_descanso"] = (
    jogos_por_time.groupby("team")["gameday"].diff().dt.days
)

# No primeiro jogo de cada temporada (ou o primeiro jogo do time no dataset),
# não existe "jogo anterior" dentro da métrica que faz sentido (seria o
# intervalo de offseason, que é enorme e não comparável a descanso normal).
# Marcamos esses casos como NaN explicitamente.
primeiro_jogo_temporada = jogos_por_time.groupby(["team", "season"]).cumcount() == 0
jogos_por_time.loc[primeiro_jogo_temporada, "dias_descanso"] = None

# ---------------------------------------------------------------------------
# FEATURE 4 (nova): flag de "semana curta" (pouco descanso, ex: jogo de quinta)
# ---------------------------------------------------------------------------
# Um jogo normal tem 7 dias de intervalo (domingo a domingo). Se o descanso
# foi de 4 dias ou menos, é sinal de jogo na quinta-feira (Thursday Night Football),
# que estatisticamente costuma prejudicar o desempenho por menor tempo de preparo.
#
# CUIDADO: "NaN <= 4" sempre retorna False em Python/pandas, NUNCA NaN.
# Se calculássemos direto (dias_descanso <= 4), o primeiro jogo de cada
# temporada (onde dias_descanso é vazio) ficaria incorretamente marcado
# como "não é semana curta" (False/0), quando na verdade é "não sabemos".
# Por isso, calculamos a comparação primeiro e SÓ DEPOIS restauramos
# manualmente os vazios usando .where() com a condição de onde dias_descanso
# já era nulo.
semana_curta_calculada = jogos_por_time["dias_descanso"] <= 4
jogos_por_time["semana_curta"] = semana_curta_calculada.astype("Int64")
jogos_por_time.loc[jogos_por_time["dias_descanso"].isna(), "semana_curta"] = pd.NA
# Usamos "Int64" (maiúsculo) em vez de "int" para permitir valores NaN também
# nessa coluna (nos primeiros jogos de temporada, onde dias_descanso é vazio).

# ---------------------------------------------------------------------------
# Conferência: vamos olhar o Kansas City de novo, agora com todas as features.
# ---------------------------------------------------------------------------
print("=" * 70)
print("CONFERÊNCIA: Kansas City Chiefs (KC), temporada 2023")
print("=" * 70)
exemplo = jogos_por_time[(jogos_por_time["team"] == "KC") & (jogos_por_time["season"] == 2023)]
colunas_mostrar = [
    "week", "gameday", "opponent", "pontos_time", "vitoria",
    "media_pontos_marcados_temporada", "dias_descanso", "semana_curta",
]
print(exemplo[colunas_mostrar].head(8).to_string(index=False))

# Salvamos a tabela final, substituindo a versão anterior (mais simples).
jogos_por_time.to_sql("jogos_com_forma_recente", conexao, if_exists="replace", index=False)
print("\nTabela 'jogos_com_forma_recente' atualizada com todas as features.")

conexao.close()