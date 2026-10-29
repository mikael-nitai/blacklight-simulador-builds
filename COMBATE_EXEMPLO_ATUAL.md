# Um combate de exemplo com as regras atuais

Esta é uma leitura simplificada de uma [trilha completa auditada](experiments/current_duel_study/demos/mirror_blade_v1.json), não uma nova simulação nem uma amostra representativa. É um exemplo de como os eventos podem acontecer, inclusive quando Victor perde; não é uma previsão de resultado.

**Cenário:** Victor Rank 3 contra um espelho sintético com os mesmos recursos iniciais, 150 Health e 90 Focus. Eles começam a quatro espaços. Victor escolhe Fast Strikes com Marreta + Lâmina e efeitos da Marreta; o espelho usa Lâmina + Marreta e escolhe os efeitos da Lâmina. Ambos podem usar Escudo e Riposte. A semente é `146001`; a trilha registra regras, rerrolagens, dados e alterações de estado. O adversário não é personagem oficial.

Ambos obtiveram iniciativa fantástica e participaram da rodada bônus. Victor ficou primeiro: sua rolagem final foi `6, 1, 6` e total 20; a do espelho foi `6, 1, 1` e total 15. Em todas as rolagens de acerto mostradas abaixo, o **dado do meio é o Marvel** e os valores já incluem as rerrolagens de edge, quando houve.

## Rodada bônus

Victor se aproxima até ficar a um espaço. Com Fast, ele acerta a Marreta com `3, 6, 3` (total 18) e a Lâmina com `4, 6, 6` (total 22), contra defesa 16. O espelho ativa Escudo por reação depois de ver o acerto. A Marreta causa 13 e a Lâmina 10; o Health do espelho passa de 150 para **127**. Os dois testes vieram antes da reação e do dano.

Para conferir a Marreta: Escudo e Sturdy reduzem os 8 dados para 5; o acerto comum de Fast usa metade, arredondada para baixo, ou 2 dados. As faces `4, 6` mais `3` de bônus causam `13`. A Lâmina usa 2 dados, `3, 4`, mais `3`: causa `10`. Victor escolheu os efeitos da Marreta, então a Lâmina não aplica Bleeding nesse Fast.

O espelho desativa o próprio Escudo gratuitamente e responde com Fast. Sua Lâmina acerta com `1, 4, 5` e sua Marreta com `4, 1, 2`, esta fantástica. Victor ativa Escudo antes do dano. A Lâmina causa 11 e Bleeding; a Marreta causa 24, deixando Victor com **115 Health**. Apesar do fantástico da Marreta, ela não aplica Stunned: o espelho escolheu os efeitos da Lâmina. O espelho recupera 5 Health com Healing Factor, ficando com **132**, e ativa Escudo ao fim do turno com uma reação.

## Rodada 1

Victor desativa Escudo e acerta Fast: Marreta `3, 4, 3` causa 9; Lâmina `5, 1, 4` é fantástica e causa 22. O espelho fica com 101 Health. O fantástico da Lâmina não gera Bleeding nem ação extra porque Victor escolheu os efeitos da Marreta. Ao fim de seu turno, Victor recupera 5 Health, de 115 para **120**, e a cura efetiva remove Bleeding.

O espelho desativa Escudo e acerta seus dois testes fantásticos: Lâmina `6, 1, 5` causa 23 e Marreta `2, 1, 3` causa 33. Victor ativa Escudo como reação e cai de 120 para 64 Health. Como a Lâmina foi escolhida e teve sucesso fantástico no próprio turno, o espelho recebe uma ação extra e usa outro Fast: Lâmina `4, 1, 4` causa 25, e Marreta `3, 6, 2` causa 15. Victor fica com **24 Health**. O espelho recupera 5, indo a **106**, e ativa Escudo ao fim do turno.

## Rodada 2 e resultado

Victor desativa Escudo, acerta a Marreta com `5, 6, 3` para 12 e a Lâmina fantástica com `5, 1, 5` para 28. O espelho cai de 106 para 66. Victor recupera 5 Health e remove Bleeding, encerrando seu turno com **29 Health**.

O espelho desativa Escudo, acerta Lâmina `6, 4, 3` e Marreta fantástica `4, 1, 4`; Victor ativa Escudo como reação. Os danos são 8 e 26, respectivamente, deixando Victor com **−5 Health**. O espelho recupera 5 Health e termina com **71**. O combate termina com vitória do espelho; ambos mantêm **90 Focus**. Não houve Riposte nessa trilha.

Este combate ilustra a ordem dos dois testes, a reação de Escudo, a seleção de efeitos, Bleeding e a ação extra da Lâmina. Uma única sequência não determina qual escolha é melhor. Para comparação estatística e suas limitações, consulte [a reserva](CURRENT_DUEL_HOLDOUT_REPORT.md) e o [guia de mesa](GUIA_PROVISORIO_ATUAL.md).
