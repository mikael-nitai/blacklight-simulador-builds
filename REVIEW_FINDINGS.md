# Revisão adversarial independente do motor

**Decisão posterior da mesa, 26/10/2026:** o Escudo é uma ação defensiva separada e não usa Fast Strikes. As políticas antigas `shield_blade_fast` e `shield_hammer_fast` e o cenário espelho com essas combinações foram retirados da confirmação; seus números exploratórios anteriores não sustentam recomendações. A Lâmina só concede sua ação extra em sucesso fantástico **no próprio turno**; um Riposte fantástico não a concede. O teste `test_blade_fantastic_riposte_does_not_grant_bonus_action` cobre essa decisão. A mesa esclareceu depois que ativar Escudo custa ação padrão ou reação, inclusive ao fim do turno após ataque padrão ou após ver acerto inimigo; a defesa já vale nesse ataque e persiste até desativação gratuita antes de usar Marreta/Lâmina. O novo motor e os testes cobrem esses gatilhos.

**Estado verificado após as últimas correções:** `python -m unittest discover -s tests -q` passou **58/58** em 26/10/2026. A auditoria de logs em `tests/test_cross_scenarios.py` cobre 4.000 combates (dez políticas × quatro cenários × 100 sementes), e `results/secondary_summary.json` documenta mais **20.000 trilhas completas** recalculadas por `audit_log`, sem erro; o script e seu pré-registro têm hashes próprios. O erro de renovação das reações no início do turno foi corrigido para um orçamento por rodada, com teste forçado e verificador que rejeita segunda renovação. As seções R1–R17 abaixo preservam o histórico das versões anteriores; em particular R12 e R14 descrevem dúvidas que foram resolvidas pela decisão posterior da mesa, e suas sugestões antigas de Escudo em Fast Strikes e ação extra da Lâmina em Riposte **não se aplicam** à versão atual.

Data: 2026-10-26. Escopo revisto: `blacklight/dice.py`, `damage.py`, `engine.py`, `policies.py` e testes existentes, comparados com `RULES_AUDIT.md` e o Core Rulebook fornecido (páginas impressas 26–34, 81, 83, 99, 102, 108–109, 115). A revisão não alterou o motor. As seções R1–R10 documentam a **primeira versão** (25 testes); a revisão cruzada abaixo informa o estado após as correções (42 testes). Não interpretar os achados históricos como ainda presentes quando a tabela diz resolvido.

## Revisão cruzada após correções, antes da confirmação

Na primeira revisão cruzada, `python -m unittest discover -s tests -v` passou **42/42**, e 2.800 combates auditados (S1–S4 × 7 políticas × 100 sementes) não apresentaram erro. Após as correções de S3/S4 e inclusão de P8, a suíte passou **45/45** e uma nova amostra de **3.200** combates auditados (4 × 8 × 100) também teve zero erros de classificação, aritmética ou ledger. Isso prova consistência desses rastros com o modelo codificado, não que todo comportamento adversário seja competente ou que as regras ausentes tenham sido implementadas.

| Achado inicial | Estado na versão atual | Evidência e limite |
|---|---|---|
| R1 Mighty/knockback/Stance | **Corrigido para ataques próximos não-Fast** | Escolha da política ocorre antes dos efeitos; Marreta/Lâmina/Garra agora podem afastar, com bônus da Marreta na distância e escolha entre knockback e efeito fantástico especial. Fast Strikes continua sem essa opção, uma limitação interpretativa a manter explícita. |
| R2 economia de movimento | **Corrigido para S1–S4** | Ação padrão pode virar segundo movimento e política pode mover antes ou depois do ataque. O motor ainda não divide uma mesma ação de movimento em trechos antes/depois do ataque, permitido pelo Core, mas as políticas pré-registradas não pedem isso. |
| R3 edge no motor | **Corrigido** | `Policy.choose_edge_die` controla rerrolagem; o motor recebe callback com rolagem observada. |
| R4 fila de reações | **Corrigido para duelo com Riposte** | `deque[ReactionEvent]` com trigger ID, gastos e bound explícito. Não há múltiplas reações simultâneas de três personagens, fora do escopo de S1–S4. |
| R5 Dodge, condições e recursos | **Parcial** | Dodge, Bleeding, Stunned e fim de concentração agora têm código/testes. Karma, Focus damage, múltiplas condições e defesa com equipamentos fora dos cenários permanecem ausentes; o pré-registro delimita isso. |
| R6 Heroic | **Corrigido** | Ataque letal é limitado a um ponto antes do limiar de morte. |
| R7 testes fracos | **Parcialmente corrigido** | 42 testes, incluindo double move, iniciativa fantástica, Dodge, duas reações, Lâmina, Escudo, Marreta; o auditor independente verifica logs. Ainda faltam oráculos para política de tratamento de Bleeding e alternativas adversariais S4. |
| R8 perfis incoerentes | **Corrigido no recorte** | `Profile` exige defesa Melee/Agility = 10 + atributo e Run derivado; não valida toda a criação oficial de personagem, o que não foi alegado. |
| R9 Fast Strikes/Lâmina | **Parcial** | Há Lâmina + outra arma em uma rolagem Fast Strikes e até uma segunda ação após fantástico, com limite testado. Atingir dois alvos distintos e a penalidade de membro seguem fora do duelo; pré-registro diz isso. |
| R10 Escudo/Marreta | **Corrigido no recorte** | Escudo soma DR 2 com Sturdy 1, imunidade a munição Rank 3; Marreta fantástico aplica Stunned com expiração e quebra Stance. Imunidade a fogo/reflexão acima do Rank 3 seguem fora. |

