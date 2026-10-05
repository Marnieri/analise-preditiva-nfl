# Análise e Previsão de Resultados da NFL 🏈

Projeto de análise de dados e machine learning construído para aprender e praticar habilidades de ciência de dados de ponta a ponta: coleta, limpeza, exploração, engenharia de features, modelagem preditiva e um dashboard interativo — usando dados históricos e em tempo real da NFL (2019 até a temporada atual).

## Objetivo

Prever resultados de jogos da NFL a partir de estatísticas históricas de times e jogadores, comparar o modelo com o mercado de apostas como benchmark, e acompanhar o desempenho do modelo semana a semana, com um dashboard para explorar times, jogadores e previsões.

## O que este projeto demonstra

- **Coleta de dados via API** (`nflreadpy`, sucessora oficial do projeto nflverse), com tratamento resiliente para dados de temporadas futuras ainda não publicados
- **Limpeza e validação de dados**, incluindo diagnóstico e correção de inconsistências reais entre fontes (siglas de times divergentes, tipos de dados incompatíveis)
- **Engenharia de features para séries temporais**, com cuidado explícito para evitar vazamento de dados (*data leakage*) - toda feature usa apenas informação disponível antes de cada jogo
- **Métricas avançadas de futebol americano**: EPA (Expected Points Added) ofensivo e defensivo, calculado a partir de dados de jogo por jogo
- **Machine learning**: regressão logística com validação cruzada temporal (*walk-forward validation*), padronização de features e comparação honesta com dois benchmarks (taxa de vitória em casa e odds de mercado)
- **Banco de dados relacional** (SQLite) como fonte única de dados para o pipeline e o dashboard
- **Pipeline de atualização semanal automatizado**, que baixa dados novos, recalcula features, retreina o modelo e gera previsões da próxima rodada com um único comando
- **Dashboard interativo** (Streamlit) com 3 páginas: previsões e classificação, estatísticas por time, estatísticas de jogadores por categoria (estilo ESPN)
- **Rastreamento retroativo de precisão do modelo** ao longo do tempo, usando o mesmo princípio de validação temporal

## Estrutura do projeto

```
analise-nfl/
├── scripts/
│   ├── 00_pipeline_semanal.py          # SCRIPT PRINCIPAL - rodar 1x/semana durante a temporada
│   ├── teste_gerar_previsoes_demo.py   # Gera previsões de demonstração p/ testar o dashboard fora de temporada
│   └── 01_a_20_*.py                    # Jornada de aprendizado: cada etapa do projeto isolada
│                                        # (coleta, EDA, merge, banco de dados, features, modelagem)
├── dashboard/
│   ├── Home.py                         # Página inicial: classificação, previsões, histórico de precisão
│   ├── divisoes.py                     # Mapeamento time -> conferência/divisão + cálculo de classificação
│   └── pages/
│       ├── 1_Times.py                  # Estatísticas e evolução por time
│       └── 2_Jogadores.py              # Estatísticas de jogadores por categoria (Passe/Corrida/Recepção/Defesa)
├── nfl_dados.db                        # Gerado pelo pipeline (não versionado)
├── previsoes_proxima_semana.csv        # Gerado pelo pipeline (não versionado)
├── resultados_ultima_rodada.csv        # Gerado pelo pipeline (não versionado)
├── historico_precisao_semanal.csv      # Gerado pelo pipeline (não versionado)
├── requirements.txt
└── README.md
```

## Como rodar

1. Crie um ambiente virtual com Python 3.11 ou 3.12 (bibliotecas de dados podem não ter suporte total a versões mais recentes ainda).
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Rode o pipeline principal (baixa dados, atualiza o banco, treina o modelo, gera previsões):
   ```
   python scripts/00_pipeline_semanal.py
   ```
4. Abra o dashboard:
   ```
   streamlit run dashboard/Home.py
   ```
5. Atualize `ULTIMA_TEMPORADA` no topo do `00_pipeline_semanal.py` uma vez por ano, quando uma nova temporada da NFL começar.

Fora de temporada (sem jogos futuros para prever), rode `scripts/teste_gerar_previsoes_demo.py` para gerar previsões de demonstração e testar o dashboard visualmente.

## O modelo

Regressão logística com 8 features, sem redundância entre elas (validado removendo features de pontos brutos, que carregavam informação já capturada pelo EPA, sem perda de performance):

- Taxa de vitórias na temporada (casa e visitante)
- Dias de descanso desde o último jogo (casa e visitante)
- EPA ofensivo médio na temporada (casa e visitante)
- EPA defensivo médio permitido na temporada (casa e visitante)

**Validação cruzada temporal (2021-2025), a métrica mais confiável do projeto:**

