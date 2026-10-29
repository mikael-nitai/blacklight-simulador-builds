# Estado do projeto completo — 27/10/2026

**Ataques durante agarrão:** [uma extensão experimental](ENTANGLED_ATTACK_EXPERIMENT.md)
permite ataques próximos entre os dois envolvidos, incluindo Fast Strikes, com
duas hipóteses explícitas para trouble adicional. Autoacerto, terceiros,
deslocamento conjunto e contra-ataques durante o agarrão seguem fora do escopo;
não há novas estimativas de eficácia.

**Agarrar em desenvolvimento:** [transações experimentais de Grappling
Technique e Escape](GRAPPLING_EXPERIMENT.md) agora integram um duelo restrito
e um recorte parcial de Crossbones, com auditoria e duas hipóteses de gatilho.
As ações durante agarrão continuam limitadas; não há resultados de eficácia.
Uma [trilha individual](experimental_outputs/crossbones_grapple_demo_v1.json)
foi reproduzida exatamente a partir de 112 fontes no commit `b8e46d4`;
SHA-256 `b58c4073007c0ac808df28c02c95a68cabd4ea2aeb8549e622154d2c3d10ba31`.

**Adversário adaptativo experimental:** uma [política de aproximação e ataque
corporal explicitamente letal](ADAPTIVE_ARMED_MELEE_EXPERIMENT.md) permite ao
recorte armado de Crossbones reagir ao Escudo observado. A cobertura continua
limitada e não representa a ficha completa nem uma conclusão estatística. A
[demonstração individual](experimental_outputs/adaptive_armed_melee_demo_v1.json)
foi auditada e reproduzida exatamente com 105 fontes no commit `e4c51f0`;
SHA-256 `55ac92f598e3b54a299b775b44436fb9655e776091a1596d36193462f7618cb7`.

**Exploração com Ram e Crossbones parcial:** [12.000 inícios](RAM_CROSSBONES_EXPLORATION_REPORT.md)
foram auditados, e 36 registros foram reproduzidos. Contra uma política de
recuo, a maioria permaneceu inconclusiva; os dados são exploratórios e não
completam a ficha do adversário nem definem a regra de morte por autoimpacto.

**Expansão em 29/10/2026:** [Double Tap, Slow-Motion Dodge e submetralhadora
contra um alvo](RANGED_POWERS_EXPERIMENT.md) foram combinados em um host
experimental com auditorias próprias, sem promover ficha oficial completa.
A [transcrição visual de Crossbones](character_evidence/crossbones_core_p155.json)
preserva os poderes faltantes; ela não é executável. Uma leitura do Core p. 36
também corrigiu a descrição do número de alvos em `DMG-04`; o disparo da
submetralhadora contra múltiplos alvos continua pendente.
O host experimental inclui [Fast Hands e Point-Blank Parry](FAST_HANDS_PARRY_EXPERIMENT.md),
com reação restrita, Focus e ordem dos dois braços auditados. O recorte de
Crossbones continua incompleto; a opção experimental não amplia a certificação
do runner genérico.
O recorte ampliado também experimenta [Stopping Power](STOPPING_POWER_EXPERIMENT.md)
com custo de Focus e ataque adicional condicionado ao fantástico. Ele permanece
separado dos resultados certificados e não completa a ficha de Crossbones.

**Lacuna posterior à certificação:** [ataques desarmados não Heroic](NONLETHAL_GAP.md)
podem ultrapassar o limite não letal no duelo físico `split_fast_v3`. O problema
foi reproduzido em 29/10/2026. Isso limita a certificação anterior para essa
fronteira de letalidade; resultados e fontes históricas permanecem preservados.
Uma [correção experimental](NONLETHAL_EXPERIMENT.md) aplica o limite ao Ram e
a ataques de perfis claramente sem armas. O duelo físico geral ainda precisa
de cobertura dos casos ambíguos e validação antes de promover uma solução.

**Estudo de duelos sob a regra atual:** o [pré-registro](CURRENT_DUEL_STUDY_SPEC.md)
define três cenários sintéticos, cinco políticas e a seleção das finalistas antes
de observar os novos resultados. A execução e a confirmação devem ser registradas
separadamente; as taxas antigas não substituem esses dados.
O [desenvolvimento com 15.000 inícios](CURRENT_DUEL_DEV_REPORT.md) foi auditado,
congelado e selecionou duas candidatas. A [confirmação com 120.000 inícios](CURRENT_DUEL_CONFIRM_REPORT.md)
foi preservada e analisada; suas conclusões se limitam aos cenários sintéticos
descritos. A [reserva em três cenários novos](CURRENT_DUEL_HOLDOUT_REPORT.md)
foi executada, congelada e analisada. O atirador em campo aberto expôs uma
limitação importante: Ram não integra o motor desses testes; veja
[RAM_REVIEW.md](RAM_REVIEW.md). A missão completa permanece em andamento.

