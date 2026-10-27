# Manual de combate do Blacklight — ficha Rank 3 atual

Este manual usa a ficha **de Downloads** fornecida nesta conversa (Health 150, Focus 90, Melee 6, Mighty 3, Sturdy 1, Run derivado 5), o Core Rulebook, a errata/FAQ e as decisões de mesa registradas em [RULES_AUDIT.md](RULES_AUDIT.md). O Chicote está indisponível no Rank 3. As recomendações se baseiam em duelos simulados de campo aberto; não são uma regra universal para qualquer cena. Consulte [REPORT.md](REPORT.md) para as taxas, intervalos e limites do experimento.

**Fast Strikes está em revisão:** a [decisão posterior da mesa](FAST_STRIKES_RULING.md) confirma duas edges e dois danos separados por arma. A comparação antiga com Marreta e as contas de Fast Strikes abaixo não devem orientar uma escolha quantitativa até a nova implementação e validação.

## Plano principal para um duelo próximo

1. Se o alvo estiver ao alcance de Melee (1 espaço no modelo), use a **Marreta** como ação padrão. Seu multiplicador é `Rank 3 + Mighty 3 + 2 da Marreta = ×8`; o bônus de atributo de dano é `+6`. Sem redução, um acerto comum causa `dM×8+6` Health. Um sucesso fantástico de ataque normal dobra o dano e pode aplicar **Stunned** pela Marreta. A opção de knockback de Mighty pode ser útil para quebrar concentração ou abrir distância; no modelo, escolhê-la substitui o efeito fantástico especial da arma.
2. Use o **Escudo** como defesa separada. Se ainda houver reação ao fim de seu turno, pode ativá-lo mesmo depois de atacar com a ação padrão. Também pode esperar e ativá-lo como reação **depois de ver que um ataque inimigo acertou**: a proteção já vale contra aquele ataque. Ele permanece ativo até você desativá-lo gratuitamente. **Antes de atacar com a Marreta ou a Lâmina, desative-o.** Ele nunca participa de Fast Strikes.
3. Enquanto o Escudo Rank 3 estiver ativo, ataques inimigos Melee e Agility que causem **dano de Health** têm `−2` no multiplicador, somado ao `−1` do Sturdy 1 pela regra da mesa. A redução total é `3`, aplicada antes de dobrar ou dividir dano. **Escudo e Sturdy não reduzem dano de Focus**, inclusive Mental Punch Melee, conforme o [esclarecimento posterior da mesa](FOCUS_RULING.md). Ele não muda a rolagem de acerto. A imunidade a fogo e munição foi confirmada pela mesa, mas o simulador só testou diretamente munição; peça ao mestre para classificar o ataque se a fonte não for evidente.
4. A conta de reações é compartilhada: Victor dispõe de duas por rodada na interpretação conservadora adotada pelo simulador. Escudo e Riposte disputam esse orçamento. Não use duas reações no mesmo gatilho. Se o Escudo já está ativo, não gaste outra reação para ativá-lo; preserve as restantes para Riposte quando um ataque próximo falhar.

Os dois momentos de ativação do Escudo — ao fim do próprio turno e após um acerto inimigo — foram testados como políticas separadas. A comparação não sustenta uma preferência universal entre eles. Ao fim do turno, a defesa já estará pronta para o próximo ataque, mas consome uma reação mesmo se nenhum golpe vier. Esperar o acerto preserva a reação até ser necessária, mas não cobre uma ameaça que não seja um ataque elegível ou caso Victor já não possa reagir. Decida conforme a ameaça visível e a chance de Riposte.

## Primeiro turno e distância

- **Victor age primeiro, alvo a 1 espaço:** Marreta; ao fim do turno, considere ativar Escudo com reação. Se a iniciativa for fantástica e conceder rodada bônus, esse ataque adicional é uma oportunidade forte de incapacitar ou aplicar Stunned antes da rodada normal.
- **Inimigo age primeiro:** se um ataque acertar e Victor tiver reação, ative o Escudo antes do dano. Se o ataque errar, considere Riposte em alcance Melee. O mesmo erro não permite também ativar Escudo, pois a ativação após acerto exige acerto.
- **Alvo fora de 1 espaço:** aproxime-se com sua ação de movimento, até Run 5. Se ainda não alcançar, pode usar a ação padrão como segunda movimentação. Escolha a aproximação conforme o espaço disponível na mesa; o simulador não considera obstáculos, cobertura ou ameaças de oportunidade.
- **Atirador que recua mais rápido:** uma perseguição em campo aberto pode se prolongar sem que você consiga uma ação de ataque. O Escudo Rank 3 evitou dano de munição nos cenários modelados, mas muitos duelos terminaram sem vencedor até a rodada 30. Num [corredor exploratório sem saída](CORRIDOR_REPORT.md), a parede permitiu contato em todas as lutas modeladas; o atirador, porém, manteve a política fixa de recuo. Verifique as rotas, a cobertura e os objetivos do mapa real antes de apostar nessa solução.