| Modelo/Referência | Acurácia média |
|---|---|
| Baseline (sempre apostar na casa) | 54,8% |
| **Nosso modelo** | **61,1%** |
| Mercado de apostas (odds convertidas em probabilidade) | 66,7% |

O gap para o mercado é esperado: casas de apostas têm acesso a informações que não temos (lesões de última hora, análise de especialistas). Superar o baseline por ~6 pontos percentuais com só 8 features é um resultado sólido para um modelo desse tamanho.

## Principais achados

- **EPA (Expected Points Added) é um preditor mais forte e mais limpo que pontos brutos** - depois de padronizar as features para comparação justa, EPA ofensivo/defensivo dominou os coeficientes do modelo, e remover as features de pontos brutos manteve a mesma acurácia com coeficientes muito mais interpretáveis (sem sinais invertidos por multicolinearidade).
- **A vantagem de jogar em casa está diminuindo** - o baseline "sempre apostar na casa" caiu de ~57% em 2022-2023 para ~53% em 2024-2025, um padrão real e não um artefato dos dados.
- **Jazidas de passe muito altas numa única partida frequentemente coincidem com derrotas**, não vitórias - evidência de causalidade reversa (times perdendo tendem a passar mais, por necessidade).
- **Taxa de vitórias sozinha é um preditor mais "ruidoso"** que eficiência por jogada (EPA) - times podem vencer jogos apertados por sorte, mas EPA reflete qualidade real de forma mais consistente.

## Lições técnicas aprendidas (erros reais encontrados no processo)

Documentar os erros mostra processo de resolução de problemas, não só o resultado final.

1. **Biblioteca de dados descontinuada em produção**: `nfl_data_py` foi arquivada pelo mantenedor em setembro de 2025, sem aviso prévio no código. O projeto foi migrado para `nflreadpy` (sucessora oficial), incluindo lidar com nomes de colunas diferentes entre as duas fontes.
2. **Fontes de dados externas podem simplesmente parar de existir**: a fonte de dados de lesões da nflverse parou de ser atualizada após 2024, sem previsão de retorno - a feature de lesões foi pausada no modelo em vez de manter uma coluna sempre zerada.
3. **Comparação de `NaN` sempre retorna `False`, nunca `NaN`**: ao criar uma feature booleana a partir de uma coluna com valores vazios, isso pode silenciosamente transformar "não sei" em "não".
4. **Merge falha silenciosamente com tipos de dados incompatíveis** (ex: `season` como `int` numa tabela e `float` noutra).
5. **Vazamento de dados (data leakage) em features de série temporal**: toda feature que descreve "como o time está indo" precisa ser deslocada no tempo (`.shift()`) para garantir que só usa informação anterior ao jogo que está sendo previsto.
6. **`working directory` diferente entre ferramentas**: um script rodado pelo PyCharm e um dashboard rodado via `streamlit run` podem resolver caminhos relativos ("nfl_dados.db") de pastas diferentes, mesmo dentro do mesmo projeto. Resolvido ancorando todos os caminhos na localização real de cada arquivo com `Path(__file__).resolve()`.
7. **Cache do Streamlit não detecta mudanças externas ao arquivo de banco de dados**: `@st.cache_data` guarda o resultado em memória e não sabe que o `.db` mudou por fora - resolvido com um botão manual de "atualizar dados" que limpa o cache.
8. **Bug conhecido do pandas em `.replace(0, pd.NA)`**: em certas combinações de versão, essa chamada entra em recursão infinita ao tentar coagir o tipo da coluna - resolvido calculando a divisão normalmente e usando `.where()` para descartar os casos de divisão por zero.
9. **Scripts de pipeline precisam ser idempotentes**: um script que lê e escreve na mesma tabela do banco pode gerar colunas duplicadas (`coluna_x`, `coluna_y`) se rodado mais de uma vez sem remover o resultado da execução anterior primeiro.

## Possíveis melhorias futuras

- Retomar a feature de lesões, ponderada por posição/importância do jogador, se a fonte de dados voltar a funcionar
- Testar modelos não-lineares (Random Forest, Gradient Boosting)
- Incorporar dados de transações e mudanças de elenco
- Adicionar a probabilidade de mercado como feature do próprio modelo (blending modelo + mercado)
- Automatizar a execução semanal com o Agendador de Tarefas do Windows (ou `cron`), em vez de rodar manualmente

## Fontes de dados

- [nflreadpy](https://github.com/nflverse/nflreadpy) (projeto nflverse) - calendário de jogos, estatísticas de time e jogador, odds de mercado.

## Autor

Projeto desenvolvido como exercício de aprendizado prático em análise de dados e machine learning.