**Ram em desenvolvimento experimental:** a mesa confirmou rolagens separadas
para o atacante e o alvo, com redução individual; veja [RAM_RULING.md](RAM_RULING.md).
Um [duelo limitado com Ram desarmado e Prone](RAM_PRONE_EXPERIMENT.md) já
continua após a reação, com parte de Escudo e Riposte auditada. Auto-incapacitação,
armas e outras interações seguem pendentes; o exemplo não autoriza novas taxas
de vitória com Ram.
As [hipóteses de auto-incapacitação](RAM_INCAPACITY_EXPERIMENT.md) foram
implementadas em host separado e comparadas em um caso reproduzível; não são
decisões da mesa nem modificam o padrão que bloqueia esse caso. A mesa agora
confirmou que os dois danos de Ram ocorrem e que o combate termina antes da
cura quando Victor fica inconsciente; o modo experimental correspondente foi
adicionado. A morte por autoimpacto permanece sem decisão e é bloqueada.
O modo foi combinado com os poderes experimentais à distância; uma correção
impede confundir dano de contra-ataque após Ram errado com autoimpacto.

**Prone experimental:** um [duelo separado](PRONE_EXPERIMENT.md) já mantém a
condição, ajusta testes e permite levantar gastando movimento. A trilha completa
com Victor foi auditada e reproduzida. A combinação posterior com Ram permanece
experimental e não foi promovida ao runner certificado.

**Grade experimental de grupo:** [posições individuais, caminhos e alcance
por alvo](GROUP_GRID_EXPERIMENT.md) já podem ser executados por fichas dentro
de um cenário limitado; não são certificação geral de mapa ou grupo.

**Expansão experimental de grupo:** [fichas versionadas podem alimentar um
confronto de contato fixo](GROUP_CHARACTER_EXPERIMENT.md), com trilha e
verificações parciais. Reações aninhadas interrompem a fila de gatilhos
pendentes; o caso foi testado com incapacitação. Não há certificação de combate
de grupo ou de resultados de eficácia nesta etapa.
O contrato experimental de trilha v2 acrescenta auditoria independente das
fronteiras de turno, durações de Stunned/Dodge, fila de reações e gatilho de
Escudo. As trilhas v1 preservadas continuam identificadas por suas fontes.
Uma revisão independente encontrou que Resilience negativa com Healing Factor
podia reduzir Health. A combinação agora é bloqueada na entrada de fichas e
perfis, sem presumir uma solução normativa para o caso extremo.

**Continuação após a Fundação:** o grupo experimental agora exige papéis
explícitos de jogador/NPC e registra uma ordem declarada quando sobrar empate
de iniciativa. Um verificador próprio confere essa ordem e os turnos, dentro
dos limites de [GROUP_INITIATIVE_EXPERIMENT.md](GROUP_INITIATIVE_EXPERIMENT.md).
O grupo inteiro permanece experimental; seu uso em estudos depende dos gates
de reações, alvos, efeitos, posicionamento e integração de fichas.

**Atualização de 28/10:** o usuário confirmou que os braços de Fast Strikes
podem mirar alvos diferentes. A migração de grupo em `combatants/group.py` foi
interrompida antes da validação e está preservada como experimental. Consulte
[OPERACAO_FUNDACAO.md](OPERACAO_FUNDACAO.md) para o diagnóstico e as correções
posteriores; os números e estágios abaixo descrevem o momento original.
O escopo congelado e os critérios da continuação estão em
[CERTIFICACAO_FUNDACAO.md](CERTIFICACAO_FUNDACAO.md); os protótipos de grupo e
Focus não são apresentados como componentes certificados.

**Encerramento da Operação Fundação:** os cinco critérios foram atendidos no
recorte de duas fichas e nas fronteiras documentadas da certificação. A missão
mais ampla de fichas, poderes e grupo permanece futura; consulte a matriz e o
backlog em [CERTIFICACAO_FUNDACAO.md](CERTIFICACAO_FUNDACAO.md) antes de tratar
os textos históricos abaixo como estado atual.

O [controle executado do corredor atual](CURRENT_CORRIDOR_RESULTS.md) acrescentou dois exemplos completos e 1.000 duelos com todas as trilhas auditadas para combate e posições. Esses artefatos de integração não selecionam uma estratégia como melhor.

