# Slow-Motion Dodge: contrato experimental

O Core Rulebook, p. 118 impressa (PDF p. 119), descreve uma reação acionada
quando um inimigo ataca a defesa Agility do personagem; o ataque recebe uma
trouble. Não há custo de Focus indicado. O poder aparece, por exemplo, nas
fichas de Crossbones e Hawkeye, mas nenhuma ficha oficial completa está pronta
para uso apenas por causa desta etapa.

`experimental/slow_motion_dodge.py` oferece uma transição isolada e imutável:
o chamador informa qual defesa o ataque realmente utiliza, se a reação é legal,
quantas reações restam e se já houve reação ao mesmo gatilho. Uma decisão
explícita consome uma reação e acrescenta uma trouble; uma tentativa ilegal é
rejeitada. O recorte exige ativação antes da rolagem para que o modificador seja
aplicado ao teste. Essa ordem é uma escolha conservadora da implementação,
não uma decisão adicional atribuída à mesa.

A função isolada não resolve o teste, o cancelamento entre edges e troubles,
o momento de outras reações nem a política do personagem. O host separado
`experimental/slow_motion_duel.py` a conecta a um duelo **restrito** com duas
fichas Heroic sintéticas e apenas Accuracy, Brawling, Combat Reflexes e este
poder. Ele verifica a defesa efetiva: um ataque à distância contra quem usa
Brawling mira Melee e não dispara Slow-Motion Dodge. A escolha e o gasto são
registrados antes da rolagem. Foram verificados gatilhos, recusa, reação
esgotada, testes completos reproduzíveis e as auditorias físicas existentes.

Uma auditoria específica independente também verifica a associação entre a
reação e o ataque, a trouble e a defesa utilizada, além das auditorias físicas,
de resultados e de distância. Testes incluem adulteração desses registros,
alcance longo e Dodge comum. O recorte não cobre outras reações, armas
biológicas, Fast ou condições adicionais. A funcionalidade não está no catálogo
de cobertura e não autoriza uma ficha que possui o poder a entrar no executor
genérico como se estivesse completamente implementado. Testar essas interações
é requisito antes de ampliar o escopo.

Os resultados históricos permanecem vinculados às versões que os produziram;
este módulo não altera os executores anteriores nem valida novos resultados de
combate.
