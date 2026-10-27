# Revisão independente da primeira migração modular

Este relatório preserva o snapshot do commit `b1e4d19`. A revisão da evolução atual com estados está em [MODULAR_STATES_REVIEW.md](MODULAR_STATES_REVIEW.md).

**Escopo:** `combatants/actions.py` e `combatants/modular_duel.py`, migração de Do This All Day (ação padrão; Focus de 5 até `5 × Rank`, mantendo ao menos 1; cura 2 por Focus). O `blacklight/engine.py` foi tratado como referência congelada de equivalência, não como prova independente de correção das regras. Nenhum módulo de produção ou teste existente foi alterado nesta revisão.

## Resultado do snapshot revisado

Os quatro achados da revisão anterior foram revalidados como corrigidos:

1. `effects` gerador ou vazio é rejeitado antes de gastar ação/Focus (`modular_duel.py` linhas 85–90).
2. `legal_actions()` rejeita requests de outro `kind`, custo acima de `5 × Rank` ou sem Focus suficiente para deixar 1 (`modular_duel.py` linhas 25–36).
3. Request não hashable gera `IllegalAction` explícito, sem `TypeError` nem mutação (`modular_duel.py` linhas 27–36).
4. `cost_rules` exige tupla não vazia de strings não vazias; gerador vazio não gera mais evento sem regra (`modular_duel.py` linhas 75–84).

O script reproduzível [scripts/audit_modular_healing.py](scripts/audit_modular_healing.py) passou em:

| Verificação | Quantidade | Critério |
|---|---:|---|
| Grade de estados | 6.060 | `legal_actions` idênticas entre `Duel` e `ModularDuel` |
| Transições de cura | 55.760 | Estado do combatente e log idênticos |
| Duelos completos | 300 | `BattleResult` completo idêntico, incluindo métricas e log |
| Módulos malformados | 7 | `IllegalAction` sem alteração parcial de Health, Focus, ação ou log |

Os duelos de comparação usam as mesmas políticas fixas, distâncias iniciais 1/5/12, seeds 0–99, limite de 15 rodadas e `audit=True`. São replays de equivalência da refatoração, não uma nova avaliação estratégica.

## Comandos executados

```powershell
python -B -m scripts.audit_modular_healing
python -B -m unittest tests.test_modular_actions -v
```

O script terminou com `status: pass`. Os 10 testes de `test_modular_actions.py` passaram. O script imprime JSON e não grava resultados. Hashes SHA-256 dos arquivos de produção no snapshot examinado:

| Arquivo | SHA-256 |
|---|---|
| `blacklight/engine.py` | `d77b89649bc897c9bf8c2ccccc4b4122aa08623c7dccf4080cf9c7e2fca9134b` |
| `combatants/actions.py` | `12038c313381afceefe73ee43f51ca626f121b6dc4bb8512e88af3777da9de50` |
| `combatants/modular_duel.py` | `63da414053ed47112b40889b04e56727cdce59a0a69df69ab95310f9b9349f8e` |

## Limites

Somente a família de autocura paga com Focus foi migrada; os demais poderes e reações seguem no motor anterior. A igualdade com o motor congelado detecta regressões da migração, mas não demonstra que a regra original esteja correta. A grade finita e os 300 replays não cobrem todos os estados, políticas ou extensões futuras. `ActionPlan` ainda representa apenas `RestoreHealth`; novos tipos de efeito exigirão revisão própria antes de uso.
