# Confirmação dos duelos físicos atuais

Pré-registro de confirmação, feito após congelar o desenvolvimento e antes de
executar estas células. A [seleção exploratória](experiments/current_duel_study/development_selection_v1.json)
foi registrada no commit `a7ac036`; seu SHA-256 é
`87fec028587c5c18ce4a7f55f4a45b3bc282f34241d18d9f4e55f00f23dc4529`.
O desenvolvimento foi vinculado ao commit `0e9f307`. O critério que escolheu
as finalistas foi registrado em `CURRENT_DUEL_STUDY_SPEC.md` antes de observar
as taxas de desenvolvimento.

## Células e sementes

Reexecutar as duas finalistas `hammer_fast_hammer` e `hammer_fast_blade`, mais
o controle `bare`, nos cenários `mirror`, `rank4` e `gunner_corridor` exatamente
como definidos no pré-registro de desenvolvimento. A seleção não é revista
com base nos resultados de confirmação. São **10.000 inícios por célula**,
nove células e 90.000 inícios; auditoria de todos os combates é obrigatória.
O custo dos 15.000 inícios exploratórios foi considerado aceitável para esta
amostra. A semente mestra é **827104292**, distinta da de desenvolvimento
`827104291`; os demais parâmetros de célula e fórmula `character-batch-v2`
são os mesmos. As células usam seeds diferentes e não são pareadas.

Um fracasso de auditoria interrompe a célula; não excluir combates falhos.
Resultados usam nomes novos e congelamento por fontes após commit. O índice,
as amostras de métricas por início e as sementes são preservados; os logs
integrais de todos os inícios não são armazenados.

## Comparações fixadas

Para cada cenário, comparar a taxa de vitória de cada finalista com a do
controle `bare`, num total de **seis comparações**. Usar o intervalo conservador
de Hoeffding com união e `alpha = 0,05/6` por comparação, além do intervalo
Newcombe/Wilson ajustado como aproximação. A garantia do primeiro depende do
modelo de inícios independentes e não valida o simulador ou a representatividade
dos cenários. Apresentar vitória, derrota, empate e inconclusão separadamente,
e Wilson 95% para proporções individuais como descrição não simultânea.

Uma diferença só é reportada como sustentada neste conjunto de comparações se
o intervalo conservador ajustado excluir zero. A confirmação não declara uma
finalista globalmente melhor: as comparações pré-especificadas são contra o
controle, e desempenho nos três cenários não representa todos os encontros.
Qualquer comparação direta entre finalistas é descritiva/exploratória nesta fase.
Métricas contínuas e quantis por início, custos de Focus, cura, ataques,
fantásticos, Riposte, Stunned e ação extra são descrições e não têm testes
confirmatórios múltiplos predefinidos.

## Reserva e limites

A reserva prevista no pré-registro de desenvolvimento segue intocada, com
sementes e configurações próprias. A confirmação não autoriza ajustar as
políticas e chamá-las de confirmadas na reserva. O experimento cobre apenas os
três cenários físicos sintéticos e suas políticas. Faltam adversários oficiais
completos, combate mental, Karma, grupos e mapas gerais. A variante da ficha
com Run e iniciativa inscritos no PDF continua fora do cenário principal e
precisa de sensibilidade separada.
