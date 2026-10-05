"""
dashboard/pages/1_Times.py
------------------------------
Página do dashboard para navegar entre times: retrospecto, EPA e evolução
ao longo da temporada, em formato compacto (mesmo estilo das outras páginas).
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from divisoes import calcular_classificacao

st.set_page_config(page_title="Times - NFL Analytics", page_icon="🏟️", layout="wide")

RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
DB_PATH = RAIZ_PROJETO / "nfl_dados.db"


@st.cache_data
def carregar_dados():
    conexao = sqlite3.connect(DB_PATH)
    jogos_por_time = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)
    conexao.close()
    return jogos_por_time


jogos_por_time = carregar_dados()

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# --- Filtros compactos no topo, mesmo padrão da página de Jogadores ---
col_time, col_temporada = st.columns(2)
with col_time:
    times = sorted(jogos_por_time["team"].unique())
    time_selecionado = st.selectbox("Time", times)
with col_temporada:
    temporadas = sorted(jogos_por_time["season"].unique(), reverse=True)
    temporada_selecionada = st.selectbox("Temporada", temporadas)

dados_time = jogos_por_time[
    (jogos_por_time["team"] == time_selecionado) & (jogos_por_time["season"] == temporada_selecionada)
].sort_values("week")

st.title(f"🏈 {time_selecionado} — {temporada_selecionada}")

jogos_disputados = dados_time.dropna(subset=["pontos_time", "pontos_adversario"])

if jogos_disputados.empty:
    st.info("Nenhum jogo disputado ainda nesta temporada para este time.")
else:
    # --- Card de resumo, reaproveitando a mesma função de classificação ---
    dados_temporada_completa = jogos_por_time[jogos_por_time["season"] == temporada_selecionada]
    classificacao = calcular_classificacao(dados_temporada_completa)
    linha_time = classificacao[classificacao["Time"] == time_selecionado]

    with st.container(border=True):
        if not linha_time.empty:
            info = linha_time.iloc[0]
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Retrospecto", f"{info['V']}-{info['D']}")
            col2.metric("Sequência", info["STRK"])
            col3.metric("Pontos marcados (média)", f"{jogos_disputados['pontos_time'].mean():.1f}")
            col4.metric("Pontos sofridos (média)", f"{jogos_disputados['pontos_adversario'].mean():.1f}")
            col5.metric("Saldo de pontos", f"{info['DIF']:+d}")
        else:
            col1, col2 = st.columns(2)
            col1.metric("Pontos marcados (média)", f"{jogos_disputados['pontos_time'].mean():.1f}")
            col2.metric("Pontos sofridos (média)", f"{jogos_disputados['pontos_adversario'].mean():.1f}")

    # --- Abas para os gráficos e a tabela, em vez de empilhar tudo ---
    aba_pontos, aba_epa, aba_jogos = st.tabs(["📈 Pontos", "📊 EPA", "📋 Jogo a jogo"])

    with aba_pontos:
        fig_pontos = go.Figure()
        fig_pontos.add_trace(go.Scatter(
            x=jogos_disputados["week"], y=jogos_disputados["pontos_time"],
            name="Pontos marcados", mode="lines+markers",
        ))
        fig_pontos.add_trace(go.Scatter(
            x=jogos_disputados["week"], y=jogos_disputados["pontos_adversario"],
            name="Pontos sofridos", mode="lines+markers",
        ))
        fig_pontos.update_layout(
            xaxis_title="Semana", yaxis_title="Pontos", hovermode="x unified",
            margin=dict(t=10, b=10), height=350,
        )
        st.plotly_chart(fig_pontos, use_container_width=True)

    with aba_epa:
        if "epa_ofensivo" in dados_time.columns:
            dados_epa = dados_time.dropna(subset=["epa_ofensivo"])
            fig_epa = go.Figure()
            fig_epa.add_trace(go.Scatter(
                x=dados_epa["week"], y=dados_epa["epa_ofensivo"],
                name="EPA ofensivo", mode="lines+markers",
            ))
            fig_epa.add_trace(go.Scatter(
                x=dados_epa["week"], y=dados_epa["epa_ofensivo_permitido"],
                name="EPA permitido (defesa)", mode="lines+markers",
            ))
            fig_epa.add_hline(y=0, line_dash="dot", line_color="gray")
            fig_epa.update_layout(
                xaxis_title="Semana", yaxis_title="EPA", hovermode="x unified",
                margin=dict(t=10, b=10), height=350,
            )
            st.plotly_chart(fig_epa, use_container_width=True)
            st.caption(
                "EPA positivo = jogadas que aumentaram a chance de pontuar. "
                "Para o 'EPA permitido', valores mais altos indicam defesa mais fraca."
            )
        else:
            st.info("Dados de EPA não disponíveis. Rode o pipeline atualizado.")

    with aba_jogos:
        colunas_tabela = ["week", "opponent", "local", "pontos_time", "pontos_adversario", "dias_descanso"]
        colunas_existentes = [c for c in colunas_tabela if c in dados_time.columns]
        st.dataframe(
            dados_time[colunas_existentes].rename(columns={
                "week": "Semana", "opponent": "Adversário", "local": "Local",
                "pontos_time": "Pontos time", "pontos_adversario": "Pontos adversário",
                "dias_descanso": "Descanso (dias)",
            }),
            use_container_width=True, hide_index=True,
        )