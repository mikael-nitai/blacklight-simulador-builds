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

## Duelo experimental

`experimental/prone_duel.py` usa essas contribuições em um host separado de
duelo físico de dois personagens em campo aberto. A política recebe observações
imutáveis com as condições dos dois e escolhe se tenta levantar. Levantar
consome uma casa do movimento escolhido; os ataques usam edge/trouble próprios
de Prone junto das demais fontes. Se o personagem decidir permanecer no chão,
esse host aceita apenas deslocamento zero: **não modelar rastejar é uma
restrição experimental**, não uma proibição geral da regra. Ele não implementa
movimento dividido, terreno, imunidades ou Ram.

O host exige políticas que decidam sobre levantar, rejeita mecânicas fora do
catálogo físico e é recusado pelo runner certificado. Os resultados antigos não
mudam. `experimental/prone_duel_audit.py` reconstrói independentemente a
condição, o custo de levantar e as contribuições de edge/trouble, incluindo os
dois testes de Fast; seu uso acompanha as auditorias físicas, espaciais e de
resultado já existentes. `tests/test_prone_duel.py` cobre replays sem Prone,
acertos, postura de ambos, Fast, Escudo, Stunned e Riposte em confrontos com a
ficha atual de Victor e um espelho sintético, além de falsificações de registro.

Não há ainda uma integração entre esse host e o checkpoint de Ram. Antes de
usar combate continuado com Ram, é preciso conectar a aplicação de Prone,
revisar a ordem dos efeitos, reações e incapacitação, e validar as interações
pendentes sem substituir resultados históricos.

Uma [trilha ilustrativa completa](experimental_outputs/prone_victor_duel_001.json)
usa a ficha atual de Victor contra um espelho sintético que começa caído e foi
programado deliberadamente para permanecer assim. A seed é `246810`; a
simulação terminou em quatro rodadas, passou pelas auditorias e foi reproduzida
com bytes idênticos. O arquivo tem SHA-256
`44125b08a8259ef9bc69b7573b0c4114ff86f8ffe3f336e58d5e2721befe293a`
e registra suas fontes no commit `9f710c1`. Esse único exemplo não mede a
eficácia de uma estratégia e não usa Ram.
