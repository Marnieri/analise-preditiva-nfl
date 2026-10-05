"""
00_pipeline_semanal.py
------------------------
Script ÚNICO E CONSOLIDADO para atualizar os dados e gerar previsões da
próxima rodada da NFL. Substitui a necessidade de rodar os scripts 01-20
manualmente toda semana (aqueles continuam existindo como registro do seu
aprendizado, mas não precisam mais ser rodados individualmente).

COMO USAR: rode só este arquivo, uma vez por semana (idealmente entre
terça e quinta-feira, depois que a NFL corrige as estatísticas oficiais
dos jogos do fim de semana anterior).

Atualize ULTIMA_TEMPORADA abaixo quando uma nova temporada da NFL começar.
"""

import sqlite3
from pathlib import Path
import pandas as pd
import nflreadpy as nfl
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ============================================================
# CAMINHOS - ancorados na raiz do projeto, não importa de onde
# o script seja executado (isso evita o problema clássico de
# "working directory" diferente entre PyCharm e Streamlit).
# ============================================================
# Path(__file__) = caminho deste próprio arquivo. .parent sobe um nível
# de pasta. Como este script está em "scripts/", subimos 1 nível para
# chegar na raiz do projeto.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
BANCO = RAIZ_PROJETO / "nfl_dados.db"
ARQUIVO_PREVISOES = RAIZ_PROJETO / "previsoes_proxima_semana.csv"

# ============================================================
# CONFIGURAÇÃO - o único lugar que você precisa atualizar por ano
# ============================================================
ULTIMA_TEMPORADA = 2026
TEMPORADAS = list(range(2019, ULTIMA_TEMPORADA + 1))

# Features "enxutas" validadas na sessão de melhoria do modelo -
# mesma performance da versão completa, sem redundância entre si.
FEATURES = [
    "taxa_vitorias_temporada_casa", "taxa_vitorias_temporada_fora",
    "dias_descanso_casa", "dias_descanso_fora",
    "epa_ofensivo_temporada_casa", "epa_defensivo_temporada_casa",
    "epa_ofensivo_temporada_fora", "epa_defensivo_temporada_fora",
]

print(f"Atualizando dados das temporadas: {TEMPORADAS}")


def baixar_temporadas_disponiveis(funcao_carregamento, temporadas, **kwargs):
    """Tenta baixar as temporadas pedidas. Se a mais recente ainda não tiver
    dados publicados (comum ANTES do início da temporada, ou nas primeiras
    semanas dela), tenta de novo sem ela, avisando o motivo, até conseguir
    ou esgotar as opções."""
    temporadas_restantes = list(temporadas)
    while temporadas_restantes:
        try:
            dados = funcao_carregamento(temporadas_restantes, **kwargs).to_pandas()
            return dados, temporadas_restantes
        except Exception as erro:
            temporada_removida = temporadas_restantes.pop()
            print(f"  Aviso: dados de {temporada_removida} ainda não disponíveis "
                  f"({erro.__class__.__name__}). Tentando sem essa temporada...")
    raise RuntimeError("Não foi possível baixar dados de nenhuma temporada.")

# ============================================================
# [1/5] BAIXAR DADOS ATUALIZADOS
# ============================================================
print("\n[1/5] Baixando jogos (calendário/placares)...")
jogos = nfl.load_schedules(TEMPORADAS).to_pandas()
jogos["home_team"] = jogos["home_team"].replace({"OAK": "LV"})
jogos["away_team"] = jogos["away_team"].replace({"OAK": "LV"})
jogos["gameday"] = pd.to_datetime(jogos["gameday"])

print("[1/5] Baixando estatísticas de time (EPA)...")
time_stats, temporadas_time_stats = baixar_temporadas_disponiveis(
    nfl.load_team_stats, TEMPORADAS, summary_level="week"
)
time_stats["team"] = time_stats["team"].replace({"OAK": "LV"})
time_stats["opponent_team"] = time_stats["opponent_team"].replace({"OAK": "LV"})

print("[1/5] Baixando estatísticas de jogadores (para o dashboard)...")
jogadores_brutos, temporadas_jogadores = baixar_temporadas_disponiveis(nfl.load_player_stats, TEMPORADAS)

