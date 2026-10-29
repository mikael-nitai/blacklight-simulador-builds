# Prone: primitivas experimentais

O Core Rulebook fornecido, p. 38 impressa / p. 39 do PDF, descreve Prone: o
personagem no chão tem trouble em ataques Melee; ataques próximos contra ele
recebem edge e ataques à distância contra ele têm trouble. Levantar-se custa
uma casa de movimento. A condição não deve desaparecer silenciosamente no
início do turno apenas porque o personagem continua consciente.

`experimental/prone.py` calcula contribuições de edge e trouble sem escolher
dados nem cancelar fontes; a resolução normal deve combiná-las com todas as
demais causas. Também modela a despesa de uma casa para levantar, exigindo que
o chamador informe se movimento é permitido e quanto resta. Os testes
`tests/test_prone_primitives.py` incluem atacante e alvo caídos simultaneamente,
ataque próximo ou à distância, custo exato e ausência de movimento.

Essas funções **não estão integradas ao motor** e não alteram lutas ou resultados.
Elas não definem prioridade entre gatilhos, interação com movimento dividido,
efeitos de outros poderes, imunidades, reação Ram ou acessibilidade de terreno.
Antes da integração, essas fronteiras devem ser verificadas em conjunto com os
testes de ação, condições, reações, logs e replays das versões preservadas.
