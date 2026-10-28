# Pré-registro: duelos físicos com Fast Strikes atual

**Fase:** desenvolvimento. Registrado antes de executar esta bateria e de
consultar suas taxas. Os resultados antigos `pool_v2` usam outro contrato de
Fast e não são usados para selecionar políticas desta bateria.

## Pergunta e recorte

Entre as políticas descritas abaixo, quais mantêm melhor taxa de vitória no
pior dos três cenários físicos sintéticos? O objetivo é selecionar candidatas
para avaliação posterior, não determinar uma estratégia global ou uma taxa
para a campanha. A ficha é `rank3_2026-10-27_split_fast.json`: Victor usa
Health 150, Focus 90, Melee 6, Resilience 5, Run 5 e iniciativa +2 derivados,
com os poderes e armas registrados. O conflito do PDF quanto a Run 6 e
iniciativa +1 permanece documentado; esse é um recorte principal, não uma
decisão presumida do mestre.

A regra da mesa aplica dois testes em Fast, duas edges quando cabíveis em
cada teste e uma arma escolhida para efeitos por uso. Dados de dano literais
seguem HR-07/08/09. A defesa do Escudo e Sturdy se somam contra Health; Focus
e imunidades não suportadas pelo motor físico não entram. Bleeding, Healing
Factor, iniciativa, reações e condições seguem as implementações e ressalvas
de `RULES_AUDIT.md`. A rodada termina por incapacitação; após 30 rodadas sem
vitória, o combate é inconclusivo, não perda ou vitória.

## Políticas de Victor fixadas antes da exploração

Todas usam aproximação, Riposte quando possível, Escudo reativo após acerto,
escolha de edge para acertar e não escolhem knockback; não ativam postura,
Escudo no fim do turno ou cura voluntária. Isso não prova que essas omissões
sejam ótimas. As cinco políticas são as seguintes:

| ID | Ação principal em alcance | Efeito escolhido em Fast | Riposte |
|---|---|---|---|
| `bare` | ataque desarmado | não se aplica | desarmado |
| `hammer` | Marreta comum | não se aplica | Marreta |
| `hammer_fast_hammer` | Fast Marreta + Lâmina | braço 0, Marreta | Marreta |
| `hammer_fast_blade` | Fast Marreta + Lâmina | braço 1, Lâmina | Marreta |
| `blade_fast_blade` | Fast Lâmina + Marreta | braço 0, Lâmina | Lâmina |

A tabela resume decisões principais; o objeto `SplitFastPolicy` completo e
todos os parâmetros de cada célula serão registrados em cada resultado. Cada
política escolhe somente com informações disponíveis na observação.

## Desenvolvimento: três cenários sintéticos

1. `mirror`: cópia sintética e renomeada da ficha de Victor, como adversário
   hipotético, sem alegar ser personagem oficial. Usa Marreta + Lâmina em
   Fast, seleciona efeitos da Marreta, Escudo reativo e Riposte. Campo aberto,
   distância inicial 1. O uso do arsenal de Victor pelo espelho é uma hipótese
   de cenário, não uma regra geral para NPCs.
2. `rank4`: ficha sintética `synthetic_rank4_split_fast.json`, com Mighty 2,
   Sturdy 1 e ataque desarmado comum; não recebe Riposte ou Fast não presentes
   na ficha. Campo aberto, distância inicial 1. Sua legalidade integral de build
   não foi certificada.
3. `gunner_corridor`: ficha sintética `synthetic_rank4_nonammo_gunner.json`,
   ataque à distância **não classificado como munição**, Run 6 e alcance 10.
   Usa política de recuo com tratamento de Bleeding e reconhecimento limitado
   da parede (`WallAwarePolicy`). Corredor de uma linha, comprimento 12, posições
   iniciais 0 e 8. Não representa um poder oficial de energia, fogo ou Focus.
   O comportamento especial da parede pode não ocorrer contra Run 5; não
   atribuir resultados a essa decisão sem medir quando ela efetivamente atua.

Todos os ataques/rodadas de todas as 15 células devem passar pelas auditorias
do runner. O script interrompe a célula que falhar; não descartar combates.
São 1.000 inícios por célula, master seed de desenvolvimento `827104291` e
identidade de célula/seed definida pelo runner `character-batch-v2`. As células
usam seeds diferentes em função das fichas e políticas; **não são pareadas**.
Cada lote registra os índices e sementes dos inícios auditados e amostras de
métricas por início, mas não guarda cada trilha completa. Registrar também
demonstrações integrais separadas; para rever uma amostra, reproduzir sua seed.

## Seleção antes de confirmação

Após completar todas as células de desenvolvimento, escolher **duas** entre
as quatro políticas não controle (`hammer`, `hammer_fast_hammer`,
`hammer_fast_blade`, `blade_fast_blade`) pela maior das suas menores taxas de
vitória nos três cenários. Desempatar por maior média aritmética das três taxas
e depois pela ordem alfabética do ID. Essa média e o mínimo servem somente para
priorização no conjunto fixo de três cenários; não atribuem probabilidades aos
encontros da campanha. A política `bare` acompanha as finalistas como controle.
O resultado da seleção e os hashes dos 15 arquivos serão registrados antes da
confirmação; não trocar políticas ou critérios após ler taxas confirmatórias.

## Confirmação e reserva ainda não executadas

Repetir as duas finalistas e `bare` nos três cenários com sementes mestras
separadas; selecionar `n` antes de olhar os resultados, visando 10.000 por
célula se o tempo for aceitável, e registrar qualquer redução e a precisão
correspondente. Comparar cada finalista com `bare` por cenário: seis diferenças
de taxas independentes, com ajuste familiar Bonferroni `alpha=0,05/6` e
intervalo conservador de Hoeffding/união. O intervalo de Newcombe/Wilson pode
ser apresentado como aproximação adicional. Separar vitória, derrota, empate e
inconclusão; não tratar células diferentes como amostras pareadas.

Após congelar confirmação, usar sementes novas e cenários não usados na seleção:
espelho com Lâmina Fast/Escudo no fim do turno a distância 4; Rank 4 físico com
Sturdy 2 em contato; e atirador não munição no campo aberto com distância 8.
Essas são variações sintéticas predefinidas, não personagens oficiais nem
uma garantia de generalização. Comparações e limites de confiança serão
declarados antes de executar a reserva. Não ajustar a política após observar
qualquer resultado reservado e ainda chamá-lo de confirmação independente.

## Medidas e limites

Apresentar proporções e Wilson 95% por célula; para os confrontos desde o início,
registrar recursos finais, rodadas/turnos, dano aplicado/recebido/mitigado,
cura efetiva, Focus gasto, ataques, acertos, fantásticos, Ripostes, Stunned,
ações extras da Lâmina e dano até rodadas 3/5/10. Quantis 10/50/90 usam posto
mais próximo; média e erro-padrão usam todos os inícios, não só sobreviventes.
Para horizontes após o fim, o dano acumulado conserva o valor final. Duração
em rodadas inclui casos censurados no limite; não é sobrevivência mediana.

Os parâmetros são um experimento limitado com adversários artificiais. Faltam
controle mental/Focus, Karma, fogo, membros com penalidades numéricas, perfis
oficiais completos, grupo validado, mapa geral e adversários mais adaptativos.
Renovação exata das reações e ordem Healing Factor/Bleeding permanecem
interpretações registradas, e não devem ser apresentadas como decisões do mestre.