### R11 — Atirador S4 não tratava Bleeding: refutação quantitativa, agora corrigida

O Core p.37 permite à própria vítima encerrar Bleeding gastando uma ação e passando em Logic TN 10; também termina se recuperar pelo menos 1 Health. O atirador `gunner_kiter` não possui atributo Logic no `Profile`, nem opção de tratamento em `legal_actions`, e a política `KITER` sempre atira e recua. Recuar com movimento e tratar com ação padrão seria uma contramedida legal quando está sangrando.

Reprodução anterior: usei 1.000 sementes `redteam_bleed` para cada uma das duas políticas com Lâmina, no cenário S4. `blade_hammer_fast` aplicou Bleeding ao atirador em 218 combates e venceu 95; **todas as 95 vitórias ocorreram nos combates com Bleeding**. `shield_blade_fast` aplicou Bleeding em 186 e venceu 186; **todas as 186 vitórias tinham Bleeding**. São números diagnósticos, não estimativas confirmatórias. Eles mostraram que a omissão tinha potencial de mudar materialmente a classificação.

**Correção observada:** `Profile.logic=2` no atirador, `Action("treat_bleeding")` com d616+Logic vs TN10 e política KITER que trata enquanto recua. Em 1.000 novas sementes por política, o atirador tentou 190 tratamentos (171 êxitos) contra `blade_hammer_fast` e 205 (185 êxitos) contra `shield_blade_fast`; vitórias Blacklight foram 28 e 0, respectivamente. Como as sementes mudaram, a diferença não é uma estimativa pareada do efeito causal. O snapshot agora arquivado como `results/dev_pre_heal_kiter_fix.json` registrou 24/1000 e 0/1000 vitórias nesses dois pares, antes da revisão posterior da política de fuga. Em uma terceira amostra de 1.000 combates S4/P4, recalculei à parte os dados, TN e remoção de Bleeding de **171 eventos de tratamento**: zero discrepâncias. O gate de tratamento S4 está satisfeito no recorte de Bleeding, mas a fuga dupla posterior exige uma nova bateria de desenvolvimento; excluir versões anteriores da confirmação.

### R12 — Configuração S3 foi estreitada para Fast Strikes (resolvida para ataque padrão)

Na primeira versão, `mirror_shield` começava com Escudo ativo e atacava normalmente com Marreta, uma simultaneidade fora da autorização escrita HR-06. A versão atual usa `SHIELD_HAMMER_FAST`: Marreta + Escudo na mesma ação Fast Strikes, coberta pela decisão da mesa. Foi acrescentada P8 com a mesma combinação para o jogador. O novo pré-registro identifica a emenda e separa os resultados anteriores. **Ressalva:** Riposte do inimigo usa Marreta enquanto o Escudo permanece ativo; HR-06 trata explicitamente Fast Strikes, então a permanência da defesa do Escudo durante essa reação ainda depende da interpretação de equipamento simultâneo. Rotular essa suposição ou esclarecer com o mestre antes de chamar S3 de estritamente confirmado.

### R13 — Sensibilidade das edges foi separada após detecção (resolvido)

