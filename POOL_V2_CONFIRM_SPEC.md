# Seleção e reserva da versão de dano literal

Registrado em 27/10/2026 **depois** da bateria de desenvolvimento de 1000 duelos por célula e **antes** das baterias confirmatória e reservada v2. As dez políticas históricas e três novas foram executadas em quatro cenários sintéticos. Nenhuma taxa antiga de dano escalar é usada como evidência para a mesa atual.

Finalistas e controles fixados agora: `bare_attack`, `hammer`, `blade_hammer_fast`, `shield_blade_reactive`, `shield_hammer_reactive`, `shield_blade_hammer_reactive`. A última foi a maior taxa de vitória nos três cenários de contato no desenvolvimento; `blade_hammer_fast` isola o mesmo combo sem Escudo; `shield_blade_reactive` e `shield_hammer_reactive` isolam a escolha da arma; `hammer` e `bare_attack` são controles. `hammer_fast` e `claw_hammer_fast` foram exploradas no desenvolvimento, mas não escolhidas para a bateria maior. A seleção baseada no desenvolvimento não é uma descoberta confirmatória virgem nos mesmos quatro cenários.

**Replicação:** 10.000 duelos por finalista em cada cenário original (`mirror_attack`, `mirror_hammer`, `mirror_shield`, `gunner_kiter`), sementes `blacklight-pool-v2|confirm_v2|...`, separadas do desenvolvimento. Repetir todas as finalistas; relatar vitória, derrota, inconclusão e intervalos Wilson por célula. Não somar cenários em uma taxa global sem frequência de encontros conhecida.

**Reserva genuína da versão v2:** dois perfis sintéticos novos, nunca usados para escolher essas finalistas:

- `H1_rank4_bruiser`: Rank 4, Health 180, Focus 60, Melee 7, Agility 2, Resilience 6, Vigilance 3, defesas Melee 17/Agility 12, Run 5, Mighty com bônus de Melee 2, Marreta, política de ataque de Marreta, contato inicial 1.
- `H2_rank4_energy_kiter`: Rank 4, Health 120, Focus 60, Melee 3, Agility 7, Resilience 4, Vigilance 3, defesas 13/17, Run 6, ataque à distância de alcance normal 10 sem munição, política KITER, distância inicial 8. Sem cobertura ou limite de mapa.

Executar 10.000 duelos por finalista e perfil reservado, sementes `blacklight-pool-v2|holdout_v2|...`. As comparações são amostras Bernoulli independentes; a mesma fórmula de semente por política não implica emparelhamento de rolagens. Interpretar o atirador de campo aberto junto do corredor limitado, sem tomar nenhum dos dois como geometria universal. Critérios de robustez: vantagem consistente sobre controles nos cenários de contato, reconhecimento explícito de inconclusão/derrota contra kiter, nenhuma falha do auditor independente em trilhas selecionadas, e limites do motor declarados.