# Mesmo mapeamento defensivo de colunas usado no script 04, para lidar com
# possíveis diferenças de nomenclatura na fonte.
candidatos_por_campo = {
    "player_display_name": ["player_display_name", "display_name", "player_name"],
    "position": ["position"],
    "recent_team": ["recent_team", "team"],
    "season": ["season"],
    "week": ["week"],
    "completions": ["completions"], "attempts": ["attempts"],
    "passing_yards": ["passing_yards"], "passing_tds": ["passing_tds"],
    "interceptions": ["interceptions", "passing_interceptions"],
    "carries": ["carries"], "rushing_yards": ["rushing_yards"], "rushing_tds": ["rushing_tds"],
    "receptions": ["receptions"], "targets": ["targets"],
    "receiving_yards": ["receiving_yards"], "receiving_tds": ["receiving_tds"],
    "fantasy_points": ["fantasy_points"],
    # Estatísticas defensivas - novas, para a página de jogadores por posição.
    "def_tackles_solo": ["def_tackles_solo"],
    "def_tackles_with_assist": ["def_tackles_with_assist"],
    "def_tackles_for_loss": ["def_tackles_for_loss"],
    "def_sacks": ["def_sacks"],
    "def_qb_hits": ["def_qb_hits"],
    "def_interceptions": ["def_interceptions"],
    "def_pass_defended": ["def_pass_defended"],
    "def_tds": ["def_tds"],
    "def_fumbles_forced": ["def_fumbles_forced"],
}
colunas_finais = {}
for nome_padrao, candidatos in candidatos_por_campo.items():
    encontrado = next((c for c in candidatos if c in jogadores_brutos.columns), None)
    if encontrado:
        colunas_finais[nome_padrao] = encontrado
jogadores = jogadores_brutos[list(colunas_finais.values())].rename(columns={v: k for k, v in colunas_finais.items()})
jogadores["recent_team"] = jogadores["recent_team"].replace({"OAK": "LV"})

# ============================================================
# [2/5] SALVAR NO BANCO DE DADOS
# ============================================================
print("[2/5] Salvando no banco de dados...")
conexao = sqlite3.connect(BANCO)
jogos.to_sql("jogos", conexao, if_exists="replace", index=False)
time_stats.to_sql("estatisticas_time", conexao, if_exists="replace", index=False)
jogadores.to_sql("jogadores", conexao, if_exists="replace", index=False)

# ============================================================
# [3/5] RECALCULAR FEATURES (forma recente, descanso, EPA)
# ============================================================
print("[3/5] Calculando features (forma recente, descanso, EPA)...")

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

colunas = ["season", "week", "gameday", "team", "opponent", "pontos_time", "pontos_adversario", "local", "div_game"]
jogos_por_time = pd.concat([casa[colunas], fora[colunas]], ignore_index=True)

# "vitoria" só existe para jogos já disputados (placar preenchido). Jogos
# futuros ficam de propósito sem essa informação - vamos usá-los só pelas
# FEATURES (que dependem de jogos passados), nunca por um resultado que
# ainda não aconteceu.
jogos_por_time["jogo_disputado"] = jogos_por_time["pontos_time"].notna() & jogos_por_time["pontos_adversario"].notna()
jogos_por_time["vitoria"] = pd.NA
jogos_por_time.loc[jogos_por_time["jogo_disputado"], "vitoria"] = (
    jogos_por_time.loc[jogos_por_time["jogo_disputado"], "pontos_time"]
    > jogos_por_time.loc[jogos_por_time["jogo_disputado"], "pontos_adversario"]
).astype(int)

jogos_por_time = jogos_por_time.sort_values(["team", "gameday"]).reset_index(drop=True)
grupo_temporada = jogos_por_time.groupby(["team", "season"])

jogos_por_time["media_pontos_marcados_temporada"] = grupo_temporada["pontos_time"].transform(
    lambda s: s.shift(1).expanding().mean()
)
jogos_por_time["media_pontos_sofridos_temporada"] = grupo_temporada["pontos_adversario"].transform(
    lambda s: s.shift(1).expanding().mean()
)
jogos_por_time["taxa_vitorias_temporada"] = grupo_temporada["vitoria"].transform(
    lambda s: pd.to_numeric(s, errors="coerce").shift(1).expanding().mean()
)

jogos_por_time["dias_descanso"] = jogos_por_time.groupby("team")["gameday"].diff().dt.days
primeiro_jogo_temporada = jogos_por_time.groupby(["team", "season"]).cumcount() == 0
# Não faz sentido contar o offseason inteiro como "descanso", então
# esvaziamos esse valor no primeiro jogo de cada temporada...
jogos_por_time.loc[primeiro_jogo_temporada, "dias_descanso"] = None
# ...mas preenchemos de volta com um valor neutro (7 dias = 1 semana padrão),
# em vez de deixar vazio. Um valor vazio aqui excluiria esses jogos do
# treino E da avaliação do modelo (dropna elimina a linha inteira) - e
# como isso inclui a semana 1 de TODA temporada nova, o modelo nunca
# teria dados pra prever nem avaliar a primeira rodada do ano. Usar 7 dias
# é uma escolha neutra: nenhum dos dois times leva vantagem de descanso
# nesse jogo específico.
jogos_por_time.loc[primeiro_jogo_temporada, "dias_descanso"] = 7

