"""
14_features_lesoes.py
--------------------------
Cria uma feature de "quantidade de jogadores machucados (Out)" por time,
por semana, e integra à tabela de features que já vínhamos construindo.

Diferença importante em relação às features anteriores:
- media_pontos_marcados_ult3, taxa_vitorias_temporada, etc: precisam de
  .shift() porque descrevem RESULTADOS de jogos passados.
- jogadores_out: NÃO precisa de .shift(), porque o relatório de lesões
  da própria semana já é informação conhecida ANTES do jogo acontecer.
  Não é vazamento de dados usar a informação da semana atual aqui.
"""

import sqlite3
import pandas as pd

conexao = sqlite3.connect("nfl_dados.db")

lesoes = pd.read_csv("lesoes_2019_2025.csv")

# 1. Filtramos só os jogadores marcados como "Out" (praticamente certeza
#    de que não vão jogar). Poderíamos incluir "Doubtful" também, mas
#    vamos começar simples com o status mais claro.
lesoes_out = lesoes[lesoes["report_status"] == "Out"]

# 2. Contamos quantos jogadores "Out" cada time teve, por temporada e semana.
#    .size() conta o número de linhas em cada grupo (equivalente a "COUNT(*)" em SQL).
contagem_lesoes = (
    lesoes_out.groupby(["season", "week", "team"])
    .size()
    .reset_index(name="jogadores_out")
)

print("Prévia da contagem de jogadores 'Out' por time/semana:")
print(contagem_lesoes.head(10))

# 3. Carregamos nossa tabela de features já existente.
jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)

# season na tabela de lesões veio como float (ex: 2019.0) - vamos garantir
# que os tipos batem antes do merge, senão o merge falha silenciosamente
# (junta 0 linhas sem dar erro, um problema clássico e traiçoeiro).
contagem_lesoes["season"] = contagem_lesoes["season"].astype(int)

# 4. Merge: adicionamos a contagem de lesões à tabela principal.
#    how="left" mantém todas as linhas de jogos_por_time, mesmo para
#    times/semanas sem nenhum jogador "Out" registrado.
jogos_por_time = jogos_por_time.merge(
    contagem_lesoes, on=["season", "week", "team"], how="left"
)

# 5. Times/semanas sem registro de lesão viram NaN após o merge - mas aqui
#    o significado correto de "não apareceu" é ZERO jogadores machucados,
#    não "não sabemos". Por isso preenchemos com 0, diferente do que fizemos
#    com dias_descanso (onde NaN realmente significava "não sabemos").
jogos_por_time["jogadores_out"] = jogos_por_time["jogadores_out"].fillna(0).astype(int)

print("\nConferência: Kansas City Chiefs, 2023, com a nova coluna de lesões:")
exemplo = jogos_por_time[(jogos_por_time["team"] == "KC") & (jogos_por_time["season"] == 2023)]
print(exemplo[["week", "opponent", "jogadores_out"]].head(8).to_string(index=False))

# 6. Salvamos a tabela atualizada, substituindo a versão anterior.
jogos_por_time.to_sql("jogos_com_forma_recente", conexao, if_exists="replace", index=False)
print("\nTabela atualizada com a feature 'jogadores_out'.")

conexao.close()