"""
dashboard/Home.py
--------------------
Página inicial do dashboard: classificação por divisão + previsões da
próxima rodada em formato compacto, usando nossas próprias métricas
(EPA, forma recente) em vez de destaques de jogador.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from divisoes import calcular_classificacao

st.set_page_config(page_title="NFL Analytics", page_icon="🏈", layout="wide")

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
DB_PATH = RAIZ_PROJETO / "nfl_dados.db"
PREVISOES_PATH = RAIZ_PROJETO / "previsoes_proxima_semana.csv"

st.title("🏈 NFL Analytics Dashboard")


@st.cache_data
def carregar_jogos_por_time():
    conexao = sqlite3.connect(DB_PATH)
    dados = pd.read_sql("SELECT * FROM jogos_com_forma_recente", conexao)
    conexao.close()
    return dados


jogos_por_time = carregar_jogos_por_time()

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# CLASSIFICAÇÃO POR DIVISÃO
# ============================================================
st.header("Classificação")

temporadas_disponiveis = sorted(jogos_por_time["season"].dropna().unique(), reverse=True)
temporada_classificacao = st.selectbox("Temporada", temporadas_disponiveis, key="temporada_classificacao")

dados_temporada = jogos_por_time[jogos_por_time["season"] == temporada_classificacao]
classificacao = calcular_classificacao(dados_temporada)

if classificacao.empty:
    st.info("Nenhum jogo disputado ainda nesta temporada.")
else:
    aba_afc, aba_nfc = st.tabs(["Conferência Americana (AFC)", "Conferência Nacional (NFC)"])

    for aba, conferencia in [(aba_afc, "AFC"), (aba_nfc, "NFC")]:
        with aba:
            dados_conf = classificacao[classificacao["Conferência"] == conferencia]
            for divisao in ["Leste", "Norte", "Sul", "Oeste"]:
                dados_div = dados_conf[dados_conf["Divisão"] == divisao].sort_values(
                    "% VIT", ascending=False
                )
                if dados_div.empty:
                    continue
                st.subheader(f"{conferencia} {divisao}")
                colunas_exibir = ["Time", "V", "D", "% VIT", "CASA", "VISITANTE", "DIV", "PF", "PC", "DIF", "STRK"]
                st.dataframe(dados_div[colunas_exibir], use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# DESEMPENHO DO MODELO NA ÚLTIMA RODADA
# ============================================================
ARQUIVO_ULTIMA_RODADA = RAIZ_PROJETO / "resultados_ultima_rodada.csv"

if ARQUIVO_ULTIMA_RODADA.exists():
    resultados_ultima = pd.read_csv(ARQUIVO_ULTIMA_RODADA)
    if not resultados_ultima.empty:
        st.header("Desempenho do modelo na última rodada")
        acertos = int(resultados_ultima["previsao_correta"].sum())
        total = len(resultados_ultima)
        st.metric("Acertos", f"{acertos}/{total}")
        st.dataframe(
            resultados_ultima.rename(columns={
                "home_team": "Casa", "away_team": "Visitante",
                "prob_casa_vencer_%": "Prob. casa (%)",
                "resultado_real": "Resultado real", "previsao_correta": "Acertou?",
            }),
            use_container_width=True, hide_index=True,
        )
        st.divider()

# ============================================================
# HISTÓRICO DE PRECISÃO DO MODELO AO LONGO DO TEMPO
# ============================================================
ARQUIVO_HISTORICO = RAIZ_PROJETO / "historico_precisao_semanal.csv"

if ARQUIVO_HISTORICO.exists():
    historico = pd.read_csv(ARQUIVO_HISTORICO)
    if not historico.empty:
        st.header("Histórico de Precisão do Modelo")

        historico = historico.sort_values(["season", "week"]).reset_index(drop=True)
        historico["rotulo"] = historico["season"].astype(str) + "-S" + historico["week"].astype(str)

        # Acurácia acumulada: mais estável que a semanal isolada (poucos
        # jogos por semana tornam a taxa semanal bem ruidosa).
        historico["acertos_acumulados"] = historico["acertos"].cumsum()
        historico["jogos_acumulados"] = historico["jogos"].cumsum()
        historico["acuracia_acumulada"] = historico["acertos_acumulados"] / historico["jogos_acumulados"]

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Semanas avaliadas", len(historico))
        col_b.metric("Jogos avaliados", int(historico["jogos"].sum()))
        col_c.metric("Precisão acumulada geral", f"{historico['acuracia_acumulada'].iloc[-1]:.1%}")

        import plotly.graph_objects as go

        fig_historico = go.Figure()
        fig_historico.add_trace(go.Bar(
            x=historico["rotulo"], y=historico["acuracia"] * 100,
            name="Precisão da semana", marker_color="lightgray",
        ))
        fig_historico.add_trace(go.Scatter(
            x=historico["rotulo"], y=historico["acuracia_acumulada"] * 100,
            name="Precisão acumulada", mode="lines", line=dict(color="royalblue", width=3),
        ))
        fig_historico.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="50% (acaso)")
        fig_historico.update_layout(
            xaxis_title="Temporada-Semana", yaxis_title="Precisão (%)",
            hovermode="x unified", margin=dict(t=10, b=10), height=380,
        )
        st.plotly_chart(fig_historico, use_container_width=True)
        st.caption(
            "Barras cinzas = acerto naquela semana específica (poucos jogos, então varia bastante). "
            "Linha azul = acerto acumulado desde o início - visão mais confiável da tendência real."
        )

st.divider()

# ============================================================
# PREVISÕES DA PRÓXIMA RODADA
# ============================================================
st.header("Previsões da Próxima Rodada")

if not PREVISOES_PATH.exists():
    st.warning(
        "Arquivo de previsões não encontrado. Rode o script "
        "'00_pipeline_semanal.py' primeiro para gerar as previsões."
    )
else:
    previsoes = pd.read_csv(PREVISOES_PATH)

    if previsoes.empty:
        st.info(
            "Nenhuma previsão disponível ainda para a próxima rodada "
            "(normal na semana 1 de uma temporada nova)."
        )
    else:
        def buscar_forma(season, week, time):
            """Busca as features de forma do time ENTRANDO naquele jogo
            (já calculadas com o cuidado de nunca usar dados do próprio
            jogo - são exatamente os números que a previsão usou)."""
            linha = jogos_por_time[
                (jogos_por_time["season"] == season)
                & (jogos_por_time["week"] == week)
                & (jogos_por_time["team"] == time)
            ]
            if linha.empty:
                return None
            return linha.iloc[0]

        for _, jogo in previsoes.iterrows():
            forma_casa = buscar_forma(jogo["season"], jogo["week"], jogo["home_team"])
            forma_fora = buscar_forma(jogo["season"], jogo["week"], jogo["away_team"])

            with st.container(border=True):
                col_fora, col_meio, col_casa = st.columns([3, 2, 3])

                with col_fora:
                    st.markdown(f"#### {jogo['away_team']}")
                    st.caption("Visitante")
                    if forma_fora is not None and pd.notna(forma_fora.get("epa_ofensivo_temporada")):
                        st.caption(
                            f"EPA ofensivo: {forma_fora['epa_ofensivo_temporada']:+.2f}  \n"
                            f"EPA permitido: {forma_fora['epa_defensivo_temporada']:+.2f}  \n"
                            f"Taxa de vitórias: {forma_fora['taxa_vitorias_temporada']:.0%}"
                        )

                with col_meio:
                    prob = jogo["prob_casa_vencer_%"]
                    st.metric("Prob. casa vencer", f"{prob:.0f}%")
                    if pd.notna(jogo.get("spread_line")):
                        st.caption(f"Spread (casa): {jogo['spread_line']:+.1f}")

                with col_casa:
                    st.markdown(f"#### {jogo['home_team']}")
                    st.caption("Casa")
                    if forma_casa is not None and pd.notna(forma_casa.get("epa_ofensivo_temporada")):
                        st.caption(
                            f"EPA ofensivo: {forma_casa['epa_ofensivo_temporada']:+.2f}  \n"
                            f"EPA permitido: {forma_casa['epa_defensivo_temporada']:+.2f}  \n"
                            f"Taxa de vitórias: {forma_casa['taxa_vitorias_temporada']:.0%}"
                        )

        with st.expander("Ver tabela completa (com odds de mercado)"):
            st.dataframe(previsoes, use_container_width=True, hide_index=True)

st.caption("Dados via nflverse / nflreadpy. Rode o pipeline semanal para atualizar.")