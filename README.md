# Blacklight: simulador de duelos restritos

Projeto de pesquisa reproduzível para Victor Halle (Rank 3) em *Marvel Multiverse Role-Playing Game*. Usa a ficha PDF fornecida nesta conversa, o Core Rulebook e as decisões de mesa registradas em [RULES_AUDIT.md](RULES_AUDIT.md). **Chicote não está disponível no Rank 3** e não entra no motor, nas políticas ou nos experimentos.

## O que está implementado

O motor determinístico cobre duelos de dois personagens em campo aberto, d616, edge/trouble, iniciativa, Health/Focus, ações e movimento, ataques Melee/Agility, Fast Strikes contra um alvo, Garra, Lâmina, Marreta, Escudo, Mighty, Sturdy, Healing Factor, Do This All Day, Attack Stance, Riposte, Bleeding e Stunned. As políticas só solicitam ações; o motor valida e resolve o estado. Cada experimento registra sementes e hashes de fontes.

Ficam fora da inferência confirmatória de duelos: múltiplos alvos, penalidades de membros inutilizados, Karma, dano de Focus, fogo e outras imunidades especiais, mapa/terreno e encontros sequenciais. Há um **protótipo experimental separado** de três participantes em contato fixo, descrito no [relatório de grupo](GROUP_REPORT.md). A ficha apresenta conflito entre Initiative/Run inscritos e derivados pelo Core; a variante literal está no [resultado atual de sensibilidade](results/sensitivity.json).

**Escudo atualizado:** a mesa esclareceu posteriormente que ele é uma ação defensiva separada e não usa Fast Strikes. As antigas P6/P8/S3 foram substituídas por políticas de ativação por reação; os JSONs anteriores foram renomeados com `pre_shield_action_clarification`. A proteção se aplica ao ataque que acertou e permanece até desativação gratuita antes de usar Marreta ou Lâmina.

## Arquivos de evidência

- [CHARACTER_AUDIT.md](CHARACTER_AUDIT.md): inventário da ficha atual e conflitos com versão histórica.
- [RULES_AUDIT.md](RULES_AUDIT.md): regras oficiais, decisões de mesa, ambiguidades e exemplos calculados.
- [EXPERIMENT_SPEC.md](EXPERIMENT_SPEC.md): políticas, cenários, sementes, métricas e emendas declaradas antes da confirmação.
- [HOLDOUT_SPEC.md](HOLDOUT_SPEC.md) e [SECONDARY_SPEC.md](SECONDARY_SPEC.md): variações reservadas e métricas suplementares, com limites de inferência explícitos.
- [ADVERSARIAL_SPEC.md](ADVERSARIAL_SPEC.md): Rank superior/inferior e atirador sem munição, como stress tests exploratórios após a confirmação.
- [GROUP_SPEC.md](GROUP_SPEC.md), [GROUP_EXPERIMENT_SPEC.md](GROUP_EXPERIMENT_SPEC.md) e [GROUP_REPORT.md](GROUP_REPORT.md): protótipo e experimento exploratório de três participantes em contato fixo.
- [VALIDATION_PLAN.md](VALIDATION_PLAN.md) e [REVIEW_FINDINGS.md](REVIEW_FINDINGS.md): oráculos independentes e revisão adversarial.
- `blacklight/`: dado, dano, motor, políticas, auditor de logs, busca, experimentos e sensibilidade.
- `tests/`: oráculos e 4.000 trilhas auditadas em dez políticas × quatro cenários × 100 sementes.
- `results/`: JSONs estruturados; arquivos `pre_*` e `invalid_*` são versões históricas excluídas das conclusões.
- [DEMONSTRATIONS.md](DEMONSTRATIONS.md): quatro combates completos válidos com rolagens, ações e estados auditados; a trilha antiga do Escudo em Fast Strikes está arquivada.
- [REPORT.md](REPORT.md): resultados confirmatórios, intervalos, refutação, sensibilidade, cenários reservados e gráficos.
- [MANUAL_BLACKLIGHT.md](MANUAL_BLACKLIGHT.md) e [QUICK_REFERENCE.md](QUICK_REFERENCE.md): estratégia prática e consulta durante a mesa.
- [PROJECT_STATUS.md](PROJECT_STATUS.md): o que a missão completa já tem de evidência e os gates ainda abertos.

## Executar no Windows

Abra PowerShell nesta pasta. Requer Python 3.11 ou mais recente; não há dependências Python externas para os experimentos.

```powershell
python -m unittest discover -s tests -q
python -m blacklight.experiment --stage dev --n 1000 --output results/dev_summary.json
python -m blacklight.experiment --stage confirm --n 10000 --output results/confirm_summary.json
python -m blacklight.sensitivity
python -m scripts.holdout
python -m scripts.secondary_metrics
python -m scripts.adversarial_scenarios
python -m scripts.group_experiment --stage description
python -m scripts.replay --scenario mirror_hammer --strategy hammer --index 0 --output results\replay.json
```

As sementes são derivadas de SHA-256 de fase, cenário, política e índice. Reexecutar uma fase com o mesmo código produz os mesmos resultados. Os resultados de confirmação usam sementes diferentes das de desenvolvimento. `source_sha256` em cada JSON permite detectar mudanças nas regras, ficha auditada, especificação e código do pacote.

A suíte atual tem **72 testes**: 58 do motor de duelos congelado, três da primitiva experimental de Fast Strikes contra dois alvos e onze do protótipo de grupo/auditor. A confirmação contém 10 000 duelos por célula (400 000 no total), os cenários reservados 150 000 duelos e a amostra suplementar 20 000 trilhas completas auditadas. O experimento de grupo tem 60 000 combates **exploratórios separados** e 600 trilhas completas auditadas. A primeira versão do cenário reservado H2 tinha Health incoerente com Resilience e foi arquivada como `invalid_holdout_pre_resilience_coherence.json`; H2 corrigido é exploratório, enquanto H1/H3 preservam a reserva original. Os PNG/SVG em `results/` são reproduzíveis com `python -m scripts.plot_results` após instalar opcionalmente Matplotlib; o simulador não depende dele.

## Leitura responsável

Vitória significa que o oponente foi incapacitado primeiro (Health abaixo de 1). Combate sem vencedor após 30 rodadas é inconclusivo, não vitória. As porcentagens estimam somente os cenários e políticas nomeados. Um resultado favorável não estabelece estratégia global para o jogo inteiro. A análise de sensibilidade mantém variantes de regra separadas do cenário principal.
