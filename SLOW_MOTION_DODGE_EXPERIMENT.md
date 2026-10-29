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

A função não resolve o teste, o cancelamento entre edges e troubles, o momento
exato de outras reações nem a política do personagem. Ela não está conectada ao
motor de duelo ou ao catálogo de cobertura, e não autoriza uma ficha que possui
o poder a entrar no executor como se estivesse totalmente implementado. Para
integrar com segurança, o host precisará passar a defesa efetiva — um ataque à
distância contra quem usa Brawling pode mirar Melee — e registrar antes da
rolagem a escolha, o orçamento de reações e a trouble. Também precisa de
auditoria independente do traço e testes com outras reações e fontes de edges.

Os resultados históricos permanecem vinculados às versões que os produziram;
este módulo não altera os executores anteriores nem valida novos resultados de
combate.
