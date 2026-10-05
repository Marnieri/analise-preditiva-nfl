"""
08_montar_banco_dados.py
----------------------------
Cria um banco de dados SQLite único, reunindo os três datasets que já
temos em CSV. A partir daqui, o banco de dados passa a ser a "fonte da
verdade" do projeto, em vez de arquivos CSV soltos.

Conceitos novos:
- sqlite3: módulo padrão do Python para criar/acessar bancos SQLite
- SQL: linguagem para consultar dados (parecida em espírito com o pandas,
  mas com sintaxe própria: SELECT, FROM, WHERE, GROUP BY, JOIN...)
"""

import sqlite3
import pandas as pd

# 1. Criamos (ou conectamos, se já existir) um arquivo de banco de dados.
#    Isso vai gerar um arquivo "nfl_dados.db" na pasta do projeto.
conexao = sqlite3.connect("nfl_dados.db")

# 2. Carregamos os três CSVs que já temos.
jogos = pd.read_csv("jogos_nfl_2019_2025.csv")
jogadores = pd.read_csv("estatisticas_jogadores_2019_2025.csv")
jogadores_contexto = pd.read_csv("dados_jogadores_com_contexto_jogo.csv")

# 3. .to_sql() escreve um DataFrame como uma TABELA dentro do banco.
#    if_exists="replace": se já existir uma tabela com esse nome, substitui.
#    Isso é útil enquanto o projeto está em desenvolvimento — toda vez que
#    você rodar esse script, o banco é reconstruído do zero com dados atuais.
jogos.to_sql("jogos", conexao, if_exists="replace", index=False)
jogadores.to_sql("jogadores", conexao, if_exists="replace", index=False)
jogadores_contexto.to_sql("jogadores_contexto", conexao, if_exists="replace", index=False)

print("Banco de dados criado com 3 tabelas: jogos, jogadores, jogadores_contexto")

# ---------------------------------------------------------------------------
# 4. Agora vamos FAZER PERGUNTAS ao banco usando SQL, em vez de pandas.
#    pd.read_sql() roda uma consulta SQL e devolve o resultado como DataFrame
#    (assim dá pra continuar usando pandas normalmente depois da consulta).
# ---------------------------------------------------------------------------

# Exemplo 1: os 5 primeiros jogos da temporada 2023.
# SELECT * = "pegue todas as colunas". WHERE filtra linhas. LIMIT restringe quantidade.
print("\n" + "=" * 50)
print("EXEMPLO 1: primeiros 5 jogos de 2023")
print("=" * 50)
consulta1 = """
    SELECT season, week, home_team, away_team, home_score, away_score
    FROM jogos
    WHERE season = 2023
    LIMIT 5
"""
print(pd.read_sql(consulta1, conexao))

# Exemplo 2: média de pontos totais por temporada, DIRETO no SQL.
# Isso é o equivalente em SQL do df.groupby("season")["total"].mean() que já fizemos.
print("\n" + "=" * 50)
print("EXEMPLO 2: média de pontos totais por temporada (via SQL)")
print("=" * 50)
consulta2 = """
    SELECT season, ROUND(AVG(total), 1) AS media_pontos
    FROM jogos
    GROUP BY season
    ORDER BY season
"""
print(pd.read_sql(consulta2, conexao))

# Exemplo 3: um JOIN em SQL — o equivalente ao merge() que já fizemos em pandas.
# Aqui buscamos os 5 jogadores com mais jazidas de passe, já trazendo o contexto
# de quantos pontos o time fez naquele jogo (dado que está na tabela jogadores_contexto,
# então esse já vem pronto, mas o exemplo mostra a sintaxe de JOIN para quando
# você precisar cruzar tabelas diretamente dentro do SQL).
print("\n" + "=" * 50)
print("EXEMPLO 3: top 5 QBs em jazidas de passe, com resultado do jogo")
print("=" * 50)
consulta3 = """
    SELECT player_display_name, season, week, passing_yards, pontos_time, pontos_adversario, vitoria
    FROM jogadores_contexto
    WHERE position = 'QB'
    ORDER BY passing_yards DESC
    LIMIT 5
"""
print(pd.read_sql(consulta3, conexao))

# 5. Sempre feche a conexão ao terminar, para liberar o arquivo.
conexao.close()
print("\nConexão com o banco fechada. Arquivo 'nfl_dados.db' pronto para uso.")