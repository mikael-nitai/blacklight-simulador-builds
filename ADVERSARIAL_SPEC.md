# Stress tests adversariais adicionais

Registrados em 27/10/2026 **depois** da confirmação principal. São testes exploratórios de transporte, sem seleção de nova política. Políticas fixas: P1, P3, P8, P9, P10. Executar 5000 sementes independentes por célula, fase `adversarial`, 30 rodadas. Desfechos inconclusivos continuam separados das vitórias. Os três perfis são sintéticos e não alegam reproduzir personagens oficiais.

| ID | Alteração relevante | Política inimiga | Propósito |
|---|---|---|---|
| A1 `rank4_hammer` | Espelho S2 elevado de Rank 3 para Rank 4; atributos, Health, Focus e poderes mantidos. | Marreta | Verificar pressão de maior Rank sem mudar outro atributo. |
| A2 `rank2_brawler` | Rank 2, Melee 4, Agility 1, Resilience 3/Health 90, Vigilance 2/Focus 60, Run 5, sem powers/equipamento. | Ataque básico | Limite inferior de poder relativo em duelo simples. |
| A3 `rank4_nonammo_kiter` | S4 elevado de Rank 3 para Rank 4 e ataque ranged abstrato **não classificado como munição**; mesmos outros atributos/Health/Run. | Atirar e recuar; tratar Bleeding | Tentar quebrar a imunidade à munição do Escudo. É uma sonda mecânica, pois o poder/range que forneceria esse ataque não foi especificado numa ficha oficial. Não inferir legalidade de build ou frequência na campanha. |

A3 muda **Rank e tipo de ataque** e, por isso, não identifica isoladamente o efeito de cada fator. Serve como contramedida adversarial plausível dentro do motor, não como estimativa causal controlada. A1/A2 verificam variação de Rank com perfis coerentes nas defesas, Health e Focus derivados. `scripts/adversarial_scenarios.py` e o JSON de saída guardam hashes e perfis. Antes de uma recomendação geral, ainda faltam grupos, controle de Focus, mapa e inimigos oficiais.
