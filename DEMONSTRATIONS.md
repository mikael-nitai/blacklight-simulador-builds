# Combates completos reproduzíveis

Os quatro exemplos abaixo foram escolhidos para mostrar transições distintas, **não** para estimar frequência. Cada JSON guarda os perfis e políticas iniciais, semente, todas as rolagens, movimentos, estados, alterações de Health/Focus, IDs das regras e auditoria aritmética. Todos passaram em `audit_log` sem divergências.

Para reproduzir, execute `python -m scripts.replay --scenario ID --strategy ID --index N --output results\replay.json` nesta pasta. O estágio padrão é `demo`; a fórmula da semente e os hashes de fontes estão no arquivo gerado.

| Exemplo | Configuração e semente | Eventos decisivos | Desfecho |
|---|---|---|---|
| [Marreta e rodada bônus](results/demo_mirror_hammer_0.json) | P3 contra S2, distância 1, seed `2973050510440785229` | Iniciativa fantástica de Victor abre rodada bônus. No evento 8, `6,M,2` vence defesa 16: `(6×(8−1)+6)×2 = 96` de dano e Stunned. O inimigo recupera a possibilidade de agir depois que a condição expira; ambos atacam na rodada 1. | Victor vence na rodada 2; Health final `121/−30`, Focus `90/90`. |
| [Lâmina + Marreta no Fast Strikes](results/demo_blade_bonus_1.json) | P4 contra S1, distância 1, seed `10674383309980768037` | No evento 30, `5,M,4` é acerto fantástico: `6×(8−1)+6 = 48` de dano integral de Fast Strikes, Bleeding e Stunned. O evento 31 concede uma única ação extra com Lâmina; o novo teste do evento 33, `6,3,6`, acerta e causa `ceil((3×7+6)/2)=14`. Um Riposte com Lâmina encerra o duelo no evento 73. | Victor vence na rodada 5; Health final `26/−30`, Focus `90/90`. A penalidade por membro inutilizado ainda não tem valor mecânico no modelo. |
| [Escudo ativado após acerto](results/demo_shield_reaction_0.json) | P8 contra S3, distância 1, seed `7382822477084913011` | O inimigo gasta reação no evento 7 e ativa Escudo no 8 **depois de saber que foi acertado**; o ataque 9 já usa DR `3` e causa `6×(8−3)+6=36`. Ao atacar, desativa gratuitamente no evento 14. Victor faz o mesmo nos eventos 15–16 antes de receber o ataque 18. | Victor vence na rodada 4; Health final `36/0`, Focus `90/90`. Não há Escudo em Fast Strikes. |
| [Atirador recuando](results/demo_gunner_stalemate_126.json) | P3 contra S4 sintético, distância 8, seed `15908668917959299003` | O inimigo atira e recua com Run 6; Victor tem Run 5 e usa movimento mais ação padrão para se aproximar, sem alcançar uma ação de ataque. Nas 30 rodadas, Victor não executa nenhum ataque Melee. | Inconclusivo no limite de 30 rodadas; Health final `14/120`, Focus `90/60`. Isso descreve apenas campo aberto sem obstáculos. |

O campo `outcome: "win"` nos JSONs indica que **alguém** venceu; consulte `winner` para identificar quem. `inconclusive` é censura no horizonte, nunca vitória automática.

O exemplo antigo de Escudo + Marreta em Fast Strikes foi arquivado em `results/invalid_pre_shield_action_demo_shield_duel_0.json` após a mesa esclarecer que o Escudo é uma ação defensiva separada. A trilha é reproduzível, mas sua política não é legal e não serve como demonstração de tática atual.
