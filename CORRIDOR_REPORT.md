# Corredor limitado contra o atirador que recua

**27/10/2026 — experimento exploratório.** Este estudo testa a dependência do resultado S4 de [campo aberto](REPORT.md) em relação à geometria. O [protocolo](CORRIDOR_SPEC.md) foi fixado antes das amostras. O corredor sintético é uma linha de células `0..12` ou `0..20`, sem cobertura, obstáculos intermediários ou passagem através de outro personagem. Victor começa em 0 e o atirador em 8. A política inimiga de S4 atira e tenta recuar, mesmo quando a parede torna o movimento nulo. O motor trunca o deslocamento à célula livre mais distante; esse comportamento **não representa um atirador que escolhe rotas alternativas ou usa a parede taticamente**.

**Baterias históricas:** as tabelas abaixo preservam o motor anterior. O corredor foi reexecutado com dano literal e uma terceira política de Lâmina + Marreta com Escudo reativo; o [relatório v2](POOL_V2_REPORT.md) é posterior a estas tabelas, mas também antecede o último balanceamento de Fast Strikes. Nenhuma dessas taxas mede o contrato atual.

C1 é o mesmo atirador sintético Rank 3 de munição do S4. C2 mantém seu perfil, mas sobe a Rank 4 e usa tiro não classificado como munição; é um teste adversarial de sensibilidade, **não** um personagem oficial. Victor usa Marreta sem Escudo (`hammer_attack`) ou Marreta com Escudo reativo (`shield_hammer_reactive`). São oito células, com 1000 lutas de desenvolvimento e 5000 novas por célula descritiva. O resultado `win`/`loss` na tabela é sempre da perspectiva de Victor; inconclusões e empates foram zero.

| Corredor | Atirador | Política de Victor | Vitórias / 5000 | IC Wilson 95% | Parede atingida | Contato corpo a corpo | Rodadas médias |
|---:|---|---|---:|---:|---:|---:|---:|
| 12 | C1 Rank 3, munição | Marreta | 4999; 99,98% | [99,89; 100,00]% | 4694 | 5000 | 3,25 |
| 12 | C1 Rank 3, munição | Marreta + Escudo | 5000; 100,00% | [99,92; 100,00]% | 4676 | 5000 | 3,25 |
| 12 | C2 Rank 4, sem munição | Marreta | 4990; 99,80% | [99,63; 99,89]% | 4711 | 5000 | 3,25 |
| 12 | C2 Rank 4, sem munição | Marreta + Escudo | 5000; 100,00% | [99,92; 100,00]% | 4667 | 5000 | 3,22 |
| 20 | C1 Rank 3, munição | Marreta | 4999; 99,98% | [99,89; 100,00]% | 4688 | 5000 | 4,76 |
| 20 | C1 Rank 3, munição | Marreta + Escudo | 5000; 100,00% | [99,92; 100,00]% | 4731 | 5000 | 4,79 |
| 20 | C2 Rank 4, sem munição | Marreta | 4947; 98,94% | [98,62; 99,19]% | 4679 | 5000 | 4,76 |
| 20 | C2 Rank 4, sem munição | Marreta + Escudo | 5000; 100,00% | [99,92; 100,00]% | 4680 | 5000 | 4,76 |

No S4 original, campo aberto infinito, `shield_hammer_reactive` venceu **6,7%** e muitas lutas ficaram inconclusivas até a rodada 30. No corredor de mesmo atirador C1, o contato ocorreu em **100%** das lutas e Victor venceu **100%** das 5000 com Escudo em cada comprimento. A diferença é consistente com a parede impedir o recuo indefinido; estes experimentos usam sementes independentes e **não** formam pares contrafactuais. A vitória de 5000/5000 ainda tem limite inferior Wilson de cerca de 99,92%, não prova chance verdadeira de 100%. O corredor mais longo adicionou aproximadamente 1,5 rodada até o desfecho. C2 mostra que remover a classificação de munição e elevar Rank permite algumas derrotas de Marreta; o Escudo reativo venceu as amostras C2, mas essa comparação não isola os dois fatores alterados entre C1 e C2.

## Validação e reprodução

Cinco testes de corredor verificam parede, distância, impossibilidade de cruzar personagens, rastreabilidade de movimento, rejeição de trilha espacial adulterada e interrupção diante de knockback não modelado; 400 lutas adicionais de teste foram auditadas integralmente. A suíte completa passou em **89 testes**. Na fase descritiva, **400 trilhas completas** (cada centésima de cada célula) passaram pelo auditor independente de rolagem, dano, Health, Focus, ações e reações do duelo e por um auditor separado de posições. Os [resultados de desenvolvimento](results/corridor_dev_summary.json) e [descritivos](results/corridor_description_summary.json) registram contagens, intervalos, perfis, políticas, sementes e hashes das fontes. Uma [vitória C1 com Escudo](results/corridor_demo_C1_shield_win_0.json) e uma [derrota C2 com Marreta](results/corridor_demo_C2_hammer_loss_91.json) apresentam combates completos, incluindo posições por movimento, rolagens e estados.

```powershell
python -m unittest discover -s tests -q
python -m scripts.corridor_experiment --stage dev
python -m scripts.corridor_experiment --stage description
python -m scripts.corridor_replay --length 20 --opponent C2_rank4_nonammo --policy hammer_attack --index 91 --output results/corridor_demo_C2_hammer_loss_91.json
```

O protótipo só admite uma dimensão, duas figuras e nenhum knockback; não calcula cobertura, linha de visão complexa, rotas, aliados ou objetivos de cenário. A política do atirador não é adaptada à parede e C2 não é perfil oficial. A inferência útil é **condicional**: quando o inimigo tem de permanecer em um corredor curto sem saída e apenas dispõe dessas ações, perseguir até a parede permite que Victor use sua superioridade em Melee. O estudo não demonstra uma taxa de vitória para corredores reais ou para atiradores capazes de escapar por outros meios.
