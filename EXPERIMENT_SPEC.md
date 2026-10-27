# Pré-registro dos experimentos de duelo restrito

Versão: 2026-10-26, anterior à bateria quantitativa. Este documento congela hipóteses e escolhas metodológicas. O simulador cobre **duelos de dois personagens em campo aberto**, com posição reduzida à distância em espaços. Não representa todo o RPG; em especial, não representa mutilação como penalidade mecânica, controles de vários alvos, Karma, dano de Focus, cobertura ou terreno.

## ADEMP

**Aim.** Comparar políticas praticáveis do Blacklight Rank 3 atual em duelos bem definidos, verificar o impacto de Attack Stance, cura, Lâmina, Marreta e Escudo e tentar encontrar contramedidas.

**Data-generating mechanism.** Core Rulebook de 2023 com errata de julho/2025, FAQ de março/2025, ficha de Downloads fornecida em 26/10/2026 e decisões da mesa HR-01 a HR-06 de `RULES_AUDIT.md`. O motor `blacklight/` é determinístico com estado, políticas e semente. Cada combate termina na primeira incapacitação (Health < 1) ou após 30 rodadas, quando é inconclusivo. A ação padrão e a movimentação ocorrem em ordem escolhida; a fila explícita resolve Riposte. O orçamento de reações é renovado uma vez no início de cada rodada, inclusive rodada bônus, e compartilhado entre Riposte e Escudo. O Escudo começa desativado. Ativá-lo custa ação padrão ou reação; após um acerto inimigo, a reação já protege contra esse ataque. Pode-se ativar com reação ao fim do próprio turno, inclusive após ataque padrão. Permanece ativo até desativação gratuita; antes de atacar com Marreta/Lâmina, é desativado.

**Estimands.** Probabilidade de vitória, derrota e inconclusão até 30 rodadas; diferença de vitória contra a política de ataque simples no mesmo cenário; dano após redução acumulado até as rodadas 3, 5 e 10, com resultado final carregado adiante em combates encerrados; Health final, Focus gasto, cura efetiva, dano mitigado, acertos, acertos fantásticos, contra-ataques e stuns. O denominador é sempre o total de combates iniciados, exceto quando explicitamente indicado.

**Methods.** Primeiro executar 1000 combates por par política/cenário com sementes de desenvolvimento. Inspecionar falhas, logs e invariantes antes da confirmação. Confirmar todas as políticas predefinidas com 10 000 sementes novas por par, se a validação do motor permanecer satisfatória. As sementes derivam de SHA-256 de `(stage, scenario, policy, index)`, sem alegação de pareamento entre políticas. Comparações de proporções usam IC para diferença entre amostras independentes e correção de Bonferroni para as comparações com a baseline dentro de cada cenário. Nenhuma política é alterada depois de ver os resultados confirmatórios.

**Performance measures.** Taxas e IC Wilson, diferença em pontos percentuais e IC simultâneo, médias e erros-padrão Monte Carlo para métricas contínuas. Reportar cada cenário separadamente; não aplicar pesos de encontros inventados. Não declarar ótimo global.

**Interpretação de renovação das reações.** O Core p.29 diz tanto “uma reação por rodada” quanto que, depois do gasto, o personagem só volta a reagir no início do próximo turno. A errata do Combat Reflexes assegura uma reação adicional “each round”. Para evitar uma terceira reação na mesma rodada, o motor renova o orçamento de duas no início da rodada, inclusive a bônus. Essa escolha conservadora para o instante exato de renovação deve ser confirmada na mesa antes de generalizar as taxas com Escudo e Riposte.

## Políticas Blacklight pré-definidas

