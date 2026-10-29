# Revisão adversarial independente — política física atual

Revisão independente em memória sobre o commit `4c9a5df`, sem consultar a
reserva em execução. Uma hipótese de atirador mais preciso em campo aberto
reduziu bastante as vitórias de Victor no motor existente: **15/400** para
`hammer_fast_hammer` e **16/400** para `hammer`. Todos os combates foram
auditados na execução, mas os agregados e trilhas desses lotes **não foram
salvos**. As amostras são exploratórias, com seeds diferentes por política;
não demonstram superioridade estatística entre as duas nem resultado geral.

O adversário é sintético, baseado no arquivo
`characters/examples/synthetic_rank4_nonammo_gunner.json`, SHA-256
`954c9d94829458d006b9c3b855587f56772559aaf0f3267a9f0042b4a9e803da`, com
Accuracy 3 adicionada, alcance 10 e ataque genérico não classificado como
munição. Rank 4 satisfaz o pré-requisito de Rank de Accuracy 3 no Core p. 82
(PDF p. 83), mas origem, orçamento de poderes e equipamento da ficha completa
não foram certificados. Não é ficha oficial nem um poder Elemental Burst
completo; esse poder tem um efeito adicional fantástico não modelado aqui.

O resultado também reflete a ausência da reação básica Ram: veja
[RAM_REVIEW.md](RAM_REVIEW.md). Na trilha individual seed `987156`, Victor
aparentemente chegou ao gatilho de Ram na segunda rodada, mas essa escolha não
estava disponível. Portanto, os números não provam que o atirador impeça uma
resposta legal na mesa. Campo aberto em uma dimensão, ausência de obstáculos e
uma única política de perseguição são limitações adicionais. Antes de usar essa
hipótese em recomendação, é preciso resolver Ram e registrar outro experimento.

O seguinte reproduz a construção e os parâmetros relatados; o código identifica
separadamente o adversário e não substitui fontes ou resultados anteriores:

```python
from scripts.current_study_dev import configurations, INPUTS
from combatants.sheets import sheet_record, parse_sheet
from combatants.runner import run_batch
from combatants.split_fast import SplitFastPolicy
from blacklight.batch_audit import audit_batch_metadata

hero, policies, scenarios = configurations(tuple(p.read_bytes() for p in INPUTS))
gunner = sheet_record(scenarios['gunner_corridor'][0])
gunner['id'] = 'redteam_rank4_accuracy3_gunner'
gunner['revision'] = 'adversarial-memory-only-v1'
gunner['name'] = 'Red-team synthetic gunner'
gunner['features'].append({'id': 'accuracy', 'kind': 'power', 'level': 3,
                           'parameters': {},
                           'sources': ['Adversarial synthetic countermeasure, build legality pending']})
gunner['notes'].append('Synthetic model; character creation legality and equipment provenance not certified.')
opponent = parse_sheet(gunner)
foe = SplitFastPolicy('redteam_kiter_accuracy3', kite=True, move_after_attack=True,
                      treat_bleeding=True, riposte=False, knockback_stance=False)
for name in ('hammer_fast_hammer', 'hammer'):
    result = run_batch(hero, opponent, policies[name], foe, n=400,
                       master_seed=665411901, initial_distance=8,
                       max_rounds=30, audit_every=1, extended_metrics=True)
    issues = audit_batch_metadata(result)
    if issues:
        raise RuntimeError(issues)
    print(name, result['outcomes'])
```

Para conferir a trilha individual, usar a mesma construção e chamar `run_duel`
com `seed=987156`, `initial_distance=8` e `max_rounds=30`. Uma reprodução deve
usar as fontes do commit indicado e verificar seus hashes; o bloco acima não
é, por si só, um arquivo de resultados congelado.
