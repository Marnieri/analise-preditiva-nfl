"""
dashboard/pages/2_Jogadores.py
-----------------------------------
Estatísticas de jogadores organizadas por categoria (Passe, Corrida,
Recepção, Defesa), no estilo da página de estatísticas de time da ESPN -
cada categoria com sua própria tabela e colunas relevantes.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Jogadores - NFL Analytics", page_icon="👤", layout="wide")

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
DB_PATH = RAIZ_PROJETO / "nfl_dados.db"


@st.cache_data
def carregar_jogadores():
    conexao = sqlite3.connect(DB_PATH)
    try:
        jogadores = pd.read_sql("SELECT * FROM jogadores", conexao)
    except Exception:
        jogadores = pd.DataFrame()
    conexao.close()
    return jogadores


jogadores = carregar_jogadores()

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

if jogadores.empty:
    st.warning(
        "Tabela de jogadores não encontrada no banco de dados. Rode o script "
        "'00_pipeline_semanal.py' primeiro."
    )
    st.stop()

st.title("👤 Estatísticas de Jogadores")

# --- Filtros compactos no topo (time + temporada), estilo página de time da ESPN ---
col_time, col_temporada = st.columns(2)
with col_time:
    times = sorted(jogadores["recent_team"].dropna().unique())
    time_selecionado = st.selectbox("Time", ["Todos os times"] + times)
with col_temporada:
    temporadas = sorted(jogadores["season"].dropna().unique(), reverse=True)
    temporada_selecionada = st.selectbox("Temporada", temporadas)

dados = jogadores[jogadores["season"] == temporada_selecionada]
if time_selecionado != "Todos os times":
    dados = dados[dados["recent_team"] == time_selecionado]


def agregar_temporada(df, colunas_soma):
    """Soma as estatísticas de cada jogador ao longo da temporada (várias
    linhas semanais viram 1 linha por jogador), e conta quantos jogos ele
    jogou (JJ) - métrica que a ESPN sempre mostra junto."""
    colunas_existentes = [c for c in colunas_soma if c in df.columns]
    agrupado = df.groupby(["player_display_name", "recent_team"], as_index=False).agg(
        JJ=("week", "nunique"),
        **{c: (c, "sum") for c in colunas_existentes},
    )
    return agrupado


# ============================================================
# ABAS POR CATEGORIA (igual ao layout da ESPN)
# ============================================================
aba_passe, aba_corrida, aba_recepcao, aba_defesa = st.tabs(["🏈 Passe", "🏃 Corrida", "🙌 Recepção", "🛡️ Defesa"])

with aba_passe:
    dados_qb = dados[dados["position"] == "QB"] if "position" in dados.columns else dados
    tabela = agregar_temporada(dados_qb, ["completions", "attempts", "passing_yards", "passing_tds", "interceptions"])
    if not tabela.empty:
        tabela["CMP%"] = (tabela["completions"] / tabela["attempts"] * 100).round(1)
        tabela["CMP%"] = tabela["CMP%"].where(tabela["attempts"] > 0)
        tabela["JDS/JOGO"] = (tabela["passing_yards"] / tabela["JJ"]).round(1)
        tabela = tabela.sort_values("passing_yards", ascending=False)
        tabela = tabela.rename(columns={
            "player_display_name": "Jogador", "recent_team": "Time",
            "completions": "CMP", "attempts": "ATT", "passing_yards": "JDS",
            "passing_tds": "TD", "interceptions": "INT",
        })
        st.dataframe(
            tabela[["Jogador", "Time", "JJ", "CMP", "ATT", "CMP%", "JDS", "JDS/JOGO", "TD", "INT"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Nenhum dado de passe disponível para este filtro.")

with aba_corrida:
    tabela = agregar_temporada(dados, ["carries", "rushing_yards", "rushing_tds"])
    tabela = tabela[tabela["carries"] > 0] if "carries" in tabela.columns else tabela
    if not tabela.empty:
        tabela["MÉD"] = (tabela["rushing_yards"] / tabela["carries"]).round(1)
        tabela["MÉD"] = tabela["MÉD"].where(tabela["carries"] > 0)
        tabela["JDS/JOGO"] = (tabela["rushing_yards"] / tabela["JJ"]).round(1)
        tabela = tabela.sort_values("rushing_yards", ascending=False)
        tabela = tabela.rename(columns={
            "player_display_name": "Jogador", "recent_team": "Time",
            "carries": "CAR", "rushing_yards": "JDS", "rushing_tds": "TD",
        })
        st.dataframe(
            tabela[["Jogador", "Time", "JJ", "CAR", "JDS", "MÉD", "JDS/JOGO", "TD"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Nenhum dado de corrida disponível para este filtro.")

with aba_recepcao:
    tabela = agregar_temporada(dados, ["receptions", "targets", "receiving_yards", "receiving_tds"])
    tabela = tabela[tabela["targets"] > 0] if "targets" in tabela.columns else tabela
    if not tabela.empty:
        tabela["MÉD"] = (tabela["receiving_yards"] / tabela["receptions"]).round(1)
        tabela["MÉD"] = tabela["MÉD"].where(tabela["receptions"] > 0)
        tabela["JDS/JOGO"] = (tabela["receiving_yards"] / tabela["JJ"]).round(1)
        tabela = tabela.sort_values("receiving_yards", ascending=False)
        tabela = tabela.rename(columns={
            "player_display_name": "Jogador", "recent_team": "Time",
            "receptions": "REC", "targets": "ALVO", "receiving_yards": "JDS", "receiving_tds": "TD",
        })
        st.dataframe(
            tabela[["Jogador", "Time", "JJ", "REC", "ALVO", "JDS", "MÉD", "JDS/JOGO", "TD"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Nenhum dado de recepção disponível para este filtro.")

with aba_defesa:
    colunas_def = ["def_tackles_solo", "def_tackles_with_assist", "def_tackles_for_loss",
                   "def_sacks", "def_qb_hits", "def_interceptions", "def_pass_defended",
                   "def_fumbles_forced", "def_tds"]
    colunas_def_existentes = [c for c in colunas_def if c in dados.columns]
    if colunas_def_existentes:
        tabela = agregar_temporada(dados, colunas_def_existentes)
        tabela = tabela[tabela["def_tackles_solo"] + tabela.get("def_tackles_with_assist", 0) > 0]
        if not tabela.empty:
            tabela["TCKL"] = tabela["def_tackles_solo"] + tabela.get("def_tackles_with_assist", 0)
            tabela = tabela.sort_values("TCKL", ascending=False)
            tabela = tabela.rename(columns={
                "player_display_name": "Jogador", "recent_team": "Time",
                "def_tackles_for_loss": "TFL", "def_sacks": "SACK", "def_qb_hits": "QBH",
                "def_interceptions": "INT", "def_pass_defended": "PD",
                "def_fumbles_forced": "FF", "def_tds": "TD",
            })
            colunas_finais = ["Jogador", "Time", "JJ", "TCKL", "TFL", "SACK", "QBH", "INT", "PD", "FF", "TD"]
            colunas_finais = [c for c in colunas_finais if c in tabela.columns]
            st.dataframe(tabela[colunas_finais], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado defensivo disponível para este filtro.")
    else:
        st.info(
            "Estatísticas defensivas ainda não coletadas. Rode o "
            "'00_pipeline_semanal.py' atualizado para baixá-las."
        )

st.divider()

# --- Busca de jogador específico (evolução semana a semana) ---
st.subheader("🔍 Ver evolução de um jogador específico")
nomes = sorted(dados["player_display_name"].dropna().unique())
jogador_busca = st.selectbox("Jogador", ["-"] + nomes)

if jogador_busca != "-":
    dados_jogador = dados[dados["player_display_name"] == jogador_busca].sort_values("week")
    colunas_possiveis = [
        "week", "recent_team", "passing_yards", "passing_tds", "rushing_yards",
        "rushing_tds", "receptions", "receiving_yards", "receiving_tds", "fantasy_points",
    ]
    colunas_mostrar = [c for c in colunas_possiveis if c in dados_jogador.columns]
    st.dataframe(
        dados_jogador[colunas_mostrar].rename(columns={"week": "Semana", "recent_team": "Time"}),
        use_container_width=True, hide_index=True,
    )