# Primeira família de ações modularizada

27/10/2026. O executor de fichas genéricas passou a usar `combatants/modular_duel.py`. A primeira ação migrada é **Do This All Day**. O motor físico de referência em `blacklight/engine.py` permanece congelado, preservando os experimentos v2. A nova camada executa a mesma regra por um módulo reutilizável; as demais ações ainda passam pelo resolvedor anterior.

```mermaid
flowchart LR
    F[Ficha versionada] --> C[Catálogo de cobertura]
    C --> P[Política pede uma ação]
    P --> L[Motor valida turno e posse do poder]
    L --> D[Módulo define custo e efeitos]
    D --> V[Motor valida o plano inteiro]
    V --> E[Motor paga e aplica os efeitos]
    E --> A[Log e auditor independente]
```

O módulo recebe um contexto imutável com Rank, Health, Focus e poderes. Ele não recebe o estado mutável do combate nem os geradores de dados. A família `FocusSelfHeal` declara gasto mínimo, limite por Rank, reserva mínima de Focus, cura por ponto, IDs de regras e fontes. `DO_THIS_ALL_DAY` usa mínimo 5, limite `5×Rank`, reserva 1 e cura 2 por Focus, conforme Core p.94 e RES-01/POW-07 do registro de regras.

O motor controla a ação padrão, o personagem consciente e sem Stunned, a posse do poder, o limite geral de gasto e o saldo. Antes de qualquer pagamento, ele exige um plano tipado, uma tupla não vazia de efeitos reconhecidos e referências de regra válidas. Pedidos de outro tipo, custos ilegais, efeitos desconhecidos, geradores consumíveis e planos incompletos interrompem a execução antes de alterar Health, Focus, disponibilidade da ação ou log.

Uma nova habilidade da mesma família pode ser registrada como definição de regra, sem ramo por nome de personagem. Outros tipos de efeito, custos, alvos ou reações ainda precisam de uma família própria validada. O exemplo sintético usado no teste de extensibilidade existe apenas no teste; ele não foi cadastrado como poder do RPG.

## Evidência executada

- 129 testes da suíte passaram, incluindo dez testes da migração modular e os testes de fichas.
- 1.040 combates completos, em 13 políticas e quatro cenários, tiveram estados, métricas e logs idênticos entre o motor anterior e o modular.
- A [revisão independente](MODULAR_REVIEW_FINDINGS.md) comparou 6.060 estados de ações legais, 55.760 transições de cura e 300 replays adicionais. Seu [script](scripts/audit_modular_healing.py) é reproduzível.
- A revisão encontrou e fez reproduzir quatro falhas de extensão: gerador de efeitos consumido sem cura, custos ilegais anunciados como ações legais, erro de tipo em pedido não hashable e gasto registrado sem IDs de regras. As reproduções foram corrigidas e estão nos testes de regressão.
- A bateria de integração de outra ficha Rank 4 teve as mesmas contagens anteriores: 2 vitórias e 998 derrotas em 1.000 duelos, com dez trilhas completas auditadas. Isso demonstra equivalência da integração, não qualidade estratégica dessa ficha sintética.

O [exemplo completo de autocura](results/generic_sheet_modular_heal_demo.json) carrega a ficha atual de Victor e o oponente Rank 4 sintético, usa a política `hammer_heal`, semente 57 e registra `execution_adapter=modular_physical_duel_v1`. Ele inclui gastos de 15 Focus para recuperar até 30 Health; o último gasto é 14, deixando Focus 1 e recuperando 28 Health. O auditor de ledger e dano aprovou a trilha.

Reprodução:

```powershell
python -m unittest discover -s tests -q
python -B -m scripts.audit_modular_healing
python -m scripts.character_sheet duel --hero characters/victor_halle/rank3_2026-10-26.json --opponent characters/examples/synthetic_rank4.json --policy hammer_heal --opponent-policy attack --seed 57 --output results/generic_sheet_modular_heal_demo.json
python -m scripts.verify_sources
```

Igualdade com o motor de referência comprova a equivalência da refatoração nos casos executados. A correção normativa continua apoiada nas fontes e nos oráculos manuais de custo/cura; a equivalência não prova a correção de todos os poderes. Ainda faltam migrar ataques, efeitos de estado, condições, duração, alvos variados e gatilhos de reação para famílias comuns antes de ampliar o catálogo para fichas completas.