**Regra atual implementada no duelo de fichas:** [Fast Strikes por braço](SPLIT_FAST_SPEC.md), dois testes antes dos efeitos, seletor exclusivo de efeitos, Escudo antes do dano e danos/efeitos antes de Riposte. A suíte daquela etapa passou em **228 testes** e os oráculos independentes de cronologia, 108 combinações e cinco falsificações de logs passaram; a matriz de certificação registra as verificações posteriores. A revisão de Victor conserva seus valores Rank 3 e o PDF; não é progressão inventada. O [corredor atual](CURRENT_CORRIDOR.md) já usa a mesma resolução de Fast e o runner de fichas, com geometria e política que observa a parede. Grupo, novos experimentos de eficácia, sensibilidade e manuais ainda precisam da revisão atual. Os resultados abaixo são históricos quanto ao último balanceamento.

**Histórico do contrato de Fast anterior:** o motor de duelos, Focus, grupo e corredor já usa vários dados Marvel de dano, com Fast Strikes de dois componentes e duas edges. Aquele snapshot tinha **176 testes**. Desenvolvimento v2: 52.000 duelos; replicação: 240.000; reserva: 120.000; descrições v2: 60.000 encontros de grupo, 60.000 duelos de Focus e 60.000 perseguições em corredor. [POOL_V2_CONFIRM_SPEC.md](POOL_V2_CONFIRM_SPEC.md) registra a seleção anterior à replicação/reserva. A camada de fichas também executou 1.000 duelos de integração com outro personagem Rank 4 sintético. As famílias modulares de cura, estado e [duração de Dodge/Stunned](MODULAR_LIFECYCLE.md) passaram por revisão independente e equivalência de replay. Os resultados estão ligados a [commits imutáveis](RESULT_VERSIONING.md), com nomes novos para novas execuções. As 42 saídas anteriores foram preservadas em `results/legacy_scalar_v1/` e suas taxas não valem para a mesa atual.

**Histórico da fórmula escalar anterior:** o estudo de duelos restritos Rank 3 foi executado e auditado: 96 testes passam (58 do núcleo/duelos antigo, 3 da primitiva multi-alvo, 11 do protótipo de grupo, 12 de Focus, 5 do corredor, 1 das duas edges e 6 da nova rolagem de dano isolada); 400.000 duelos confirmatórios, 150.000 variações reservadas/corrigidas, 75.000 stress tests posteriores, 20.000 logs suplementares auditados e quatro demonstrações completas. Expansões **exploratórias separadas** simularam 60.000 encontros de três participantes, 60.000 duelos de Focus e 40.000 perseguições em corredor limitado, com respectivamente 600, 600 e 400 logs descritivos completos auditados. [REPORT.md](REPORT.md), [GROUP_REPORT.md](GROUP_REPORT.md), [FOCUS_REPORT.md](FOCUS_REPORT.md), [CORRIDOR_REPORT.md](CORRIDOR_REPORT.md), [MANUAL_BLACKLIGHT.md](MANUAL_BLACKLIGHT.md) e [QUICK_REFERENCE.md](QUICK_REFERENCE.md) documentam seus recortes distintos. A missão original é maior; **o objetivo completo permanece em andamento**.

| Requisito da missão original | Evidência atual | Estado |
|---|---|---|
| 1–3 Fontes, ficha e registro de regras | [CHARACTER_AUDIT.md](CHARACTER_AUDIT.md), [RULES_AUDIT.md](RULES_AUDIT.md), PDFs, FAQ e errata | Feito para a ficha atual e mecânicas do duelo; ambiguidades listadas. |
| 4–6 Motor pequeno, estado, d616 | `blacklight/`, `experimental/`, testes e trilhas | Feito para duelos físicos; protótipos separados de grupo em contato fixo, duelo de Focus e corredor com duas figuras. |
| 7–8 Gates e testes independentes | 96 testes, enumeração exata, 26.300 logs auditados na versão antiga, exemplos completos | Feito no escopo de duelo; grupo, Focus e corredor parciais, ainda sem prioridades de reações simultâneas ou recuperação por Karma. |
| 9–10 Políticas e inimigos capazes | Dez políticas de duelo, espelhos, atirador que recua/trata Bleeding, Rank 2/4; três políticas contra dois atacantes; adversário Mental Punch Rank 3/4 | Parcial: faltam inimigos com controle mental variado, grupos com poderes/posicionamento e perfis oficiais. |
| 11–15 Pré-registro, cenários, Monte Carlo, métricas, estatística | [EXPERIMENT_SPEC.md](EXPERIMENT_SPEC.md), [GROUP_EXPERIMENT_SPEC.md](GROUP_EXPERIMENT_SPEC.md), [FOCUS_DUEL_SPEC.md](FOCUS_DUEL_SPEC.md), [CORRIDOR_SPEC.md](CORRIDOR_SPEC.md), JSONs, ICs, quantis e sobrevivência | Feito para cenários declarados; há um corredor 1D limitado, mas faltam terreno com rotas/cobertura, grupos mais completos, múltiplos encontros e métricas de ações impedidas. |
| 16–19 Busca, decisões críticas, revisão cruzada, refutação | Busca de limiar, [REVIEW_FINDINGS.md](REVIEW_FINDINGS.md), resultados inválidos preservados | Parcial: ainda não se testaram contramedidas que exigem grupo/Focus ou efeito numérico de membro. |
| 20–24 Código, relatório, manual, guia, demonstrações | Arquivos locais e resultados reproduzíveis | Entregues para o recorte de duelos. |
| 25–27 Condições de sucesso e distinção entre permitido, implementado e incerto | [REPORT.md](REPORT.md), este status | **Não cumpridas para o RPG completo**: conclusão limitada a políticas e adversários testados. |

