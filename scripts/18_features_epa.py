"""
18_features_epa.py
------------------------
Constrói features de EPA (Expected Points Added) ofensivo e defensivo
por time, e integra à tabela de features já existente.

TRUQUE DE MERGE: a fonte só nos dá EPA da OFENSIVA de cada time (passing_epa,
rushing_epa). Para saber o EPA que o time permitiu na DEFESA, usamos a lógica:
"o que o adversário produziu no ataque é exatamente o que esse time permitiu
na defesa". Por isso cruzamos a tabela com ela mesma, casando cada time com
o adversário dele no mesmo jogo (game_id).
"""

import sqlite3
import pandas as pd

conexao = sqlite3.connect("nfl_dados.db")

time_stats = pd.read_csv("estatisticas_time_2019_2025.csv")

# 1. EPA ofensivo total = passagem + corrida. Não somamos receiving_epa
#    porque, em nível de TIME, ela mede a mesma jogada de passe sob a
#    perspectiva do recebedor - somar as duas contaria a mesma coisa 2x.
time_stats["epa_ofensivo"] = time_stats["passing_epa"] + time_stats["rushing_epa"]

own = time_stats[["game_id", "season", "week", "team", "opponent_team", "epa_ofensivo"]]

# 2. O "truque": juntamos a tabela com ela mesma, casando o "opponent_team"
#    de uma linha com o "team" da outra linha do MESMO jogo (game_id).
#    Isso traz o EPA ofensivo do adversário para dentro da linha do time,
#    representando o que a defesa desse time permitiu.
epa_permitido = own.merge(
    own[["game_id", "team", "epa_ofensivo"]],
    left_on=["game_id", "opponent_team"],
    right_on=["game_id", "team"],
    suffixes=("", "_permitido"),
)[["game_id", "season", "week", "team", "epa_ofensivo", "epa_ofensivo_permitido"]]

print("Prévia da tabela de EPA ofensivo/defensivo por time/jogo:")
print(epa_permitido.head(10))

# ---------------------------------------------------------------------------
# 3. Integramos essa nova informação à tabela de features já existente.
# ---------------------------------------------------------------------------
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)

jogos_por_time = jogos_por_time.merge(
    epa_permitido[["season", "week", "team", "epa_ofensivo", "epa_ofensivo_permitido"]],
    on=["season", "week", "team"],
    how="left",
)

# 4. Ordenação cronológica (necessária de novo, já que recarregamos a tabela).
jogos_por_time = jogos_por_time.sort_values(["team", "season", "week"]).reset_index(drop=True)
grupo_temporada = jogos_por_time.groupby(["team", "season"])

# 5. Média da temporada até aqui (expanding + shift, igual às features anteriores) -
#    o mesmo cuidado de vazamento de dados se aplica: EPA de um jogo só pode
#    ser usado para prever jogos FUTUROS, nunca o próprio jogo.
jogos_por_time["epa_ofensivo_temporada"] = (
    grupo_temporada["epa_ofensivo"].transform(lambda s: s.shift(1).expanding().mean())
)
jogos_por_time["epa_defensivo_temporada"] = (
    grupo_temporada["epa_ofensivo_permitido"].transform(lambda s: s.shift(1).expanding().mean())
)

print("\nConferência: Kansas City Chiefs, 2023:")
exemplo = jogos_por_time[(jogos_por_time["team"] == "KC") & (jogos_por_time["season"] == 2023)]
print(exemplo[["week", "opponent", "epa_ofensivo", "epa_ofensivo_temporada", "epa_defensivo_temporada"]].head(8).to_string(index=False))

jogos_por_time.to_sql("jogos_com_forma_recente", conexao, if_exists="replace", index=False)
print("\nTabela atualizada com features de EPA ofensivo e defensivo.")

conexao.close()