| ID | Ação operacional |
|---|---|
| P1 `bare_attack` | Aproxima-se até alcance e ataca sem arma confirmada; usa Riposte quando legal. Knockback de Mighty se quebrar Attack Stance inimiga. |
| P2 `stance_bare` | Ativa Attack Stance com ação padrão; depois age como P1. |
| P3 `hammer` | Ataca com Marreta; fantástico aplica Stunned. |
| P4 `blade_hammer_fast` | Usa Fast Strikes com Lâmina e Marreta, uma rolagem, dano específico do power e efeitos das duas armas; se primeira rolagem for sucesso fantástico e alvo sobreviver, usa a segunda ação de Lâmina com nova rolagem, no máximo uma vez. |
| P5 `hammer_heal` | Age como P3, mas gasta até 15 Focus em Do This All Day quando faltarem pelo menos 30 Health; precisa manter Focus ≥1. |
| P6 `shield_blade_reactive` | Usa Lâmina com Fast Strikes de alvo único; Escudo separado, ativado por reação após acerto inimigo, se disponível. Desativa gratuitamente antes do próximo ataque; nunca combina Escudo e Fast Strikes. |
| P7 `hybrid` | Ativa Attack Stance, ataca com Marreta e usa Do This All Day sob o limiar de P5. |
| P8 `shield_hammer_reactive` | Ataca normalmente com Marreta. Se um ataque inimigo acertar e houver reação, ativa o Escudo antes do dano. Desativa gratuitamente antes do próximo ataque próprio. |
| P9 `hammer_heal_t75_s15` | Marreta comum e Do This All Day com gasto 15 quando faltarem pelo menos 75 Health. Candidata da busca de limiar descrita abaixo; a seleção será reavaliada com S3 corrigido. |
| P10 `shield_hammer_endturn` | Ataca normalmente com Marreta e, ao fim do próprio turno, gasta uma reação para ativar o Escudo. Desativa gratuitamente antes do ataque seguinte; uma segunda reação pode restar para Riposte. |

Todas usam escolha de edge orientada primeiro a chance de acerto e depois a chance de sucesso fantástico; esta é uma política explícita, não regra do dado. Cada política tem apenas informação visível do estado corrente. A leitura conservadora para Fast Strikes contra um alvo aplica dano pela metade em sucesso comum e dano integral em fantástico, uma única aplicação por rolagem.

## Cenários pré-definidos

| ID | Inimigo e política | Distância | Propósito |
|---|---:|---:|---|
| S1 `mirror_attack` | Espelho Rank 3 do Blacklight, ataque básico/Riposte | 1 | Referência simétrica, não adversário final. |
| S2 `mirror_hammer` | Espelho Rank 3, Marreta, Stunned, Riposte e knockback contra Stance | 1 | Oponente capaz de interromper planos ofensivos. |
| S3 `mirror_shield` | Espelho Rank 3: Marreta comum e Escudo ativado por reação após acerto; DR efetiva 3 enquanto ativo | 1 | Resistência e reação defensiva com custo compartilhado com Riposte. |
| S4 `gunner_kiter` | Sintético Rank 3: Melee 2, Agility 6, Resilience 4, Vigilance 2, Logic 2, Health 120, Focus 60, Run 6, Agility ranged sem bônus de arma, alcance normal 10 espaços, ataque de munição; ataca e recua em campo aberto, trata bleeding com Logic TN10 quando seguro, e usa ação padrão mais movimento para recuar duas vezes se um perseguidor com Run ≥6 chegar a 1 espaço | 8 | Distância, sangramento e contramedida adversarial ao alcance. |

Perfis sintéticos não representam personagens oficiais. `gunner_kiter` não tem poderes, DR, nem reações especiais. Seu dano ranged é `dMarvel×3+6` e a defesa deriva de Agility 6. Nos cenários S1–S3, inimigos usam capacidades de ficha simétrica ou a variante declarada de Escudo.

**Emenda histórica superada por decisão posterior da mesa.** Após a primeira revisão, testamos Escudo + Marreta em Fast Strikes, mas a mesa esclareceu depois que Escudo é ação defensiva separada e não participa de Fast Strikes. Os resultados dessa versão estão em `dev_pre_shield_action_clarification.json` e ficam excluídos. P6/P8 e S3 foram reformulados para ativação defensiva real; P10 compara a reação ao fim do turno com a reação após acerto. A fase `dev` será refeita com dez políticas.

