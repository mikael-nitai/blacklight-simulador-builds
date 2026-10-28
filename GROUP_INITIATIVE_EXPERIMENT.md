# Iniciativa no grupo experimental

O combate de grupo atual continua experimental e restrito a contato fixo; esta
etapa cobre apenas a ordem inicial e não certifica o restante do combate.
O Core, página impressa 28 (página 29 do PDF local), ordena resultados maiores
primeiro; em empate, favorece fantástico, depois maior modificador de iniciativa
e depois personagem de jogador. Se persistir empate entre jogadores, eles podem
escolher a ordem ou rolar para desempatar. O texto consultado não especifica
como resolver todos os empates entre NPCs.

`GroupBattle` exige `initiative_roles`, uma tupla com `player` ou `npc` para
cada ficha, independente da equipe. Um `initiative_tie_order` opcional contém
uma permutação de todos os índices; ela só é usada quando os critérios anteriores
ainda deixam um empate, e representa uma decisão declarada antes da execução.
Sem ela, a execução para antes de qualquer turno se houver empate remanescente.
Sem papéis, para antes de rolar a iniciativa. O projeto não atribui papéis a
partir de nomes, fichas ou equipes, nem apresenta a ordem declarada como uma
regra oficial de desempate de NPCs. A ordem resolvida, os papéis e a escolha de
desempate ficam no resultado experimental e na trilha quando a auditoria está
ativada. A ordenação de duelos históricos permanece inalterada.

O verificador `audit_group_initiative` usa perfis e configuração fornecidos
separadamente, reconstrói resultados dos dados e rerrolagens, confere a ordem
declarada e os inícios de turno. Ele não verifica o restante dos efeitos, custos,
reações ou desfecho do grupo e não prova a origem aleatória dos dados. Os testes
incluem NPC antes de jogador na lista, fantástico e total superiores, dados
ausentes, desempates repetidos, trilha adulterada e combate completo.

O [executor experimental por fichas](GROUP_CHARACTER_EXPERIMENT.md) registra
uma interpretação operacional para reações adiadas e faz verificações adicionais
dos alvos. Ainda faltam, antes de usar o grupo em estudos de eficácia: auditoria
completa das ações, efeitos e reações, posições/movimento e um protocolo de
congelamento próprio. Stunned de múltiplas fontes segue a hipótese experimental
de durações paralelas, sem que isso seja regra oficial confirmada. A renovação
exata de reações e outras ambiguidades de mesa continuam documentadas em
`RULES_AUDIT.md`. Não usar taxas históricas como resultados da regra atual.