# EPA: "o que o adversário produziu no ataque = o que este time permitiu na defesa"
time_stats["epa_ofensivo"] = time_stats["passing_epa"] + time_stats["rushing_epa"]
own = time_stats[["game_id", "season", "week", "team", "opponent_team", "epa_ofensivo"]]
epa_permitido = own.merge(
    own[["game_id", "team", "epa_ofensivo"]],
    left_on=["game_id", "opponent_team"], right_on=["game_id", "team"],
    suffixes=("", "_permitido"),
)[["season", "week", "team", "epa_ofensivo", "epa_ofensivo_permitido"]]

jogos_por_time = jogos_por_time.merge(epa_permitido, on=["season", "week", "team"], how="left")
jogos_por_time = jogos_por_time.sort_values(["team", "season", "week"]).reset_index(drop=True)
grupo_temporada = jogos_por_time.groupby(["team", "season"])
jogos_por_time["epa_ofensivo_temporada"] = grupo_temporada["epa_ofensivo"].transform(
    lambda s: s.shift(1).expanding().mean()
)
jogos_por_time["epa_defensivo_temporada"] = grupo_temporada["epa_ofensivo_permitido"].transform(
    lambda s: s.shift(1).expanding().mean()
)

# ============================================================
# CONTINUIDADE ENTRE TEMPORADAS
# ============================================================
# Sem isso, a semana 1 de toda temporada fica sem features (não existe
# "jogo anterior DESSA temporada" pra calcular a média) - o que significa
# nunca conseguir prever nem avaliar jogos de semana 1. Para resolver,
# usamos a forma do time ao FINAL da temporada anterior como ponto de
# partida. Isso não é vazamento de dados: só usamos temporadas já 100%
# encerradas para "informar" o início da temporada seguinte.
colunas_forma = [
    "media_pontos_marcados_temporada", "media_pontos_sofridos_temporada",
    "taxa_vitorias_temporada", "epa_ofensivo_temporada", "epa_defensivo_temporada",
]

resumo_temporada = jogos_por_time[jogos_por_time["jogo_disputado"]].groupby(["team", "season"]).agg(
    media_pontos_marcados_temporada=("pontos_time", "mean"),
    media_pontos_sofridos_temporada=("pontos_adversario", "mean"),
    taxa_vitorias_temporada=("vitoria", lambda s: pd.to_numeric(s, errors="coerce").mean()),
    epa_ofensivo_temporada=("epa_ofensivo", "mean"),
    epa_defensivo_temporada=("epa_ofensivo_permitido", "mean"),
).reset_index()

# Deslocamos a temporada em +1: o resumo da temporada N vira o "ponto de
# partida" usado na temporada N+1.
resumo_temporada_anterior = resumo_temporada.copy()
resumo_temporada_anterior["season"] = resumo_temporada_anterior["season"] + 1
resumo_temporada_anterior = resumo_temporada_anterior.rename(
    columns={c: f"{c}_temp_anterior" for c in colunas_forma}
)

jogos_por_time = jogos_por_time.merge(resumo_temporada_anterior, on=["team", "season"], how="left")

# Preenchemos SÓ os valores vazios (na prática, só a semana 1 de cada
# temporada deveria estar vazia neste ponto) com a forma da temporada anterior.
for coluna in colunas_forma:
    jogos_por_time[coluna] = jogos_por_time[coluna].fillna(jogos_por_time[f"{coluna}_temp_anterior"])

jogos_por_time = jogos_por_time.drop(columns=[f"{c}_temp_anterior" for c in colunas_forma])

jogos_por_time.to_sql("jogos_com_forma_recente", conexao, if_exists="replace", index=False)

# ============================================================
# [4/5] TREINAR O MODELO COM TODOS OS JOGOS JÁ DISPUTADOS
# ============================================================
print("[4/5] Treinando o modelo com todos os jogos já disputados...")

casa2 = jogos_por_time[jogos_por_time["local"] == "casa"].rename(columns={"team": "home_team", "opponent": "away_team"})
fora2 = jogos_por_time[jogos_por_time["local"] == "fora"].rename(columns={"team": "away_team", "opponent": "home_team"})
jogos_completos = casa2.merge(fora2, on=["season", "week", "home_team", "away_team"], suffixes=("_casa", "_fora"))

