"""
07_corrigir_merge_nfl.py
----------------------------
Confirma a hipótese da inconsistência OAK/LV (Raiders) e corrige o merge
padronizando as siglas de times antes de cruzar as tabelas.
"""

import pandas as pd

jogos = pd.read_csv("jogos_nfl_2019_2025.csv")
jogadores = pd.read_csv("estatisticas_jogadores_2019_2025.csv")

# 1. Confirmando a hipótese: vamos ver em quais temporadas o "OAK" aparece
#    nos jogos, e em quais temporadas o "LV" aparece nos jogadores.
print("Temporadas em que 'OAK' aparece na tabela de jogos:")
print(sorted(jogos[(jogos["home_team"] == "OAK") | (jogos["away_team"] == "OAK")]["season"].unique()))

print("\nTemporadas em que 'LV' aparece na tabela de jogadores:")
print(sorted(jogadores[jogadores["recent_team"] == "LV"]["season"].unique()))

# Se a primeira lista mostrar só 2019 (ou anos antes) e a segunda mostrar
# 2019 também, confirma exatamente o que suspeitamos.

# ---------------------------------------------------------------------------
# 2. A CORREÇÃO: criamos um "dicionário de mapeamento" de siglas antigas
#    para siglas atuais, e aplicamos na tabela de JOGOS (para ficar
#    consistente com o padrão já usado na tabela de jogadores).
# ---------------------------------------------------------------------------
mapa_siglas = {
    "OAK": "LV",  # Raiders: Oakland -> Las Vegas
    # Se aparecerem outras inconsistências parecidas no futuro
    # (outros times que mudaram de sigla/cidade), adicione aqui também.
}

# .replace() troca valores em uma coluna baseado no dicionário fornecido.
jogos["home_team"] = jogos["home_team"].replace(mapa_siglas)
jogos["away_team"] = jogos["away_team"].replace(mapa_siglas)

# 3. Repetimos a reformatação (igual ao script anterior), agora com as
#    siglas já corrigidas.
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

colunas_finais = ["season", "week", "team", "opponent", "pontos_time", "pontos_adversario", "local"]
jogos_por_time = pd.concat([casa[colunas_finais], fora[colunas_finais]], ignore_index=True)

# 4. Repetimos o merge.
dados_completos = jogadores.merge(
    jogos_por_time,
    left_on=["season", "week", "recent_team"],
    right_on=["season", "week", "team"],
    how="left",
)

sem_correspondencia = dados_completos["pontos_time"].isnull().sum()
print(f"\nLinhas sem correspondência ANTES da correção: 169")
print(f"Linhas sem correspondência DEPOIS da correção: {sem_correspondencia}")

# 5. Se deu certo (0 linhas sem correspondência), salvamos a versão corrigida,
#    substituindo o CSV anterior.
if sem_correspondencia == 0:
    dados_completos["vitoria"] = dados_completos["pontos_time"] > dados_completos["pontos_adversario"]
    dados_completos.to_csv("dados_jogadores_com_contexto_jogo.csv", index=False)
    print("Merge corrigido com sucesso! Arquivo atualizado.")
else:
    print("Ainda restaram linhas sem correspondência — vamos investigar mais.")
    # Mostra algumas linhas problemáticas para próxima investigação.
    print(dados_completos[dados_completos["pontos_time"].isnull()][
        ["player_display_name", "season", "week", "recent_team"]
    ].head(10))