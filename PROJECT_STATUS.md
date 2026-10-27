# Estado do projeto completo — 27/10/2026

O estudo de **duelos restritos Rank 3** está executado e auditável: 72 testes passam (58 do núcleo/duelos, 3 de uma primitiva multi-alvo e 11 do protótipo de grupo); 400.000 duelos confirmatórios, 150.000 variações reservadas/corrigidas, 75.000 stress tests posteriores, 20.000 logs suplementares auditados e quatro demonstrações completas. Uma expansão **exploratória separada** simulou 60.000 encontros de três participantes em contato fixo, com 600 logs completos auditados. [REPORT.md](REPORT.md), [GROUP_REPORT.md](GROUP_REPORT.md), [MANUAL_BLACKLIGHT.md](MANUAL_BLACKLIGHT.md) e [QUICK_REFERENCE.md](QUICK_REFERENCE.md) documentam seus recortes distintos. A missão original é maior; **o objetivo completo permanece em andamento**.

| Requisito da missão original | Evidência atual | Estado |
|---|---|---|
| 1–3 Fontes, ficha e registro de regras | [CHARACTER_AUDIT.md](CHARACTER_AUDIT.md), [RULES_AUDIT.md](RULES_AUDIT.md), PDFs, FAQ e errata | Feito para a ficha atual e mecânicas do duelo; ambiguidades listadas. |
| 4–6 Motor pequeno, estado, d616 | `blacklight/`, `experimental/`, testes e trilhas | Feito para dois combatentes; protótipo de grupo em contato fixo, sem movimento ou Focus ofensivo. |
| 7–8 Gates e testes independentes | 72 testes, enumeração exata, 24.600 logs auditados, exemplos completos | Feito no escopo de duelo; grupo parcial com três participantes, ainda sem prioridades de reações simultâneas. |
| 9–10 Políticas e inimigos capazes | Dez políticas de duelo, espelhos, atirador que recua/trata Bleeding, Rank 2/4; três políticas contra dois atacantes em contato fixo | Parcial: faltam inimigos de controle de Focus, grupos com poderes/posicionamento e perfis oficiais. |
| 11–15 Pré-registro, cenários, Monte Carlo, métricas, estatística | [EXPERIMENT_SPEC.md](EXPERIMENT_SPEC.md), [GROUP_EXPERIMENT_SPEC.md](GROUP_EXPERIMENT_SPEC.md), JSONs, ICs, quantis e sobrevivência | Feito para cenários declarados; faltam terreno, grupos mais completos, múltiplos encontros e métricas de alcance/ações impedidas. |
| 16–19 Busca, decisões críticas, revisão cruzada, refutação | Busca de limiar, [REVIEW_FINDINGS.md](REVIEW_FINDINGS.md), resultados inválidos preservados | Parcial: ainda não se testaram contramedidas que exigem grupo/Focus ou efeito numérico de membro. |
| 20–24 Código, relatório, manual, guia, demonstrações | Arquivos locais e resultados reproduzíveis | Entregues para o recorte de duelos. |
| 25–27 Condições de sucesso e distinção entre permitido, implementado e incerto | [REPORT.md](REPORT.md), este status | **Não cumpridas para o RPG completo**: conclusão limitada a políticas e adversários testados. |

## Próximos gates técnicos antes de ampliar as conclusões

1. **Grupo completo:** `experimental/group.py` integra Fast Strikes de dois alvos, iniciativa individual, três atores, reações, Escudo, Marreta, Riposte e auditor independente no recorte de contato fixo. [GROUP_REPORT.md](GROUP_REPORT.md) descreve seis células exploratórias. Faltam posições individuais, movimento, prioridade entre múltiplas reações simultâneas, mais de três atores, poderes de inimigos e armas biológicas multi-alvo. Não reutilizar resultados de duelo/grupo como prova fora de seus cenários.
2. **Controle e Focus:** modelar ataque de Focus, demoralized/shattered, efeitos de grab/pin ou outro controle com fontes, custos e duração, e inimigo que explore esses recursos sem conhecer dados futuros.
3. **Terreno e perfis oficiais:** só adicionar cobertura, obstáculos ou personagens oficiais após verificar geometria, texto da ficha e testes. Repetir busca/validação/confirmatório separados para a expansão; não misturar hashes e sementes com a versão de duelo já congelada.
4. **Decisões do mestre ainda relevantes:** instante de renovação das reações quando o turno cai no meio da rodada, acúmulo de duas edges em Fast Strikes, penalidade e alvo de membro inutilizado, escopo exato da imunidade do Escudo, alcance/troca das armas biológicas. Sem isso, manter variantes separadas ou eventos sem penalidade inventada.

O material atual ajuda a jogar **agora** e responde à pergunta de duelo melhor do que um palpite. Ele ainda não prova uma estratégia ótima contra o conjunto de situações da campanha.