Na primeira releitura, `stack_signature_edge` também acumulava edge por Stunned em ataques sem Signature Attack, misturando duas decisões. Isso foi comunicado e o motor passou a ter `stack_stunned_edge` separado. Qualquer resultado produzido antes dessa separação deve usar versão/identificador próprio; o pré-registro de sensibilidade para Signature Attack agora pode variar só essa fonte.

### R14 — Lâmina fantástica em Riposte: alcance da regra caseira ainda ambíguo (pendente)

`_drain_events` agora pede à política a arma do Riposte; isso corrigiu a omissão anterior do efeito da arma. Porém o gatilho da ação extra da Lâmina é verificado apenas em `_act`, depois da ação padrão; um Riposte fantástico com Lâmina não cria a segunda ação. HR-03 diz que o primeiro sucesso fantástico da Lâmina **durante o turno** concede ação extra, sem distinguir ação padrão de reação nem dizer se a ação extra pode ser tomada no turno inimigo. Se a mesa limita o benefício à ação padrão do personagem, o motor está correto; se inclui Riposte, a política com Lâmina é subestimada. Em 1.000 duelos S1/P4 de diagnóstico, ocorreram 91 Ripostes fantásticos com Lâmina em 88 combates. Pedir a decisão da mesa ou testar uma variante separada antes de concluir sobre o potencial máximo da Lâmina.

### R15 — Fonte mudou depois do último snapshot exploratório (nota de reprodutibilidade)

No momento da inspeção, o `source_sha256` do então `results/dev_summary.json` coincidia com o motor de regras mas não com a árvore completa: `EXPERIMENT_SPEC.md` e `blacklight/experiment.py` haviam mudado e `blacklight/search.py` fora criado depois. A coordenação preservou esse resultado como snapshot intermediário, agora `results/dev_pre_heal_kiter_fix.json`, e planejou nova execução. O documento científico deve identificar o hash da versão de cada resultado e congelar fontes antes da confirmação.

### R16 — Ordem entre Healing Factor e Bleeding é uma variante controlada (ambígua)

Ambos os efeitos ocorrem no fim do turno da vítima. O Core p.37 define o instante de Bleeding e p.102 define o de Healing Factor, mas os trechos consultados não estabelecem qual dos dois resolve primeiro quando coincidem. O motor passou a oferecer `end_turn_healing_first=True` como cenário principal (a cura efetiva de ao menos 1 Health remove Bleeding antes de seu tick) e `False` como alternativa. Isso **não é bug comprovado**. Etiquetar a variante em todos os resultados, testar ambas com as mesmas políticas e não misturar os lotes. Nos cenários espelho atuais, Sturdy 1 por si já absorve os 5 pontos básicos de Bleeding; a ordem tende a afetar mais perfis futuros sem DR, mas a sensibilidade deve ser medida.

### R17 — Fuga dupla do atirador S4 corrige exploração de velocidade igual (resolvido no recorte)

Na sensibilidade com Blacklight Run 6 (campo literal da ficha), o atirador com Run 6 antes atirava e recuava apenas uma vez mesmo quando terminava em distância 1; o perseguidor podia alcançá-lo e atacá-lo. A política KITER atual gasta também a ação padrão em uma segunda retirada nessa condição. Testei um proxy de velocidade igual que mantém Melee/defesa Brawling e Vigilance de Blacklight, mudando somente Agility/Run para satisfazer o validador de perfis. Em 1.000 sementes `redteam_escape`, HAMMER contra KITER atual teve **55 vitórias, zero derrotas, 945 inconclusivos**; uma política independente que sempre usa fuga dupla quando ameaçada deu exatamente o mesmo. A exploração específica de distância 1 está corrigida. Este proxy não substitui uma variante formal de ficha Run 6 com Agility 1.

Teste residual: em 1.000 sementes por política com velocidade igual, uma alternativa que prioriza tratar Bleeding antes da fuga mudou P4 de 207 para 207 vitórias e P6 de 189 para 188, enquanto realizou centenas de tratamentos. Isso não revela vantagem material da política atual nesses lotes, embora decisões de tratamento/fuga continuem relevantes para outros perfis ou horizontes. A suíte atual passou **48/48** testes.

## Achados bloqueadores para as fases táticas

### R1 — Mighty perde knockback e deixa Attack Stance ativa indevidamente (alta)

