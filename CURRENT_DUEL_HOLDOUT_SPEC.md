# Reserva de cenários dos duelos físicos atuais

Este plano é registrado depois de observar e congelar a confirmação e antes
de executar ou observar qualquer célula da reserva. Os três tipos de cenário
foram previstos antes da exploração em `CURRENT_DUEL_STUDY_SPEC.md`; os detalhes
operacionais abaixo são fixados agora. As finalistas e os dois controles não
serão alterados com base nesta reserva. Isso não transforma escolhas feitas após
a confirmação em hipóteses decididas antes da exploração.

## Pergunta e cenários

Como se comportam as duas finalistas e os controles `bare` e `hammer` em três
variações sintéticas ainda não utilizadas para selecionar as políticas?
Usar a mesma ficha e as mesmas políticas de Victor da confirmação.

* `mirror_blade`: cópia sintética da ficha de Victor, distância 4, sem mapa
  limitado. Ataca com Lâmina + Marreta em Fast, escolhe efeito da Lâmina,
  Riposte com Lâmina, Escudo reativo e no fim do turno quando disponível.
* `rank4_sturdy2`: a ficha física sintética anterior, com Sturdy 2 em vez de 1,
  ataque comum desarmado e sem Riposte, distância 1. A alteração é uma hipótese
  sintética, não uma ficha oficial nem progressão de Victor.
* `gunner_open`: o mesmo atirador sintético de ataque não classificado como
  munição, distância 8, sem limite de mapa. Usa `SplitFastPolicy` com recuo,
  movimento após o ataque e tratamento de Bleeding; Run 6. Não representa um
  poder oficial de energia, Focus ou fogo. O modelo de distância em campo aberto
  é unidimensional, não um mapa completo.

## Amostragem e análise

São 10.000 inícios por célula, 12 células e 120.000 no total, limite de 30
rodadas e master seed `827104293`. Antes da execução, derivar todas as sementes
e verificar ausência de repetição ou sobreposição com as 15.000 de desenvolvimento
e as 120.000 de confirmação. Seeds distintas não provam independência estatística.
Auditar todo combate; falha interrompe a célula, sem descartar resultados.

Por cenário, comparar cada finalista contra `bare`, cada finalista contra
`hammer` e a primeira finalista contra a segunda, na mesma direção e ordem da
confirmação: 15 diferenças. Usar intervalo conservador de Hoeffding/união com
`alpha=0,05/15` em cada comparação e Newcombe/Wilson ajustado como aproximação.
Uma diferença só será considerada sustentada quando o intervalo conservador
excluir zero. Empates e inconclusivos do motor não são vitórias; reportar cada
desfecho. Wilson individual de 95% será descritivo, não simultâneo.

Variações de Run/iniciativa da ficha, condições, Focus, Karma, grupos e
personagens oficiais permanecem fora deste estudo. Os cenários e políticas não
representam toda a campanha, e os intervalos não certificam as regras ou os
adversários. Se a conclusão mudar entre cenários, documentar a dependência de
contexto, não procurar um vencedor global por média arbitrária.
