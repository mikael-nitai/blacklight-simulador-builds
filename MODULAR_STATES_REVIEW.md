# Revisão independente: ações padrão de estado no motor modular

Escopo: revisão inicial e revalidação do snapshot corrigido de `combatants/actions.py`, `combatants/modular_duel.py`, `combatants/runner.py` e `tests/test_modular_states.py` em 2026-10-27. Produção e testes existentes não foram editados por esta revisão. O script `scripts/audit_modular_states.py` apenas lê os módulos e imprime um JSON de auditoria. **Estado atual: os dois achados abaixo foram corrigidos e revalidados.**

## Histórico dos achados no snapshot inicial

1. **Definição malformada aparecia como ação legal e falhava na execução.** No snapshot inicial, `StateActivation.__post_init__` aceitava `rules` em lista e `FocusSelfHeal.__post_init__` aceitava `cost_rules` em lista. Dois módulos sintéticos com `rules=['AUDIT-ONLY']` ou `cost_rules=['AUDIT-ONLY']` foram registrados e tiveram `Action('mode')`/`Action('heal2',5)` em `legal_actions()`. `_act()` recusou ambos sem alteração de Health, Focus, ação ou log. Os quatro módulos padrão usavam tuplas válidas.
2. **Pedido de custo zero com tipo inválido era aceito.** `Action('stance', 0.0)`, `Action('shield', 0.0)` e `Action('dodge', False)` comparavam iguais às ações canônicas de custo inteiro zero; `StateActivation.plan` devolvia `int 0`. Os três pedidos eram executados. Não havia gasto incorreto de Focus, mas a fronteira tipada era contornada.

## Revalidação após correção

- Os dois módulos sintéticos malformados são agora recusados no construtor ou registro, antes de `legal_actions()` (`actions.py` 108–115, 145–150).
- Os três pedidos com `0.0`/`False` continuam iguais por comparação Python às ações canônicas, mas `_act()` agora rejeita seus tipos antes de consultar a lista (`modular_duel.py` 65–68). Health, Focus, contador de gasto, disponibilidade da ação e log ficam inalterados.
- `runner.run_duel` e `run_batch` agora incluem `source_sha256` dos módulos `blacklight` e `combatants`, documentos normativos e arquivos das políticas, além de parâmetros completos das quatro definições em `registered_action_modules` (`runner.py` 24–53, 56–85, 88–143). O resultado também registra versão e implementação do Python, dependência apenas da biblioteca padrão no núcleo e o limite explícito de dependências transitivas de políticas externas. O script conferiu esses campos, hashes de cinco arquivos e parâmetros de cura/estado em ambos os retornos. O código compara o manifesto antes e depois da execução; esta revisão leu esse caminho, sem provocar alteração concorrente de arquivos para testá-lo.

## Evidência de equivalência e requisitos

| Verificação | Casos | Resultado |
|---|---:|---|
| Grade de legalidade (poder/arma, estados ativos, Focus -5/0/1/5/90, Health 0/100, stun e ação disponível) | 1.280 | Igual ao `Duel` congelado |
| Transições legais de stance, shield e dodge | 240 | Estado e log idênticos; Focus e contador de gasto inalterados |
| Requisito combinado power + trait + weapon | 8 | Disponível somente com os três presentes |
| Replays completos com políticas fixas, distâncias 1/5/12 e seeds 0–39 | 360 | `BattleResult` inteiro idêntico |
| `runner.run_duel` e `run_batch` com ficha sintética Rank 4 vs. Victor Rank 3 | 2 | Auditoria sem problemas; hashes e parâmetros dos quatro módulos presentes |

Os testes direcionados existentes também passaram: **36 testes** de `test_modular_states`, `test_modular_actions` e `test_character_sheets`.

## Comandos

```powershell
python -B -m scripts.audit_modular_states
python -B -m unittest tests.test_modular_states tests.test_modular_actions tests.test_character_sheets -q
```

O script imprime JSON e não cria resultados de experimentos. SHA-256 do **snapshot corrigido**:

| Arquivo | SHA-256 |
|---|---|
| `blacklight/engine.py` | `d77b89649bc897c9bf8c2ccccc4b4122aa08623c7dccf4080cf9c7e2fca9134b` |
| `combatants/actions.py` | `e6fd391755cdad6618cd1389938f844b35e8b3854d590510fc0f5db2071658a1` |
| `combatants/modular_duel.py` | `27de4c4f1ee3e3846bcdc4877e625442d8b46d3f1a99854e4474bddd0b4dd342` |
| `combatants/runner.py` | `55070655b5af64707d320c1eb1df5aa86f14824cc013f4f4e6d5867485b935a5` |
| `tests/test_modular_states.py` | `b8bdf2151555980f5ef026a7988fa7da93dda5bce44ee500c29bf0ded25bde86` |

## Limites

Reações, duração de estados e ataques continuam resolvidos pelo `Duel`; a igualdade demonstra preservação do comportamento atual, não correção independente das regras oficiais. A grade e os replays são finitos. A lacuna de proveniência específica apontada no snapshot inicial — falta de parâmetros das definições, hashes do código e versão do Python — foi fechada para os módulos e políticas abrangidos pelo manifesto. Dependências transitivas importadas por políticas externas ainda precisam de manifesto próprio, como o resultado agora declara; isso não afeta a equivalência mecânica aqui testada.