**Emenda de contramedida ao sangramento.** A revisão adversarial encontrou que o atirador anterior nunca tentava estancar bleeding. O Core p.37 permite ação padrão e Logic TN10; S4 agora tem Logic 2 e escolhe tratar o sangramento enquanto usa sua ação de movimento para recuar. Esta mudança precede a nova bateria `dev` e todos os resultados anteriores de S4 ficam excluídos das conclusões.

**Busca de limiar de cura após exploração, antes da confirmação.** O limiar inicial de 30 Health ausente de P5 acionou Do This All Day com frequência e sacrificou ataques. Para evitar um ajuste informal, serão comparados seis candidatos de Marreta + cura: limiares 45, 60 e 75, cada um com gasto 10 ou 15 Focus, em S1–S3 e 1000 sementes de busca novas por célula. O critério prévio de seleção é a maior **pior taxa de vitória** entre S1–S3; em empate, menor gasto médio de Focus. O candidato selecionado será adicionado como P9 e testado uma vez no conjunto confirmatório. A busca não será usada como evidência de superioridade. S4 não entra no critério porque a tática de recuo em campo aberto cria um problema distinto de alcance.

**Resultado da busca refeita, sem força confirmatória.** A primeira busca escolheu `hammer_heal_t75_s15` usando o S3 anterior, agora ilegal; seu JSON foi arquivado. Na busca refeita com S3 legal, a mesma candidata liderou os seis limiares de cura pelo critério prévio, com pior taxa 26,9% em S3 (1000 duelos). P9 permanece essa política. A busca não é evidência de superioridade sobre Marreta sem cura.

**Plano de sensibilidade registrado antes da execução.** Usar 3000 sementes independentes por célula para (a) ficha derivada pelo Core `Initiative +2, Run 5` contra campos literais da ficha `Initiative +1, Run 6`, alterando só Victor e testando P3 em S1/S2/S4; (b) cura antes ou depois de bleeding no fim do turno, com P4/P6 em S1/S2; (c) um ou dois edges em Fast Strikes por Signature Attack + Blazing-Fast Fists, com P4/P6 em S1/S2. Reportar diferenças e incerteza sem misturar variantes com a confirmação principal.

**Emenda adversarial antes da confirmação.** Na primeira sensibilidade, Run 6 produziu 100% de vitórias contra o atirador porque ele insistia em atirar quando Victor chegava a 1 espaço. A economia de ações permite usar ação padrão e movimento para recuar duas vezes. S4 agora faz isso quando o perseguidor tem Run pelo menos igual ao seu. O arquivo `sensitivity_pre_kiter_escape_fix.json` documenta o resultado refutado; a sensibilidade será repetida antes de qualquer conclusão.

## Sensibilidade e limites prévios

- Rodar uma variante com dois edges para Signature Attack + Blazing-Fast Fists, sujeita à decisão do mestre; não misturar com a análise principal de um edge.
- A penalidade mecânica de membro inutilizado está ausente; P4/P6 provavelmente são subestimadas quanto ao controle, mas a direção exata do efeito em vitória não é presumida.
- Healing Factor e bleeding disparam no fim do turno da vítima. A ordem não está explicitada nas fontes conferidas; análise principal dá prioridade à cura da vítima, que pode encerrar bleeding antes do dano. Uma análise de sensibilidade separada inverte a ordem, sem misturar resultados.
- O Escudo custa ação padrão ou reação para ativar; desativação é gratuita. O modelo usa reação após acerto (antes do dano) e reação ao fim do turno, com o mesmo orçamento de Riposte. O Escudo não entra em Fast Strikes.
- Campo aberto permite recuo indefinido. S4 demonstra uma contramedida nesse ambiente, sem generalizar para mapas fechados.
- O Chicote está indisponível no Rank 3 por decisão do usuário e fica fora dos cenários.
- Não há inimigos de controle de Focus, grupos, terreno, dano mental ou perfis oficiais até seus subsistemas passarem em testes específicos. Esta bateria não responde essas perguntas.
