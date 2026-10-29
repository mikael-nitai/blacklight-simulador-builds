# Double Tap em duelo experimental

Fonte: Core Rulebook, p. 95 impressa, PDF p. 96. O poder usa ação padrão e
um ataque à distância contra um inimigo em até dois espaços. Um acerto causa
dano regular; um sucesso fantástico causa dano duplo e Bleeding. Não há custo
de Focus indicado. As rolagens de dano seguem a convenção da mesa, com múltiplos
dados Marvel e a redução de dano aplicada pelo motor físico existente.

O executor `experimental/double_tap_duel.py` acrescenta essa opção ao duelo
experimental de Ram, Prone e ataques não letais. Ele utiliza o mesmo resolvedor
de ataque à distância para defesa efetiva, rolagem, redução, Escudo e dano;
aplica Bleeding após o ataque fantástico. Uma imunidade à munição impede tanto
o dano de munição quanto seu sangramento neste recorte. Outras imunidades não
estão modeladas. O poder não entra no catálogo genérico de fichas: o caminho
experimental exige explicitamente o poder, uma arma à distância modelada e
alcance adequado.

A auditoria `experimental/double_tap_audit.py` verifica a declaração, o
alcance, o ataque e a associação do sangramento; em seguida, remove apenas os
marcadores do poder em uma cópia temporária e executa as auditorias existentes
de dano, condições, distância, Ram e não letalidade. A trilha original não é
alterada. Testes incluem sucessos, falhas, acertos fantásticos, Escudo com
imunidade a munição e reação, Fast Strikes de Victor, Healing Factor,
adulteração de eventos, reexecução determinística e equivalência sem o poder.

O atirador dos testes é **sintético**, com alguns atributos inspirados em
Crossbones. Ele não é a ficha completa de Crossbones. Slow-Motion Dodge e as
demais técnicas de Ranged Weapons desse personagem ainda não estão integrados
com Double Tap neste host. As mesmas restrições e ambiguidades do host de Ram
continuam valendo, incluindo a rejeição de autoincapacitação de Ram e a
incerteza sobre ataques desarmados de personagens não Heroic que carregam
armas. Não usar este experimento como uma estimativa de desempenho estatístico.
