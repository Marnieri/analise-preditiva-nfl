"""
dashboard/divisoes.py
--------------------------
Mapeamento de cada time da NFL para sua conferência e divisão (isso não
vem pronto em nenhuma das fontes de dados que usamos, então mantemos
uma lista fixa aqui - só muda se a NFL reorganizar divisões, o que é raro).

Também contém a função que calcula a tabela de classificação (retrospecto,
saldo de pontos, sequência) a partir da tabela 'jogos_com_forma_recente'.
"""

import pandas as pd

TIME_PARA_DIVISAO = {
    # AFC Leste
    "BUF": ("AFC", "Leste"), "MIA": ("AFC", "Leste"), "NE": ("AFC", "Leste"), "NYJ": ("AFC", "Leste"),
    # AFC Norte
    "BAL": ("AFC", "Norte"), "CIN": ("AFC", "Norte"), "CLE": ("AFC", "Norte"), "PIT": ("AFC", "Norte"),
    # AFC Sul
    "HOU": ("AFC", "Sul"), "IND": ("AFC", "Sul"), "JAX": ("AFC", "Sul"), "TEN": ("AFC", "Sul"),
    # AFC Oeste
    "DEN": ("AFC", "Oeste"), "KC": ("AFC", "Oeste"), "LV": ("AFC", "Oeste"), "LAC": ("AFC", "Oeste"),
    # NFC Leste
    "DAL": ("NFC", "Leste"), "NYG": ("NFC", "Leste"), "PHI": ("NFC", "Leste"), "WAS": ("NFC", "Leste"),
    # NFC Norte
    "CHI": ("NFC", "Norte"), "DET": ("NFC", "Norte"), "GB": ("NFC", "Norte"), "MIN": ("NFC", "Norte"),
    # NFC Sul
    "ATL": ("NFC", "Sul"), "CAR": ("NFC", "Sul"), "NO": ("NFC", "Sul"), "TB": ("NFC", "Sul"),
    # NFC Oeste
    "ARI": ("NFC", "Oeste"), "LA": ("NFC", "Oeste"), "SF": ("NFC", "Oeste"), "SEA": ("NFC", "Oeste"),
}


def calcular_classificacao(jogos_temporada):
    """Recebe as linhas (1 por time por jogo) de UMA temporada já filtrada,
    e devolve uma tabela de classificação por time: vitórias, derrotas,
    retrospecto em casa/fora/divisão, saldo de pontos e sequência atual."""
    linhas = []

    for time, grupo in jogos_temporada.groupby("team"):
        grupo = grupo.sort_values("week")
        disputados = grupo.dropna(subset=["pontos_time", "pontos_adversario"])
        if disputados.empty:
            continue

        vitorias = int(pd.to_numeric(disputados["vitoria"], errors="coerce").sum())
        total_jogos = len(disputados)
        derrotas = total_jogos - vitorias
        pct_vitorias = vitorias / total_jogos if total_jogos else 0

        pf = disputados["pontos_time"].sum()
        pc = disputados["pontos_adversario"].sum()

        def retrospecto(subgrupo):
            v = int(pd.to_numeric(subgrupo["vitoria"], errors="coerce").sum())
            d = len(subgrupo) - v
            return f"{v}-{d}"

        casa = disputados[disputados["local"] == "casa"]
        fora = disputados[disputados["local"] == "fora"]
        retrospecto_casa = retrospecto(casa) if not casa.empty else "0-0"
        retrospecto_fora = retrospecto(fora) if not fora.empty else "0-0"

        if "div_game" in disputados.columns:
            jogos_divisao = disputados[disputados["div_game"] == 1]
            retrospecto_divisao = retrospecto(jogos_divisao) if not jogos_divisao.empty else "0-0"
        else:
            retrospecto_divisao = "-"

        # Sequência atual: percorre os resultados do mais recente para o
        # mais antigo, contando quantas vitórias (ou derrotas) seguidas há.
        resultados_recentes = list(reversed(pd.to_numeric(disputados["vitoria"], errors="coerce").tolist()))
        tipo_sequencia, tamanho_sequencia = None, 0
        for resultado in resultados_recentes:
            if tipo_sequencia is None:
                tipo_sequencia = resultado
                tamanho_sequencia = 1
            elif resultado == tipo_sequencia:
                tamanho_sequencia += 1
            else:
                break
        sequencia = f"{'V' if tipo_sequencia == 1 else 'D'}{tamanho_sequencia}" if tipo_sequencia is not None else "-"

        conferencia, divisao = TIME_PARA_DIVISAO.get(time, ("?", "?"))

        linhas.append({
            "Conferência": conferencia, "Divisão": divisao, "Time": time,
            "V": vitorias, "D": derrotas, "% VIT": round(pct_vitorias, 3),
            "CASA": retrospecto_casa, "VISITANTE": retrospecto_fora, "DIV": retrospecto_divisao,
            "PF": int(pf), "PC": int(pc), "DIF": int(pf - pc), "STRK": sequencia,
        })

    return pd.DataFrame(linhas)