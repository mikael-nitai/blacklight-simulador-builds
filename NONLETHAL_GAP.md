# Lacuna identificada: ataque desarmado não letal

O Core Rulebook fornecido, p. 36 impressa / p. 37 do PDF, estabelece que
ataques de personagens desarmados são presumidos não letais, salvo declaração
contrária. Nesse caso o dano ao alvo para um ponto antes da morte. A regra de
Heroic da p. 34 é adicional e não limita essa presunção a personagens Heroic.

Na revisão de 29/10/2026, o duelo físico `split_fast_v3` em
`blacklight/engine.py` limita o Health do alvo apenas quando o atacante tem a
tag Heroic. Um atacante **não Heroic e desarmado** pode levar o alvo abaixo do
limite de morte sem declarar letalidade. O caso abaixo reproduz o problema no
commit `cbd611a`: atacante Rank 3, Melee 4, alvo com Health máximo 1, ambos sem
armas e sem Heroic, distância 1 e seed `1`; a trilha registra Health final
`-19` no alvo, embora a presunção não letal pare em `0`. Ambos os valores são
inconscientes, portanto **essa reprodução não demonstra uma mudança no vencedor**;
ela demonstra um erro de Health/morte que pode afetar outros recortes.

Reprodução em uma cópia do commit indicado, a partir da raiz do projeto:

```python
from tests.test_ram_checkpoint_duel import profile, StationaryPolicy
from combatants.actions import DEFAULT_ACTIONS
from combatants.split_fast import SplitFastDuel, SplitFastPolicy

attacker = profile('Attacker', 4, health=100, initiative=100)
target = profile('Target', 2, health=1)
policies = (SplitFastPolicy('attacker'), StationaryPolicy('stationary', always_wait=True))
duel = SplitFastDuel((attacker, target), policies, seed=1, initial_distance=1,
                     max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
print(duel.run().final_health)  # (100, -19)
```

Essa descoberta posterior limita a certificação anterior no que diz respeito
à letalidade dos ataques desarmados não Heroic. As trilhas e os resultados
históricos permanecem ligados às versões de fontes com que foram produzidos;
nenhuma estimativa é corrigida retroativamente. A ficha atual de Victor tem
Heroic, mas isso não corrige automaticamente todos os ataques dos oponentes.
O uso de armas biológicas e a intenção letal exigem decisões explícitas em
vez de classificações inventadas.

No novo duelo **experimental** de Ram, apenas Ram desarmado sem declaração
letal recebeu o limite não letal no **alvo**, inclusive para atacante não
Heroic; há testes para os dois casos. O checkpoint anterior bloqueia esse
limite em vez de resolvê-lo incorretamente. A regra de auto-dano do atacante
de Ram é uma questão separada e não deve receber o limite de alvo sem suporte.
Um [host experimental separado](NONLETHAL_EXPERIMENT.md) também aplica o
limite a ataques desarmados de perfis claramente sem armas e verifica Fast
Strikes; casos ambíguos são bloqueados. O motor de duelo físico geral ainda
precisa de solução versionada, auditoria de mais tipos de ataque, testes de
interação e replays antes de qualquer promoção dessa correção.