## Armas e poderes por situação

| Opção | Quando considerar | Custo e limite |
|---|---|
| Marreta comum | Pressão e chance de Stunned contra um alvo próximo; foi a arma ofensiva mais consistente entre as políticas testadas. | Ação padrão, alcance 1 no modelo. Fantastic dobra o dano normal e pode aplicar Stunned. |
| Escudo | Ameaça de dano Melee/Agility ou munição; preservar Health. | Ação padrão **ou reação** para ativar. Permanece até desativação gratuita. Desative antes de Marreta/Lâmina. |
| Lâmina + Marreta com Fast Strikes | Quando Bleeding, efeito de membro ou uma segunda ação com Lâmina forem taticamente valiosos; duas edges estão confirmadas pela mesa. | Um teste de acerto e duas contas de dano por uso, uma por arma. Cada parcela é metade em acerto comum ou integral em fantástico. Bleeding, efeito de membro e Stunned podem acompanhar o fantástico; a primeira rolagem fantástica no próprio turno concede somente **uma** nova ação com Lâmina e novo teste. A conta final ainda está em revalidação. |
| Lâmina simples | Quando o sangramento ou a inutilização narrativa de membro vale mais que a maior chance de incapacitar rapidamente com Marreta. | Cada acerto aplica Bleeding sem acumular. O `+1` de multiplicador não soma ao Mighty 3 de Victor. Penalidade mecânica do membro ainda depende do mestre. |
| Garra | Efeito de sangramento em fantástico, se a situação exigir essa arma. | `+1` de multiplicador não supera Mighty 3; Bleeding só no fantástico. Não foi uma política finalista medida na bateria principal. |
| Do This All Day | Recuperação quando a próxima ação de ataque tem valor menor que a sobrevivência imediata, especialmente se há segurança momentânea. | Ação padrão, gasta de 5 a 15 Focus no Rank 3, preservando pelo menos 1 Focus; recupera até 2 Health por Focus. Rotinas automáticas de cura perderam pressão contra duelistas fortes nos testes. |
| Attack Stance | Quando puder manter concentração e recuperar o turno investido em ativá-la. | Ação padrão para ativar; dobra o `+6` de atributo **no dano**, não o multiplicador ou a rolagem de acerto. Pode ser quebrada por Stunned/knockback. Não foi superior como abertura fixa nos duelos testados. |
| Riposte | Depois que um ataque próximo inimigo falha, se há reação e alcance. | Reação; escolha uma arma de ataque próximo legal. Um Riposte fantástico com Lâmina **não** concede a ação extra da Lâmina. |

## Sinais para mudar o plano

- **Escudo inimigo ativo:** seu dano da Marreta cai pelo multiplicador após a redução; continue avaliando acertos e Stunned, mas não conte com dano bruto calculado sem defesa. Contra DR alta, a Marreta foi melhor que o Fast Strikes de um alvo testado.
- **Afastamento constante:** se dois turnos seguidos se gastarem apenas em aproximação e o inimigo mantiver a distância, a política de perseguição do estudo já está falhando. Mude o objetivo tático da cena em vez de repetir uma corrida sem ataque.
- **Sem reações:** não planeje Escudo reativo e Riposte até a próxima renovação. Se o Escudo continua ativo, a defesa permanece sem novo gasto; depois que você o desativar para atacar, uma reação disponível será necessária para reativá-lo.
- **Focus caindo:** a cura não deve consumir a última unidade de Focus. Evite um ciclo de Do This All Day que troca todo turno de ataque por 30 Health sem verificar se o inimigo causa mais do que isso.
- **Inimigo causa dano de Focus:** o teste separado de [Mental Punch](FOCUS_REPORT.md) encontrou resultados próximos para Marreta com e sem Escudo sob a regra válida F0; a defesa não reduz esse dano. Outros poderes mentais, controles e combinações não foram avaliados.
- **Vários aliados inimigos:** o [protótipo de grupo](GROUP_REPORT.md) avaliou apenas dois agressores em contato fixo; não extrapole suas taxas para grupos móveis ou com poderes distintos.

## Próximas evoluções

A ficha atual **não** mostra Extended Reach 1. O Chicote foi declarado indisponível no Rank 3. Não inclua alcance de 25 m, imobilização do Chicote ou Extended Reach na conta atual. Quando houver uma nova ficha e autorização de Rank, reavalie a legalidade e os efeitos antes de comparar evoluções; este estudo não identifica uma aquisição futura ótima.
