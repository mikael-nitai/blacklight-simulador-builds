# Adversário armado: aproximação e ataque corporal declarado

Esta extensão experimental permite a um oponente não Heroic que carrega uma
arma declarar previamente um ataque corporal desarmado **letal**, incluindo o
recorte parcial de Crossbones. Não supõe que o personagem tenha largado a arma,
que o ataque seja automaticamente não letal ou que o ataque use a arma de fogo.
O Core, p. 36 impressa / p. 37 do PDF, distingue dano de personagens sem armas
e dano com armas, permitindo declarações explícitas. A declaração letal é uma
escolha do cenário; não é uma decisão do mestre sobre a presunção ambígua para
um golpe desarmado de quem ainda carrega arma. Ataques sem declaração continuam
bloqueados pelo host anterior. Somente o ataque Melee simples está coberto;
Fast desarmado, declarar não letal para esse caso e outras armas não estão.

`DeclaredArmedMeleeDuel` exige uma lista explícita de atacantes não Heroic e
armados e registra a declaração antes do teste. O auditor verifica a ordem,
identidades, tipo e resultado declarado antes de chamar os auditores físicos,
de reações, armas à distância, Ram e condições já existentes. Perfis Heroic e
atacantes fora da lista não recebem essa exceção. Nenhum host anterior é
registrado como substituto desta versão experimental; resultados históricos
continuam associados às suas fontes.

`ShieldAwarePolicy` usa apenas o Escudo ativo observado: se ativo, tenta se
aproximar e usar Melee; se inativo, segue sua política à distância existente.
Ela não prevê dados futuros, não otimiza todas as escolhas e pode tratar
Bleeding antes de atacar. A proteção de Escudo e Sturdy ainda reduz o dano
corporal aplicável, podendo zerá-lo. O recorte de Crossbones segue incompleto
e não inclui suas técnicas de agarrar; esta política isolada não demonstra
capacidade tática geral ou estratégia ótima.

A demonstração `python -m scripts.adaptive_armed_melee_demo --output CAMINHO_NOVO`
reproduz um combate individual auditado com seed fixa, tanto disparos quanto
ataque corporal declarado, mantendo o diagnóstico experimental e a proveniência.
Os testes também verificam que o host antigo e o novo sem declaração recusam
o ataque, que a decisão pode causar dano letal no cenário explicitamente
escolhido, e que alterações de identidade, ordem e declaração são detectadas.
O exemplo não estima taxa de vitória. Antes de realizar novos estudos de
eficácia, é necessário definir o experimento, os adversários, as métricas e as
sementes de forma independente.
