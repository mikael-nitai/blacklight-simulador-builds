# Experimento exploratório de três participantes, contato fixo

Registrado em 27/10/2026 antes de produzir resultados de grupo. Este experimento **não altera** nem integra a confirmação de duelos em `results/confirm_summary.json`. Seu objetivo é testar se o protótipo de economia de ações e Fast Strikes contra dois alvos produz trilhas auditáveis e como três políticas se comportam sob dois níveis declarados de oposição. Nenhuma taxa de vitória deste recorte deve ser generalizada a encontros reais com mapa, Focus, poderes dos inimigos ou coordenação complexa.

## Gerador e políticas

Todos permanecem em contato, sem deslocamento ou terreno. Victor usa a ficha Rank 3 atual. Os dois adversários são **sintéticos**, idênticos dentro de cada cenário, concentram seus ataques básicos em Victor e não possuem poderes nem armas. G1: cada adversário Rank 2, Melee 4, Resilience 3, Health 90, defesa Melee 14. G2: cada adversário Rank 3, Melee 6, Resilience 5, Health 150, defesa Melee 16. Ambos têm Vigilance 2, Agility 1, Focus 60, Run 5. O modelo usa iniciativa individual, possível rodada bônus, uma ação padrão por turno e reações renovadas no início da rodada; a ambiguidade de renovação está em `RULES_AUDIT.md`.

Comparar, em G1 e G2: GH, Marreta focada no adversário vivo com menor Health; GS, mesma Marreta com Escudo ao fim do turno ou após acerto; GF, Fast Strikes **sem armas biológicas** contra os dois inimigos vivos, ou um se apenas um restar. GF usa uma só rolagem e aplica a defesa e a redução de cada alvo; não há bônus de Lâmina nem segundo golpe caseiro. As políticas de Victor usam Riposte quando legal. Os inimigos atacam Victor no próprio turno e não usam Riposte.

## Procedimento e medidas

Executar 1000 combates de desenvolvimento por célula, inspecionar invariantes; depois 10 000 sementes **novas** por célula para descrição, sem escolher uma política após ver desenvolvimento. Semente: primeiro 8 bytes SHA-256 de `blacklight-group-v1|fase|cenário|política|índice`. Horizonte máximo de 30 rodadas; se ninguém eliminou o outro lado, classificar como inconclusivo. Reportar separadamente vitória, derrota e inconclusão com denominador de todos os combates iniciados e IC Wilson 95% por proporção. As políticas não são pareadas por semente porque seus consumos de aleatoriedade diferem; não fazer teste de diferença pareada. Guardar hashes SHA-256 de fontes, especificação e script; auditar a trilha completa de cada centésima semente da fase de descrição.

## Gates e limites

Antes de medir: suíte de testes, oráculos forçados para ataque em duas defesas, reação ao Escudo, Riposte, Stunned, rodada bônus, reprodutibilidade e auditor independente de Health/dano/reação. Toda divergência na auditoria bloqueia a execução. O motor experimental rejeita múltiplos usuários de Escudo/Riposte porque a prioridade de reações simultâneas ainda não foi implementada. Embora o FAQ oficial explique a ordem de prioridade, essa mecânica não é necessária nestes dois cenários. Não usar o experimento como prova de estratégia global ótima.
