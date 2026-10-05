"""
04_baixar_estatisticas_jogadores.py
--------------------------------------
Baixa estatísticas de jogadores (passe, corrida, recepção) jogo a jogo,
usando a biblioteca nflreadpy.

ATUALIZAÇÃO IMPORTANTE: migrado de "nfl_data_py" (descontinuada em
setembro de 2025) para "nflreadpy" (sucessora oficial e ativamente mantida).
Instale com: pip install "nflreadpy[pandas]"
"""

import pandas as pd
import nflreadpy as nfl

# 1. Mesmas temporadas do script de jogos, para manter tudo consistente.
temporadas = list(range(2019, 2026))

print(f"Baixando estatísticas de jogadores das temporadas: {temporadas}")

# 2. load_player_stats() traz uma linha por jogador, por semana, por temporada.
#    Retorna um DataFrame do Polars - convertemos para pandas com .to_pandas().
jogadores_polars = nfl.load_player_stats(temporadas)
jogadores = jogadores_polars.to_pandas()

print(f"\nTotal de registros baixados: {jogadores.shape[0]} linhas, {jogadores.shape[1]} colunas")

# 3. Como mudamos de biblioteca, vamos CONFERIR os nomes das colunas antes
#    de selecionar as que precisamos - alguns nomes podem ter mudado
#    (por exemplo, "recent_team" na fonte antiga pode aparecer como "team" aqui).
print("\nColunas disponíveis nesta fonte:")
print(list(jogadores.columns))

# 4. Mapeamento defensivo: para cada informação que precisamos, listamos
#    os possíveis nomes que essa coluna pode ter, e usamos o primeiro que
#    encontrarmos de fato na tabela baixada.
candidatos_por_campo = {
    "player_display_name": ["player_display_name", "display_name", "player_name"],
    "position": ["position"],
    "recent_team": ["recent_team", "team"],
    "season": ["season"],
    "week": ["week"],
    "completions": ["completions"],
    "attempts": ["attempts"],
    "passing_yards": ["passing_yards"],
    "passing_tds": ["passing_tds"],
    "interceptions": ["interceptions", "passing_interceptions"],
    "carries": ["carries"],
    "rushing_yards": ["rushing_yards"],
    "rushing_tds": ["rushing_tds"],
    "receptions": ["receptions"],
    "targets": ["targets"],
    "receiving_yards": ["receiving_yards"],
    "receiving_tds": ["receiving_tds"],
    "fantasy_points": ["fantasy_points"],
}

colunas_finais = {}
campos_nao_encontrados = []
for nome_padrao, candidatos in candidatos_por_campo.items():
    encontrado = next((c for c in candidatos if c in jogadores.columns), None)
    if encontrado:
        colunas_finais[nome_padrao] = encontrado
    else:
        campos_nao_encontrados.append(nome_padrao)

if campos_nao_encontrados:
    print(f"\nATENÇÃO: não encontramos correspondência para: {campos_nao_encontrados}")
    print("Confira a lista de colunas impressa acima para localizar o nome certo,")
    print("e me avise para ajustarmos o mapeamento.")

# 5. Selecionamos as colunas encontradas e renomeamos para os nomes padrão
#    que o resto do projeto já espera (assim os scripts seguintes não precisam mudar).
jogadores_simplificado = jogadores[list(colunas_finais.values())].rename(
    columns={v: k for k, v in colunas_finais.items()}
)

# 6. Salvamos em CSV, assim como fizemos com os dados de jogos.
nome_arquivo = "estatisticas_jogadores_2019_2025.csv"
jogadores_simplificado.to_csv(nome_arquivo, index=False)

print(f"\nPronto! Dados salvos em '{nome_arquivo}'.")

# 7. Prévia rápida para conferir que os dados fazem sentido.
if "passing_yards" in jogadores_simplificado.columns:
    print("\nTop 5 performances de passe em uma única semana:")
    top_passe = jogadores_simplificado.sort_values("passing_yards", ascending=False).head(5)
    colunas_mostrar = [c for c in ["player_display_name", "season", "week", "passing_yards", "passing_tds"] if c in top_passe.columns]
    print(top_passe[colunas_mostrar])