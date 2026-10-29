# Marreta ou Lâmina? O que ocorreu nos testes

Na sua mesa, a escolha dos efeitos é feita antes de cada uso de Fast Strikes. Os experimentos não respondem qual efeito escolher em toda situação, mas mostram o que aconteceu quando duas políticas simples **mantiveram a mesma escolha ao longo do combate**.

Esta leitura dos registros existentes é **exploratória, feita após a execução**, e não uma comparação confirmatória nova. Cada linha tem 10.000 combates. As contagens incluem vitórias e derrotas.

| Cenário sintético | Escolha de efeitos em Fast | Victor aplicou Stunned ao menos uma vez | Victor executou ao menos uma ação extra da Lâmina | Duração mediana |
|---|---|---:|---:|---:|
| Espelho com Lâmina | Marreta | 7.836 | 0 | 4 rodadas |
| Espelho com Lâmina | Lâmina | 897 | 7.432 | 3 rodadas |
| Físico Rank 4, Sturdy 2 | Marreta | 9.420 | 0 | 5 rodadas |
| Físico Rank 4, Sturdy 2 | Lâmina | 1.292 | 8.397 | 3 rodadas |

As contagens de Stunned incluem **todos os ataques de Victor no combate**, inclusive Riposte com Marreta; por isso podem ocorrer mesmo quando os efeitos escolhidos em Fast são os da Lâmina. A contagem de ações extras registra ações efetivamente executadas, não apenas fantásticos potencialmente capazes de concedê-las. A mediana descreve a duração de todos os combates; terminar mais cedo também pode significar perder mais cedo. Não se deve concluir que uma escolha causa vitórias mais rápidas apenas com essa coluna.

No espelho, a comparação pré-registrada da [reserva](CURRENT_DUEL_HOLDOUT_REPORT.md) favoreceu o efeito da Marreta em taxa de vitória: 56,17%, contra 51,91% para Lâmina. Contra o Rank 4, a comparação entre as duas foi inconclusiva pelo critério usado. Esses resultados não mostram que o Stunned causou a diferença de vitória, nem comparam uma política que alterna a escolha conforme a situação.

**Para a mesa:** Marreta é uma opção quando impedir ações do alvo com Stunned for relevante. Lâmina oferece Bleeding e a possibilidade de uma ação extra no próprio turno quando seus efeitos estiverem selecionados. Considere a resistência do inimigo, a chance de ele remover Bleeding e a situação do combate; o estudo não permite atribuir probabilidades gerais a essas alternativas.

O espelho é um adversário sintético com Lâmina e Escudo, e o Rank 4 é um perfil físico sintético. As políticas testadas aproximam-se, usam Escudo reativo e Riposte com Marreta, mas não usam cura voluntária nem Ram. Focus, Karma, grupos, terreno geral, ficha oficial completa e penalidades numéricas de membro ficaram fora da bateria. Os logs completos não foram guardados para todos os inícios; as sementes e métricas individuais foram preservadas.

**Reprodução:** nos quatro arquivos `results/current_duel_holdout_v1_{mirror_blade,rank4_sturdy2}_{hammer_fast_hammer,hammer_fast_blade}.json`, localize `stuns_applied`, `blade_bonus_actions` e `rounds` em `extended_fields`. Conte valores positivos nas amostras `extended_samples_all_starts` e calcule a mediana das rodadas. O [relatório da reserva](CURRENT_DUEL_HOLDOUT_REPORT.md) e seu arquivo de análise registram os resultados, hashes e fontes congeladas no commit de execução `4c9a5df`.
