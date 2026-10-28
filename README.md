# Blacklight: simulador de duelos restritos

**Regra atual em 27/10/2026:** o [duelo genérico já executa o novo Fast Strikes](SPLIT_FAST_SPEC.md): um teste por braço, ambos antes dos efeitos, escolha prévia de um único braço para efeitos, Escudo antes do dano e ambos os danos/efeitos antes de Riposte. O usuário confirmou que os braços podem mirar alvos distintos. Os experimentos `pool_v2` preservam o contrato anterior e são históricos quanto ao novo Fast. O [corredor de duas fichas](CURRENT_CORRIDOR.md) também usa a regra atual; a migração de grupo começou, mas continua experimental e sem validação suficiente. Nenhuma taxa antiga mede essa versão.

Projeto de pesquisa reproduzível para Victor Halle (Rank 3) em *Marvel Multiverse Role-Playing Game*. Usa a ficha PDF fornecida nesta conversa, o Core Rulebook e as decisões de mesa registradas em [RULES_AUDIT.md](RULES_AUDIT.md). **Chicote não está disponível no Rank 3** e não entra no motor, nas políticas ou nos experimentos.

**Experimentos anteriores:** o motor de duelos, Focus, grupo e corredor passou a lançar [vários d6 literais com face Marvel 1→6](DAMAGE_POOL_RULING.md). Na versão `pool_v2`, Fast Strikes usava duas edges, um teste de acerto e dois componentes de dano no mesmo alvo; a [regra atual](FAST_STRIKES_RULING.md) mudou esse contrato. As 42 saídas da fórmula escalar antiga foram copiadas para [results/legacy_scalar_v1/](results/legacy_scalar_v1/); suas taxas são históricas para a mesa atual. O [relatório v2](POOL_V2_REPORT.md) também é histórico: consolida a replicação, a reserva e as três extensões anteriores ao balanceamento mais recente. A sensibilidade e os manuais completos ainda precisam ser refeitos para a regra atual.

## O que está implementado

A [camada de fichas versionadas](CHARACTER_PIPELINE.md) carrega Rank, seis atributos, recursos e habilidades graduadas de arquivos externos ao motor. Ela já executa duelos e baterias com outra ficha, conserva a origem do PDF e bloqueia poderes sem suporte. O objetivo final inclui fichas oficiais completas e evolução de Victor sem reescrever o motor; a cobertura atual continua limitada às mecânicas validadas do recorte físico.

Os lotes genéricos auditam todos os combates por padrão. A opção explícita
`--audit-every N` permite amostragem exploratória; quando não cobre todos os
combates, o resultado é identificado e não passa pelo congelamento reservado a
lotes genéricos integralmente auditados. Veja [fichas e execução](CHARACTER_PIPELINE.md)
e os limites da [certificação](CERTIFICACAO_FUNDACAO.md).

As famílias de cura, ativação de estados e [duração de Dodge/Stunned](MODULAR_LIFECYCLE.md) já usam módulos reutilizáveis. Os [resultados congelados](RESULT_VERSIONING.md) ficam ligados ao commit executado; a evolução do motor produz arquivos novos e preserva as medições anteriores.

O [grupo experimental por fichas](GROUP_CHARACTER_EXPERIMENT.md) aceita equipes
e alvos separados em contato fixo, com auditoria parcial da trilha. Ele ainda
não é certificado para estudar eficácia ou substituir os duelos validados.

O motor determinístico cobre duelos de dois personagens em campo aberto, d616, edge/trouble, iniciativa, Health/Focus, ações e movimento, ataques Melee/Agility, Fast Strikes contra um alvo, Garra, Lâmina, Marreta, Escudo, Mighty, Sturdy, Healing Factor, Do This All Day, Attack Stance, Riposte, Bleeding e Stunned. As políticas só solicitam ações; o motor valida e resolve o estado. Cada experimento registra sementes e hashes de fontes.

Ficam fora da inferência confirmatória de duelos: múltiplos alvos, penalidades de membros inutilizados, Karma, dano de Focus, fogo e outras imunidades especiais, mapa/terreno e encontros sequenciais. Há **experimentos separados** de três participantes em contato fixo no [relatório de grupo](GROUP_REPORT.md), de Mental Punch no [relatório de Focus](FOCUS_REPORT.md) e de perseguição em [corredor limitado](CORRIDOR_REPORT.md). A ficha apresenta conflito entre Initiative/Run inscritos e derivados pelo Core; a variante literal está no [resultado atual de sensibilidade](results/sensitivity.json).

**Escudo atualizado:** a mesa esclareceu posteriormente que ele é uma ação defensiva separada e não usa Fast Strikes. As antigas P6/P8/S3 foram substituídas por políticas de ativação por reação; os JSONs anteriores foram renomeados com `pre_shield_action_clarification`. A proteção se aplica ao ataque que acertou e permanece até desativação gratuita antes de usar Marreta ou Lâmina.

**Dano de Focus:** um [esclarecimento posterior](FOCUS_RULING.md) fixou que o Escudo só reduz dano de Health. No experimento de Mental Punch, F0 é aplicável à mesa; F2 permanece apenas como hipótese contrafactual registrada antes da decisão.

## Arquivos de evidência

