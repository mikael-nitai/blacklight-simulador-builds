# Cenários reservados para confirmação de transporte

Registrado em 2026-10-26 após a exploração `dev` e **antes** de executar estes cenários. Nenhum limiar, arma, política ou critério será alterado usando os resultados abaixo. As quatro finalistas são Marreta simples (P3), Escudo por reação após acerto + Marreta (P8), cura t75/s15 + Marreta (P9) e Escudo por reação ao fim do turno + Marreta (P10). Ataque básico P1 é referência. Usar 10 000 combates por célula, sementes SHA-256 próprias da fase `holdout`, mesmas regras e métricas de `EXPERIMENT_SPEC.md`. Não chamar estes cenários de campanha representativa; são variações controladas.

| ID | Base | Única alteração | Questão |
|---|---|---|---|
| H1 `mirror_hammer_d8` | S2 espelho Marreta | Distância inicial 1 → 8 espaços | A política de Escudo ainda funciona quando é necessário aproximar? |
| H2 `mirror_shield_r6` | S3 espelho Escudo | Resilience do adversário 5 → 6, com Health derivado 150 → 180 e Healing Factor 5 → 6 | A vantagem persiste contra um defensor legalmente mais resistente? Perfil sintético Rank 3, não ficha oficial. |
| H3 `gunner_kiter_d1` | S4 atirador que recua | Distância inicial 8 → 1 espaço | Uma abertura em alcance muda a contramedida de recuo? |

Medida principal: taxa de vitória por cenário com IC Wilson de 95%. Desfechos inconclusivos serão apresentados separadamente. Comparações exploratórias entre finalistas usarão diferenças e IC de amostras independentes; não inferir superioridade geral se os cenários apontarem em direções diferentes. A seleção das finalistas foi informada por `dev`, logo somente os **resultados**, e não a escolha de cenários, são não vistos. O código dos cenários e os hashes são guardados em `scripts/holdout.py` e no JSON de saída.

**Emenda de coerência de H2, antes de usar H2 como evidência:** a primeira execução de H2 usou Health 200 com Resilience 5, contrariando a fórmula `Health = Resilience×30` do Core p.19. O JSON, o script e a especificação anteriores foram preservados em `results/invalid_holdout_pre_resilience_coherence.json`, `results/holdout_script_pre_resilience_coherence.py` e `results/holdout_spec_pre_resilience_coherence.md`; seus números não entram na conclusão. H2 foi corrigido para Resilience 6/Health 180, com Healing Factor 6, e todos os três cenários serão reexecutados. Como o resultado da versão inválida de H2 foi visto antes da correção, **H2 corrigido é uma verificação exploratória**, não uma amostra reservada pura. H1 e H3 não mudaram e conservam a condição reservada original.
