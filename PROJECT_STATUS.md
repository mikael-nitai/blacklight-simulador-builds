# Estado do projeto completo — 27/10/2026

O estudo de **duelos restritos Rank 3** está executado e auditável: 61 testes passam (58 do núcleo/duelos e 3 de uma primitiva experimental multi-alvo); 400.000 duelos confirmatórios, 150.000 variações reservadas/corrigidas, 75.000 stress tests posteriores, 20.000 logs suplementares auditados e quatro demonstrações completas. [REPORT.md](REPORT.md), [MANUAL_BLACKLIGHT.md](MANUAL_BLACKLIGHT.md) e [QUICK_REFERENCE.md](QUICK_REFERENCE.md) são utilizáveis dentro desse recorte. A missão original é maior; **o objetivo completo permanece em andamento**.

| Requisito da missão original | Evidência atual | Estado |
|---|---|---|
| 1–3 Fontes, ficha e registro de regras | [CHARACTER_AUDIT.md](CHARACTER_AUDIT.md), [RULES_AUDIT.md](RULES_AUDIT.md), PDFs, FAQ e errata | Feito para a ficha atual e mecânicas do duelo; ambiguidades listadas. |
| 4–6 Motor pequeno, estado, d616 | `blacklight/`, testes e trilhas | Feito para dois combatentes; estado de grupo ainda ausente. |
| 7–8 Gates e testes independentes | 61 testes, enumeração exata, 24.000 logs auditados, exemplos completos | Feito no escopo de duelo; primitiva oficial Fast Strikes de dois alvos testada isoladamente, ainda sem combate de grupo ou Focus ofensivo. |
| 9–10 Políticas e inimigos capazes | Dez políticas, espelhos, atirador que recua/trata Bleeding, Rank 2/4, contramedida sem munição | Parcial: faltam inimigos de controle de Focus, grupos cooperativos e perfis oficiais. |
| 11–15 Pré-registro, cenários, Monte Carlo, métricas, estatística | [EXPERIMENT_SPEC.md](EXPERIMENT_SPEC.md), JSONs, ICs, quantis e sobrevivência | Feito para cenários declarados; faltam terreno, grupos, múltiplos encontros e métricas de alcance/ações impedidas. |
| 16–19 Busca, decisões críticas, revisão cruzada, refutação | Busca de limiar, [REVIEW_FINDINGS.md](REVIEW_FINDINGS.md), resultados inválidos preservados | Parcial: ainda não se testaram contramedidas que exigem grupo/Focus ou efeito numérico de membro. |
| 20–24 Código, relatório, manual, guia, demonstrações | Arquivos locais e resultados reproduzíveis | Entregues para o recorte de duelos. |
| 25–27 Condições de sucesso e distinção entre permitido, implementado e incerto | [REPORT.md](REPORT.md), este status | **Não cumpridas para o RPG completo**: conclusão limitada a políticas e adversários testados. |

## Próximos gates técnicos antes de ampliar as conclusões

1. **Multi-alvo e grupo:** `experimental/multi_target.py` já resolve uma rolagem oficial de Fast Strikes contra até dois alvos distintos, com DR individual e três oráculos manuais. Falta formalizar posições individuais, ordem de iniciativa/reação entre três ou mais atores e integração com economia de ações e efeitos da mesa. Não reutilizar o resultado de duelo como prova.
2. **Controle e Focus:** modelar ataque de Focus, demoralized/shattered, efeitos de grab/pin ou outro controle com fontes, custos e duração, e inimigo que explore esses recursos sem conhecer dados futuros.
3. **Terreno e perfis oficiais:** só adicionar cobertura, obstáculos ou personagens oficiais após verificar geometria, texto da ficha e testes. Repetir busca/validação/confirmatório separados para a expansão; não misturar hashes e sementes com a versão de duelo já congelada.
4. **Decisões do mestre ainda relevantes:** instante de renovação das reações quando o turno cai no meio da rodada, acúmulo de duas edges em Fast Strikes, penalidade e alvo de membro inutilizado, escopo exato da imunidade do Escudo, alcance/troca das armas biológicas. Sem isso, manter variantes separadas ou eventos sem penalidade inventada.

O material atual ajuda a jogar **agora** e responde à pergunta de duelo melhor do que um palpite. Ele ainda não prova uma estratégia ótima contra o conjunto de situações da campanha.