- [CURRENT_CORRIDOR_RESULTS.md](CURRENT_CORRIDOR_RESULTS.md): controles executados de fichas e Fast atual no corredor, com dois exemplos completos e 1.000 trilhas auditadas.

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
- `tests/`: oráculos e trilhas cruzando políticas, cenários e sementes; a suíte informa a contagem atual de testes.
- `results/`: JSONs estruturados; `legacy_scalar_v1/`, `pre_*` e `invalid_*` são históricos. Os experimentos `pool_v2` precedem o último balanceamento de Fast Strikes.
- [OPERACAO_FUNDACAO.md](OPERACAO_FUNDACAO.md): diagnóstico, correções, evidências, limites e próximos gates da auditoria estrutural.
- [CERTIFICACAO_FUNDACAO.md](CERTIFICACAO_FUNDACAO.md): escopo congelado e matriz dos critérios de conclusão da continuação da auditoria.
- [DEMONSTRATIONS.md](DEMONSTRATIONS.md): quatro combates completos válidos com rolagens, ações e estados auditados; a trilha antiga do Escudo em Fast Strikes está arquivada.
- [REPORT.md](REPORT.md): relatório histórico da fórmula escalar, com resultados, intervalos, refutação, sensibilidade e cenários reservados.
- [MANUAL_BLACKLIGHT.md](MANUAL_BLACKLIGHT.md) e [QUICK_REFERENCE.md](QUICK_REFERENCE.md): registros históricos de opções; suas contas e recomendações ainda não foram atualizadas para as regras atuais.
- [PROJECT_STATUS.md](PROJECT_STATUS.md): o que a missão completa já tem de evidência e os gates ainda abertos.

## Executar no Windows

Abra PowerShell nesta pasta. Requer Python 3.11 ou mais recente; não há dependências Python externas para os experimentos.

```powershell
python -m unittest discover -s tests -q
python -m scripts.verify_sources
python -m scripts.result_compatibility
python -m scripts.result_compatibility --compare split_fast_v3_blade_effects_demo.json current_corridor_v1_hammer_effects_demo.json
python -m scripts.audit_split_fast
python -m scripts.audit_current_corridor
python -m scripts.audit_modular_lifecycle
python -m scripts.audit_current_results
python -m scripts.character_sheet duel --hero characters/victor_halle/rank3_2026-10-27_split_fast.json --opponent characters/examples/synthetic_rank4_split_fast.json --policy shield_blade_hammer_reactive --effect-limb 1 --seed 51 --output results/new_current_fast.json
python -m blacklight.experiment --historical-rules --stage dev --n 1000 --output results/reproduction_pool_v2_dev.json
python -m scripts.pool_v2_confirm --historical-rules --stage confirm_v2 --n 10000 --output results/reproduction_pool_v2_confirm.json
python -m scripts.pool_v2_confirm --historical-rules --stage holdout_v2 --n 10000 --output results/reproduction_pool_v2_holdout.json
python -m scripts.group_experiment --historical-rules --stage description --output results/reproduction_group_pool_v2.json
python -m scripts.focus_experiment --stage description --output results/reproduction_focus_pool_v2.json
python -m scripts.corridor_experiment --historical-rules --stage description --output results/reproduction_corridor_pool_v2.json
python -m scripts.replay --historical-rules --scenario mirror_hammer --strategy hammer --index 0 --output results\replay.json
```

As sementes são derivadas de SHA-256 de fase, cenário, política e índice. A reprodução depende também dos mesmos dados, parâmetros, implementação e versão de Python e demais dependências relevantes; sem essa condição, código e sementes iguais não garantem resultados idênticos. Os resultados de confirmação usam sementes diferentes das de desenvolvimento. `source_sha256` permite conferir as fontes declaradas, mas não garante que dependências externas transitivas tenham sido registradas.

As reproduções acima usam as mesmas sementes e não contam como amostras novas. Os destinos precisam ser novos; as saídas são criadas sem substituir arquivos existentes. Os estudos antigos de busca, sensibilidade, reserva, métricas secundárias e adversários exigem `--historical-rules --output CAMINHO_NOVO`. Para regenerar o relatório v2, escolha um novo destino com `python -m scripts.pool_v2_report --output CAMINHO_NOVO`. A auditoria de versões usa Git, além do Python. Antes de congelar uma execução nova, as fontes precisam estar em um commit, conforme [RESULT_VERSIONING.md](RESULT_VERSIONING.md).

A suíte inclui oráculos de dano, integração de duas armas, auditores de trilha, troca de fichas, [famílias modulares de cura/estado](MODULAR_STATES.md), [duração](MODULAR_LIFECYCLE.md) e proveniência; execute o comando acima para verificar a versão presente. A versão histórica `pool_v2` tem 52.000 duelos de desenvolvimento, 240.000 de replicação, 120.000 de reserva e 60.000 combates descritivos em cada extensão de grupo, Focus e corredor. A camada genérica de fichas tem um teste de integração com 1.000 duelos adicionais. [OPERACAO_FUNDACAO.md](OPERACAO_FUNDACAO.md) registra os limites da auditoria atual. Os PNG/SVG anteriores em `results/` são históricos e precisam ser refeitos para a nova regra.

## Leitura responsável

Vitória significa que o oponente foi incapacitado primeiro (Health abaixo de 1). Combate sem vencedor após 30 rodadas é inconclusivo, não vitória. As porcentagens estimam somente os cenários e políticas nomeados. Um resultado favorável não estabelece estratégia global para o jogo inteiro. A análise de sensibilidade mantém variantes de regra separadas do cenário principal.