jogos_completos["jogo_disputado"] = jogos_completos["pontos_time_casa"].notna() & jogos_completos["pontos_time_fora"].notna()
jogos_completos["home_venceu"] = pd.NA
jogos_completos.loc[jogos_completos["jogo_disputado"], "home_venceu"] = (
    jogos_completos.loc[jogos_completos["jogo_disputado"], "pontos_time_casa"]
    > jogos_completos.loc[jogos_completos["jogo_disputado"], "pontos_time_fora"]
).astype(int)

dados_treino = jogos_completos[jogos_completos["jogo_disputado"]].dropna(subset=FEATURES + ["home_venceu"])

scaler = StandardScaler()
X_treino = scaler.fit_transform(dados_treino[FEATURES])
y_treino = dados_treino["home_venceu"].astype(int)

modelo = LogisticRegression()
modelo.fit(X_treino, y_treino)
print(f"Modelo treinado com {len(dados_treino)} jogos históricos.")

# ============================================================
# [5/5] PREVISÕES PARA A PRÓXIMA RODADA
# ============================================================
print("[5/5] Gerando previsões para a próxima rodada...")

jogos_futuros = jogos_completos[~jogos_completos["jogo_disputado"]].dropna(subset=FEATURES).copy()

if jogos_futuros.empty:
    print("\nNenhum jogo futuro com features completas encontrado ainda.")
    print("Isso é normal na semana 1 de uma temporada nova (ainda não há")
    print("histórico daquela temporada para calcular as médias) - as previsões")
    print("voltam a aparecer a partir da semana 2.")
    # Criamos o arquivo mesmo vazio (só com cabeçalho), para o dashboard
    # conseguir distinguir "arquivo não existe" (nunca rodou o pipeline)
    # de "rodou certinho, só que ainda não há previsão disponível".
    pd.DataFrame(columns=[
        "season", "week", "home_team", "away_team", "prob_casa_vencer_%",
        "spread_line", "home_moneyline", "away_moneyline",
    ]).to_csv(ARQUIVO_PREVISOES, index=False)
else:
    proxima_semana = jogos_futuros["week"].min()
    proxima_rodada = jogos_futuros[jogos_futuros["week"] == proxima_semana].copy()

    X_prever = scaler.transform(proxima_rodada[FEATURES])
    proxima_rodada["probabilidade_casa_vencer"] = modelo.predict_proba(X_prever)[:, 1]

    # Trazendo odds de mercado para comparação, se já estiverem publicadas.
    odds_cols = ["season", "week", "home_team", "away_team", "spread_line", "home_moneyline", "away_moneyline"]
    proxima_rodada = proxima_rodada.merge(jogos[odds_cols], on=["season", "week", "home_team", "away_team"], how="left")

    proxima_rodada["probabilidade_casa_vencer"] = (proxima_rodada["probabilidade_casa_vencer"] * 100).round(1)

    colunas_exibir = ["season", "week", "home_team", "away_team", "probabilidade_casa_vencer", "spread_line", "home_moneyline", "away_moneyline"]
    resultado_final = proxima_rodada[colunas_exibir].rename(columns={
        "probabilidade_casa_vencer": "prob_casa_vencer_%"
    })

    print(f"\n{'=' * 70}")
    print(f"PREVISÕES PARA A SEMANA {int(proxima_semana)} - TEMPORADA {ULTIMA_TEMPORADA}")
    print(f"{'=' * 70}")
    print(resultado_final.to_string(index=False))

    resultado_final.to_csv(ARQUIVO_PREVISOES, index=False)
    print(f"\nSalvo em '{ARQUIVO_PREVISOES}'.")

# ============================================================
# EXTRA: comparação com a ÚLTIMA rodada já disputada
# ============================================================
# Útil tanto como demonstração fora de temporada (não há jogo futuro para
# prever) quanto como um "placar de acertos" contínuo do modelo durante
# a temporada - toda semana você pode ver como ele se saiu na rodada anterior.
print("\nGerando comparação com a última rodada já disputada...")

jogos_disputados_completos = jogos_completos[jogos_completos["jogo_disputado"]].dropna(subset=FEATURES).copy()

if jogos_disputados_completos.empty:
    print("Nenhum jogo disputado com features completas encontrado - pulei esta etapa.")
