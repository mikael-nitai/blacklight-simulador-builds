# Blacklight: simulador de duelos restritos

Projeto de pesquisa reproduzível para Victor Halle (Rank 3) em *Marvel Multiverse Role-Playing Game*. Usa a ficha PDF fornecida nesta conversa, o Core Rulebook e as decisões de mesa registradas em [RULES_AUDIT.md](RULES_AUDIT.md). **Chicote não está disponível no Rank 3** e não entra no motor, nas políticas ou nos experimentos.

**Atualização em andamento:** a mesa esclareceu que [todo dano usa vários d6 literais](DAMAGE_POOL_RULING.md), enquanto o motor atual multiplica um único dado Marvel. Por isso, **todas as taxas antigas de combate são históricas para a mesa atual**, inclusive as políticas sem Fast Strikes. A [nova regra de Fast Strikes](FAST_STRIKES_RULING.md) também confirma duas edges e dois componentes de dano. O motor, os auditores e os experimentos serão refeitos sob essas decisões; preserve os JSONs anteriores apenas como evidência reproduzível da versão antiga.

## O que está implementado

O motor determinístico cobre duelos de dois personagens em campo aberto, d616, edge/trouble, iniciativa, Health/Focus, ações e movimento, ataques Melee/Agility, Fast Strikes contra um alvo, Garra, Lâmina, Marreta, Escudo, Mighty, Sturdy, Healing Factor, Do This All Day, Attack Stance, Riposte, Bleeding e Stunned. As políticas só solicitam ações; o motor valida e resolve o estado. Cada experimento registra sementes e hashes de fontes.

Ficam fora da inferência confirmatória de duelos: múltiplos alvos, penalidades de membros inutilizados, Karma, dano de Focus, fogo e outras imunidades especiais, mapa/terreno e encontros sequenciais. Há **experimentos separados** de três participantes em contato fixo no [relatório de grupo](GROUP_REPORT.md), de Mental Punch no [relatório de Focus](FOCUS_REPORT.md) e de perseguição em [corredor limitado](CORRIDOR_REPORT.md). A ficha apresenta conflito entre Initiative/Run inscritos e derivados pelo Core; a variante literal está no [resultado atual de sensibilidade](results/sensitivity.json).

**Escudo atualizado:** a mesa esclareceu posteriormente que ele é uma ação defensiva separada e não usa Fast Strikes. As antigas P6/P8/S3 foram substituídas por políticas de ativação por reação; os JSONs anteriores foram renomeados com `pre_shield_action_clarification`. A proteção se aplica ao ataque que acertou e permanece até desativação gratuita antes de usar Marreta ou Lâmina.

**Dano de Focus:** um [esclarecimento posterior](FOCUS_RULING.md) fixou que o Escudo só reduz dano de Health. No experimento de Mental Punch, F0 é aplicável à mesa; F2 permanece apenas como hipótese contrafactual registrada antes da decisão.

## Arquivos de evidência

- [CHARACTER_AUDIT.md](CHARACTER_AUDIT.md): inventário da ficha atual e conflitos com versão histórica.
- [RULES_AUDIT.md](RULES_AUDIT.md): regras oficiais, decisões de mesa, ambiguidades e exemplos calculados.
- [EXPERIMENT_SPEC.md](EXPERIMENT_SPEC.md): políticas, cenários, sementes, métricas e emendas declaradas antes da confirmação.
- [HOLDOUT_SPEC.md](HOLDOUT_SPEC.md) e [SECONDARY_SPEC.md](SECONDARY_SPEC.md): variações reservadas e métricas suplementares, com limites de inferência explícitos.
- [ADVERSARIAL_SPEC.md](ADVERSARIAL_SPEC.md): Rank superior/inferior e atirador sem munição, como stress tests exploratórios após a confirmação.
- [GROUP_SPEC.md](GROUP_SPEC.md), [GROUP_EXPERIMENT_SPEC.md](GROUP_EXPERIMENT_SPEC.md) e [GROUP_REPORT.md](GROUP_REPORT.md): protótipo e experimento exploratório de três participantes em contato fixo.
- [FOCUS_SPEC.md](FOCUS_SPEC.md), [FOCUS_DUEL_SPEC.md](FOCUS_DUEL_SPEC.md), [FOCUS_RULING.md](FOCUS_RULING.md) e [FOCUS_REPORT.md](FOCUS_REPORT.md): dano de Focus e Mental Punch; F0 é a regra atual da mesa, F2 é contrafactual.
- [DAMAGE_POOL_RULING.md](DAMAGE_POOL_RULING.md) e [FAST_STRIKES_RULING.md](FAST_STRIKES_RULING.md): decisões posteriores que exigem refazer toda a aritmética de dano e os experimentos.
- [DAMAGE_POOL_V2_SPEC.md](DAMAGE_POOL_V2_SPEC.md): gate de validação e desenho de repetição antes de integrar a regra nova no motor.
- [CORRIDOR_SPEC.md](CORRIDOR_SPEC.md) e [CORRIDOR_REPORT.md](CORRIDOR_REPORT.md): mapa limitado sem cobertura contra o atirador que recua, com dois auditores de trilha.
- [OFFICIAL_PROFILE_GATE.md](OFFICIAL_PROFILE_GATE.md): conferência visual de três perfis Rank 3 do Core e lacunas que impedem chamá-los de adversários completos no motor atual.
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
python -m scripts.verify_sources
python -m blacklight.experiment --stage dev --n 1000 --output results/dev_summary.json
python -m blacklight.experiment --stage confirm --n 10000 --output results/confirm_summary.json
python -m blacklight.sensitivity
python -m scripts.holdout
python -m scripts.secondary_metrics
python -m scripts.adversarial_scenarios
python -m scripts.group_experiment --stage description
python -m scripts.focus_experiment --stage description
python -m scripts.corridor_experiment --stage description
python -m scripts.replay --scenario mirror_hammer --strategy hammer --index 0 --output results\replay.json
```

As sementes são derivadas de SHA-256 de fase, cenário, política e índice. Reexecutar uma fase com o mesmo código produz os mesmos resultados. Os resultados de confirmação usam sementes diferentes das de desenvolvimento. `source_sha256` em cada JSON permite detectar mudanças nas regras, ficha auditada, especificação e código do pacote.

A suíte atual tem **96 testes**: 58 do motor de duelos antigo, três da primitiva multi-alvo, onze do protótipo de grupo/auditor, doze de Focus, cinco do corredor, um das duas edges e seis da nova rolagem de dano isolada. A confirmação contém 10 000 duelos por célula (400 000 no total), os cenários reservados 150 000 duelos e a amostra suplementar 20 000 trilhas completas auditadas. Os experimentos separados de grupo e Focus têm 60 000 combates descritivos cada, com 600 trilhas auditadas cada; o corredor tem 40 000 combates descritivos e 400 trilhas auditadas. A primeira versão do cenário reservado H2 tinha Health incoerente com Resilience e foi arquivada como `invalid_holdout_pre_resilience_coherence.json`; H2 corrigido é exploratório, enquanto H1/H3 preservam a reserva original. Os PNG/SVG em `results/` são reproduzíveis com `python -m scripts.plot_results` após instalar opcionalmente Matplotlib; o simulador não depende dele.

## Leitura responsável

Vitória significa que o oponente foi incapacitado primeiro (Health abaixo de 1). Combate sem vencedor após 30 rodadas é inconclusivo, não vitória. As porcentagens estimam somente os cenários e políticas nomeados. Um resultado favorável não estabelece estratégia global para o jogo inteiro. A análise de sensibilidade mantém variantes de regra separadas do cenário principal.
