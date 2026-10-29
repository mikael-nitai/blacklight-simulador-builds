# Blacklight Rank 3 — consulta rápida para a mesa

Para as decisões da sua mesa e a ficha atual. O [guia detalhado](GUIA_PROVISORIO_ATUAL.md) explica as exceções e dúvidas. Estas opções não são prova de uma estratégia ótima em todas as situações.

## No seu turno

1. **Ataque próximo:** Fast Strikes com Marreta + Lâmina é uma opção testada. Escolha antes de rolar qual braço fornece os efeitos: Marreta para tentar Stunned; Lâmina para Bleeding e possibilidade de ação extra.
2. **Faça um teste de acerto por braço**, cada um com Melee +6 e duas edges confirmadas para Victor. Pode escolher um alvo diferente para cada braço. Resolva ambos os testes antes de aplicar danos e efeitos; Riposte vem depois deles.
3. **Se precisar de cura:** Do This All Day usa ação padrão; gaste de 5 a 15 Focus no Rank 3, sem baixar de 1 Focus. Recupere até 2 Health por Focus gasto, limitado ao Health máximo. Healing Factor pode recuperar até 5 Health no fim do turno, conforme o guia detalhado.
4. **Escudo:** se tiver reação disponível, pode ativá-lo ao fim do turno mesmo depois de atacar. Ele permanece ativo; desativá-lo é gratuito e necessário antes de usar Marreta ou Lâmina.

## Quando o inimigo age

- **Ataque acertou:** pode ativar Escudo como reação após ver o acerto e antes do dano. Para ataques Melee/Agility que causam Health, reduz 2 dados de dano; Sturdy 1 reduz mais 1, quando aplicável. A mesa confirmou imunidade a fogo e munição; casos específicos podem depender do mestre. Escudo e Sturdy não reduzem dano de Focus.
- **Ataque próximo errou:** se tiver alcance e reação disponíveis, considere Riposte. Fantástico no Riposte da Lâmina não concede ação extra.
- **Reações:** a interpretação do simulador concede duas por rodada com Combat Reflexes. Elas são compartilhadas entre as opções; não use duas reações no mesmo gatilho. A renovação exata depende da interpretação registrada no [guia](GUIA_PROVISORIO_ATUAL.md).

## Dano sem redução do alvo

Os dados são **d6 literais**; cada face `1` no dano vale 6. O teste de acerto usa três dados d616 separados, com o dado Marvel identificado; nele o `1` também vale 6 e indica resultado fantástico, sujeito às regras de sucesso.

| Ataque que acertou | Acerto comum | Sucesso fantástico |
|---|---:|---:|
| Marreta normal | `8d6 + 6` | dobro do total rolado; pode aplicar Stunned |
| Lâmina ou Garra normal | `7d6 + 6` | dobro do total rolado; efeitos da arma |
| Fast: braço com Marreta | `4d6 + 3` | `8d6 + 6`; Stunned se escolhido para efeitos |
| Fast: braço com Lâmina | `3d6 + 3` | `7d6 + 6`; efeitos da Lâmina se escolhida |

No Fast, cada braço erra ou acerta independentemente. Some as parcelas que atingirem o mesmo alvo. Se os efeitos escolhidos forem os da Marreta, a Lâmina não aplica Bleeding nem concede ação extra; se forem os da Lâmina, a Marreta não aplica Stunned. Uma ação extra de Lâmina por fantástico no próprio turno pode usar Fast com novos testes, mas não cria uma cadeia de ações extras.

Aplique a redução de dano do alvo à quantidade de dados **antes** de calcular a metade do componente comum de Fast; arredonde a metade dos dados para baixo. A exceção de 0 dados e outros detalhes estão no [guia detalhado](GUIA_PROVISORIO_ATUAL.md).

**Roll'em no Discord:** para um teste de acerto, `3d6ns` mostra os três dados sem ordená-los; identifique o dado do meio como Marvel e faça a conta manualmente. Use `d6` para cada rerrolagem de edge/trouble. Para dano, uma expressão como `8d6ns` mostra as faces: troque manualmente cada `1` por 6 e some o bônus correspondente. O total comum exibido pelo bot não faz essa troca automaticamente. A [sintaxe oficial do Roll'em](https://rollem.rocks/docs/v1-syntax) documenta os dados e `ns`; se o servidor exigir prefixo, `r` é uma [opção documentada](https://rollem.rocks/docs/prefix). A configuração do bot na sua mesa não foi testada.

**Bleeding:** se a Lâmina escolhida acertar, aplica 5 de Health no fim de cada turno da vítima, sem acumular; recuperação de Health ou tratamento pode removê-lo e a redução aplicável a condições pode protegê-la. A Garra aplica Bleeding em sucesso fantástico.

**Ram:** após preencher os requisitos de movimento, é uma reação opcional. Atacante e alvo rolam danos separados e aplicam suas próprias reduções; o atacante sofre dano regular e o alvo, dobro, ou triplo em fantástico. O limite de morte por autoimpacto ainda não foi decidido. Consulte os requisitos e limites no [guia detalhado](GUIA_PROVISORIO_ATUAL.md).

Chicote não está disponível para Victor no Rank 3. O antigo [QUICK_REFERENCE.md](QUICK_REFERENCE.md) é histórico e contém fórmulas de dano anteriores à regra atual.