`Duel._attack` (`engine.py`, cerca da linha 259) calcula o dobro de dano em sucesso fantástico próximo, mas não oferece a escolha de knockback de Mighty. O Core p.34 e a FAQ 2025 p.1 permitem dano dobrado **e** knockback; o Core p.81 diz que knockback pode quebrar concentração. Blacklight tem Mighty 3 e Attack Stance. Portanto uma política de Stance é favorecida indevidamente quando o rival poderia afastá-lo e interromper Stance. Também é impossível avaliar a escolha tática de afastar um atirador, interromper concentração ou preservar alcance.

Reprodução sem depender de Monte Carlo: iniciar duelo Blacklight vs espelho, marcar `fighters[0].stance=True`, forçar o ataque do espelho a `6,M,6` e chamar `_attack(1, "melee")`. Observado: Blacklight vai de 150 a 78 Health, `stance=True`, `distance=1`. Se o atacante escolher o knockback permitido, a distância deveria mudar e a concentração pode cessar. O motor precisa pedir a decisão à política e executar o evento de movimento/condição com teste separado. Até lá, não comparar Stance contra adversários com Mighty como se a reação tática estivesse modelada.

### R2 — Economia de movimento incompleta invalida alcance e kiting (alta)

`_turn` (`engine.py`, cerca da linha 366) força uma única movimentação antes da ação padrão. `legal_actions` não inclui usar a ação padrão para mover. O Core pp.29,31 permite movimento antes, durante **ou depois** da ação padrão, e usar a ação padrão como segunda movimentação. Por exemplo, com Blacklight Run 5 e distância inicial 9, ele pode gastar movimento e ação padrão para aproximar 10 espaços; o motor aproxima 5 e espera. Também não permite atacar e recuar no mesmo turno. Isso altera o desfecho contra atiradores e enfraquece artificialmente contramedidas de distância. Suspender inferências sobre adversários de longo alcance até implementar e testar a economia completa.

### R3 — Escolha de edge está dentro do motor, fora das políticas (alta)

`resolve_check` usa `choose_edge_for_hit` por padrão (`dice.py`, linhas aproximadas 67 e 102). `_attack` e `_initiative` não passam decisão da política. O algoritmo maximiza primeiro chance de acerto, depois chance de fantástico e só depois total esperado; essa preferência tática foi fixada pelo árbitro, enquanto o pedido exige que quem joga escolha o dado após observar a rolagem. O efeito pode ser grande em iniciativa (a política pode valorizar a rodada bônus ou precedência) e no ataque (dano, gatilho da Lâmina, custo de Focus). Expor um callback da política com os dados já visíveis, alvo e tipo de ação; testar duas políticas de rerrolagem contra a mesma sequência de faces, sem visão de futuros sorteios.

### R4 — O mecanismo de reações não é uma fila de eventos (alta para expansão)

`_attack` chama `_drain_riposte` recursivamente, e este chama `_attack` de novo. O orçamento de reação torna a cadeia finita neste duelo com um único gatilho possível, mas a arquitetura não conserva eventos pendentes nem prioridades entre várias reações ao mesmo gatilho. A FAQ 2025 pp.4–5 impede duas reações da mesma pessoa no mesmo gatilho e ordena reações simultâneas por iniciativa; novas armas, múltiplos alvos e a segunda ação da Lâmina exigirão decidir essas prioridades. Não registrar esse motor como nível 4/5 até substituir ou envolver a recursão por fila explícita e testes de ordem.

### R5 — Defesa ativa, condições e recursos centrais não entram nas ações legais (alta para recomendação geral)

O Core p.30 oferece Dodge como ação padrão; o motor só oferece ataque, Stance, Fast Strikes, Do This All Day e espera. Não há Karma, Focus damage, demoralized, stunned, prone, grab, duração de condições ou quebra de concentração por tais condições. Assim não se pode comparar de maneira justa pressão, defesa, esgotamento de Focus e controle, embora essas sejam perguntas centrais do estudo. É aceitável chamar o estado atual de **duelo restrito**, com resultados apenas nesse espaço de ações. Não produzir manual de combate abrangente a partir dele.

## Achados adicionais

### R6 — `Heroic` e limite de dano letal não são modelados (média)