## Próximos gates técnicos antes de ampliar as conclusões

**Requisito arquitetural confirmado pelo usuário:** suportar fichas completas, poderes e variantes do sistema e aceitar novas versões de Victor ou outro personagem sem reescrever o motor. A [camada de importação e fichas](CHARACTER_PIPELINE.md) já existe e reproduz Victor atual, mas o catálogo completo de ações/efeitos e as políticas de adversários completos continuam em desenvolvimento. O exemplo Rank 4 é um teste sintético de substituição, não uma evolução presumida de Victor.

1. **Grupo completo:** `experimental/group.py` integra Fast Strikes de dois alvos, iniciativa individual, três atores, reações, Escudo, Marreta, Riposte e auditor independente no recorte de contato fixo. [GROUP_REPORT.md](GROUP_REPORT.md) descreve seis células exploratórias. Faltam posições individuais, movimento, prioridade entre múltiplas reações simultâneas, mais de três atores, poderes de inimigos e armas biológicas multi-alvo. Não reutilizar resultados de duelo/grupo como prova fora de seus cenários.
2. **Controle e Focus:** [FOCUS_REPORT.md](FOCUS_REPORT.md) cobre Mental Punch em duelo fixo, Demoralized e Shattered. A [decisão posterior da mesa](FOCUS_RULING.md) escolheu F0: o Escudo só reduz Health; F2 é contrafactual. Faltam recuperação por Karma, concentração, outros controles (grab/pin) e integração de adversário mental a grupo/terreno sem reutilizar taxas do duelo físico.
3. **Terreno e perfis oficiais:** [CORRIDOR_REPORT.md](CORRIDOR_REPORT.md) testa um mapa 1D sem cobertura e revela a limitação do campo aberto contra atirador que recua. A política do atirador não se adapta à parede. O [inventário de perfis oficiais](OFFICIAL_PROFILE_GATE.md) verificou Crossbones, Kingpin e Misty Knight diretamente nas páginas do Core, mas seus poderes ainda não têm cobertura suficiente no motor; não usar seus nomes como se as fichas completas tivessem sido simuladas. Repetir busca/validação/confirmatório separados para a expansão; não misturar hashes e sementes com a versão de duelo já congelada.
4. **Dano e Fast Strikes recém-esclarecidos:** a [regra posterior de dano](DAMAGE_POOL_RULING.md) foi integrada ao motor principal e às três extensões; [FAST_STRIKES_RULING.md](FAST_STRIKES_RULING.md) está coberto por testes forçados. A replicação e a reserva v2 estão concluídas em [POOL_V2_REPORT.md](POOL_V2_REPORT.md). Faltam refazer sensibilidade e métricas suplementares e atualizar os manuais da mesa. A metade de bônus de habilidade ímpar em Fast Strikes permanece sem decisão; o motor bloqueia esse caso.
5. **Decisões do mestre ainda relevantes:** instante de renovação das reações quando o turno cai no meio da rodada, penalidade e alvo de membro inutilizado, escopo exato da imunidade do Escudo, alcance/troca das armas biológicas. Sem isso, manter variantes separadas ou eventos sem penalidade inventada.

O material atual ajuda a jogar **agora** e responde à pergunta de duelo melhor do que um palpite. Ele ainda não prova uma estratégia ótima contra o conjunto de situações da campanha.