else:
    ultima_temporada_disputada = jogos_disputados_completos["season"].max()
    ultima_semana_disputada = jogos_disputados_completos[
        jogos_disputados_completos["season"] == ultima_temporada_disputada
    ]["week"].max()

    ultima_rodada = jogos_disputados_completos[
        (jogos_disputados_completos["season"] == ultima_temporada_disputada)
        & (jogos_disputados_completos["week"] == ultima_semana_disputada)
    ].copy()

    X_ultima = scaler.transform(ultima_rodada[FEATURES])
    ultima_rodada["prob_casa_vencer_%"] = (modelo.predict_proba(X_ultima)[:, 1] * 100).round(1)
    ultima_rodada["home_venceu"] = ultima_rodada["home_venceu"].astype(int)
    ultima_rodada["resultado_real"] = ultima_rodada["home_venceu"].map({1: "Casa venceu", 0: "Visitante venceu"})
    ultima_rodada["previsao_correta"] = (
        (ultima_rodada["prob_casa_vencer_%"] >= 50) == (ultima_rodada["home_venceu"] == 1)
    )

    resultado_ultima = ultima_rodada[[
        "home_team", "away_team", "prob_casa_vencer_%", "resultado_real", "previsao_correta"
    ]]

    acertos = int(resultado_ultima["previsao_correta"].sum())
    total = len(resultado_ultima)
    print(f"\nÚltima rodada disputada: Temporada {int(ultima_temporada_disputada)}, "
          f"Semana {int(ultima_semana_disputada)}")
    print(resultado_ultima.to_string(index=False))
    print(f"\nAcertos do modelo nessa rodada: {acertos}/{total}")

    ARQUIVO_ULTIMA_RODADA = RAIZ_PROJETO / "resultados_ultima_rodada.csv"
    resultado_ultima.to_csv(ARQUIVO_ULTIMA_RODADA, index=False)
    print(f"Salvo em '{ARQUIVO_ULTIMA_RODADA}'.")

# ============================================================
# HISTÓRICO DE PRECISÃO DO MODELO AO LONGO DO TEMPO
# ============================================================
# Para CADA semana já disputada (com histórico de treino suficiente),
# treinamos o modelo só com dados ANTERIORES a ela e medimos o acerto
# nessa semana especificamente - o mesmo princípio de validação cruzada
# temporal que já usamos para avaliar o modelo, mas guardando o resultado
# semana a semana em vez de só a média da temporada.
print("\nCalculando histórico de precisão do modelo (retroativo, semana a semana)...")

TREINO_MINIMO = 150  # não avaliamos semanas com histórico de treino insuficiente

combinacoes = (
    jogos_completos[jogos_completos["jogo_disputado"]]
    .dropna(subset=FEATURES)[["season", "week"]]
    .drop_duplicates()
    .sort_values(["season", "week"])
)

historico_linhas = []
for _, combo in combinacoes.iterrows():
    season_atual, week_atual = combo["season"], combo["week"]

    treino_hist = jogos_completos[
        jogos_completos["jogo_disputado"]
        & ((jogos_completos["season"] < season_atual)
           | ((jogos_completos["season"] == season_atual) & (jogos_completos["week"] < week_atual)))
    ].dropna(subset=FEATURES + ["home_venceu"])

    if len(treino_hist) < TREINO_MINIMO:
        continue

    teste_hist = jogos_completos[
        (jogos_completos["season"] == season_atual)
        & (jogos_completos["week"] == week_atual)
        & jogos_completos["jogo_disputado"]
    ].dropna(subset=FEATURES)

    if teste_hist.empty:
        continue

    scaler_hist = StandardScaler()
    X_treino_hist = scaler_hist.fit_transform(treino_hist[FEATURES])
    modelo_hist = LogisticRegression()
    modelo_hist.fit(X_treino_hist, treino_hist["home_venceu"].astype(int))

    X_teste_hist = scaler_hist.transform(teste_hist[FEATURES])
    previsoes_hist = modelo_hist.predict(X_teste_hist)
    reais_hist = teste_hist["home_venceu"].astype(int).values

    acertos = int((previsoes_hist == reais_hist).sum())
    total = len(teste_hist)

    historico_linhas.append({
        "season": int(season_atual), "week": int(week_atual),
        "jogos": total, "acertos": acertos, "acuracia": round(acertos / total, 3),
    })

historico_df = pd.DataFrame(historico_linhas)
ARQUIVO_HISTORICO = RAIZ_PROJETO / "historico_precisao_semanal.csv"
historico_df.to_csv(ARQUIVO_HISTORICO, index=False)
print(f"Histórico de precisão salvo em '{ARQUIVO_HISTORICO}' ({len(historico_df)} semanas avaliadas).")

conexao.close()
print("\nPipeline semanal concluído!")