Blacklight tem a tag Heroic, e o Core p.34 deixa ataques letais, por padrão, um ponto aquém da morte, salvo intenção explícita ou decisão do Narrador. `Profile` não guarda tags e `_attack` subtrai o dano integral. Reprodução: Blacklight ataca um perfil com Health máximo 10 e DR 0 com `6,M,6`; o motor grava Health final −74, abaixo do limiar letal −10. Sob a regra padrão de Heroic, deveria ficar em −9. Isso não altera uma vitória definida por primeira incapacitação, mas invalida logs de morte, sequelas e múltiplos encontros.

### R7 — Lacunas de testes permitem falsos sinais de validação (média)

`test_horizon_is_inconclusive` contém uma asserção condicional; se o combate termina, não testa o horizonte. `test_attack_stance_uses_standard_action_then_doubles_ability_bonus` testa a função de dano isolada, sem verificar uma transição real de ataque depois da ativação. `test_reaction_budget_never_negative` usa 50 sementes em vez de forçar dois gatilhos distintos e a tentativa de terceiro; não prova a restrição da FAQ. Faltam testes de rodada bônus, edge na iniciativa, Dodge, double move, reação na rodada bônus e a quebra de Stance. Criar oráculos por sequência de dados e estados forçados.

### R8 — Parâmetros sintéticos permitem perfis incoerentes sem aviso (média)

`Profile.__post_init__` verifica apenas recursos positivos e alguns campos não negativos. Aceita, por exemplo, Melee 0 com defesa Melee 30 e Run 20, sem poder que os justifique. O usuário permite adversários sintéticos, mas pede coerência mecânica. Um construtor de perfis deveria derivar defesas e velocidade dos atributos ou exigir a exceção e sua fonte. Os cenários devem declarar por que um valor se afasta da fórmula.

### R9 — O escopo do Fast Strikes e da Lâmina permanece menor que o pedido (média, lacuna reconhecida)

O ataque `fast_strikes` do motor só aplica um resultado a um alvo, com metade do dano normal ou integral em fantástico. Isso é uma leitura conservadora do alvo único, mas não modela o uso verificado contra dois alvos, pois o motor é só de duelo. A função `blade_second_strike_eligible` testa o portão fantástico e nenhum evento adicional, arma, dano ou interação. O esclarecimento recente do usuário permite desenhar testes: primeiro acerto comum não cria segundo ataque; primeira falha fantástica também não; primeiro sucesso fantástico gera exatamente **uma nova rolagem/ação com Lâmina**; segundo fantástico não cria terceiro ataque; Fast Strikes, se escolhido, deve ser resolvido em cada uma das no máximo duas ações conforme a decisão da mesa, sem somar bônus de armas distintas. Implementar somente após registrar todos os detalhes restantes do Escudo/Chicote e da Lâmina.

### R10 — Escudo e Marreta exigem exceções e temporizadores explícitos (alta para testar o arsenal)

O usuário esclareceu que o Escudo acrescenta redução de multiplicador 2 **cumulativa** com Sturdy 1, chegando a redução efetiva 3 nos ataques elegíveis. Isso é uma regra da mesa que supera a regra geral de não acumulação; `Profile.health_dr=1` e `_attack` não representam equipamento, elegibilidade ou essa exceção. Um teste discriminante deve comparar o mesmo ataque com DR 1 sem Escudo e DR 3 com Escudo, aplicar DR antes do dobro e zerar todo o dano quando o multiplicador não exceder 3. Não generalizar a soma para outras fontes de DR.

O usuário também esclareceu que um fantástico com Marreta aplica **stunned**. Pelo Core p.38, stunned encerra concentração, impede ações e dá edge aos ataques contra o alvo; dura uma rodada salvo especificação diferente. O motor ainda não representa condições nem expiração. Testar o fantástico da Marreta, a interrupção de Attack Stance, a perda do turno aplicável, o edge recebido e a expiração no instante correto. Confirmar se a mesa especifica duração diferente antes de fixar essa parte.

## Gate recomendado

As primitivas de d616 e dano têm bons oráculos independentes. O motor está apto a **testes de desenvolvimento de duelo elementar limitado**, desde que seus resultados não sejam apresentados como estratégia geral. Para passar ao nível de tática e confirmação, corrigir R1–R5, adicionar os testes discriminantes de R7 e revisar logs curtos com knockback, iniciativa fantástica, reações e recuperação. Resultados já gerados sob a versão anterior devem receber identificador próprio e não ser misturados com execuções após a correção.
