# Resultados da versão de dano literal da mesa

27/10/2026. As tabelas desta versão usam vários dados Marvel de dano: cada face 1 vale 6. A replicação contém 240.000 duelos e a reserva 120.000, além de 52.000 duelos de desenvolvimento. Os resultados da fórmula anterior permanecem históricos em `results/legacy_scalar_v1/`.

Entre as políticas testadas, **Lâmina + Marreta em Fast Strikes com Escudo reativo** teve a maior taxa de vitória nos três cenários de contato da replicação e no combatente Rank 4 reservado. Isso sustenta uma recomendação condicional para contato. Contra o atirador de energia Rank 4 em campo aberto, essa mesma política perdeu 83,52% das lutas. Não foi estabelecida uma estratégia universal nem um resultado contra fichas oficiais completas.

## Método e regra usada

As seis finalistas foram escolhidas no desenvolvimento e fixadas em [POOL_V2_CONFIRM_SPEC.md](POOL_V2_CONFIRM_SPEC.md) antes da replicação e da reserva. Cada célula abaixo tem 10.000 sementes novas e independentes por política. Os quatro cenários da replicação já eram conhecidos; os dois perfis reservados foram definidos antes de observar seus resultados. Os adversários são sintéticos e usam políticas explícitas. As frequências dos encontros da campanha são desconhecidas, portanto não se calcula uma média global de vitória.

Marreta usa oito dados de dano antes de DR, Lâmina e Garra sete. Fast Strikes faz um teste com duas edges e aplica dois componentes. No acerto comum, DR reduz a quantidade de dados de cada componente antes da metade, com piso nos dados ímpares e metade do bônus +6. Sem DR, Lâmina + Marreta usa `3d6+3 + 4d6+3`; no fantástico usa `7d6+6 + 8d6+6`, sem dobro adicional. Um ataque normal fantástico dobra seu total rolado. Bleeding não acumula; o fantástico da Marreta aplica Stunned; o da Lâmina pode conceder apenas uma segunda ação no próprio turno, com nova rolagem. O Escudo é uma ação defensiva separada.

## Replicação e reserva

Taxas entre colchetes são intervalos Wilson de 95% por célula. Vitória exige incapacitar o adversário primeiro. Inconclusão após 30 rodadas e empate não contam como vitória.

| Cenário | Política | Vitória, IC 95% | Derrotas | Inconclusões | Empates |
|---|---|---:|---:|---:|---:|
| Espelho com ataque comum | Ataque sem arma | 50,06% [49,08%; 51,04%] | 4994 | 0 | 0 |
| Espelho com ataque comum | Marreta | 78,17% [77,35%; 78,97%] | 2183 | 0 | 0 |
| Espelho com ataque comum | Fast: Lâmina + Marreta | 89,81% [89,20%; 90,39%] | 1019 | 0 | 0 |
| Espelho com ataque comum | Fast: duas parcelas de Lâmina; Escudo por reação | 97,58% [97,26%; 97,86%] | 242 | 0 | 0 |
| Espelho com ataque comum | Marreta + Escudo reativo | 93,97% [93,49%; 94,42%] | 603 | 0 | 0 |
| Espelho com ataque comum | Fast: Lâmina + Marreta; Escudo por reação | 98,52% [98,26%; 98,74%] | 148 | 0 | 0 |
| Espelho com Marreta | Ataque sem arma | 22,82% [22,01%; 23,65%] | 7718 | 0 | 0 |
| Espelho com Marreta | Marreta | 49,93% [48,95%; 50,91%] | 5007 | 0 | 0 |
| Espelho com Marreta | Fast: Lâmina + Marreta | 67,85% [66,93%; 68,76%] | 3215 | 0 | 0 |
| Espelho com Marreta | Fast: duas parcelas de Lâmina; Escudo por reação | 70,20% [69,30%; 71,09%] | 2980 | 0 | 0 |
| Espelho com Marreta | Marreta + Escudo reativo | 64,57% [63,63%; 65,50%] | 3543 | 0 | 0 |
| Espelho com Marreta | Fast: Lâmina + Marreta; Escudo por reação | 78,74% [77,93%; 79,53%] | 2126 | 0 | 0 |
| Espelho com Marreta/Escudo | Ataque sem arma | 5,72% [5,28%; 6,19%] | 9428 | 0 | 0 |
| Espelho com Marreta/Escudo | Marreta | 36,25% [35,31%; 37,20%] | 6375 | 0 | 0 |
| Espelho com Marreta/Escudo | Fast: Lâmina + Marreta | 57,01% [56,04%; 57,98%] | 4299 | 0 | 0 |
| Espelho com Marreta/Escudo | Fast: duas parcelas de Lâmina; Escudo por reação | 54,59% [53,61%; 55,56%] | 4541 | 0 | 0 |
| Espelho com Marreta/Escudo | Marreta + Escudo reativo | 49,91% [48,93%; 50,89%] | 5009 | 0 | 0 |
| Espelho com Marreta/Escudo | Fast: Lâmina + Marreta; Escudo por reação | 70,43% [69,53%; 71,32%] | 2957 | 0 | 0 |
| Atirador com munição, campo aberto | Ataque sem arma | 0,00% [0,00%; 0,04%] | 9741 | 259 | 0 |
| Atirador com munição, campo aberto | Marreta | 4,52% [4,13%; 4,94%] | 9320 | 228 | 0 |
| Atirador com munição, campo aberto | Fast: Lâmina + Marreta | 8,75% [8,21%; 9,32%] | 8892 | 233 | 0 |
| Atirador com munição, campo aberto | Fast: duas parcelas de Lâmina; Escudo por reação | 4,00% [3,63%; 4,40%] | 0 | 9600 | 0 |
| Atirador com munição, campo aberto | Marreta + Escudo reativo | 4,20% [3,82%; 4,61%] | 0 | 9580 | 0 |
| Atirador com munição, campo aberto | Fast: Lâmina + Marreta; Escudo por reação | 8,59% [8,06%; 9,16%] | 0 | 9141 | 0 |
| Reserva: combatente Rank 4 | Ataque sem arma | 43,58% [42,61%; 44,55%] | 5642 | 0 | 0 |
| Reserva: combatente Rank 4 | Marreta | 67,78% [66,86%; 68,69%] | 3222 | 0 | 0 |
| Reserva: combatente Rank 4 | Fast: Lâmina + Marreta | 82,66% [81,91%; 83,39%] | 1695 | 0 | 39 |
| Reserva: combatente Rank 4 | Fast: duas parcelas de Lâmina; Escudo por reação | 87,30% [86,63%; 87,94%] | 1191 | 0 | 79 |
| Reserva: combatente Rank 4 | Marreta + Escudo reativo | 80,66% [79,87%; 81,42%] | 1934 | 0 | 0 |
| Reserva: combatente Rank 4 | Fast: Lâmina + Marreta; Escudo por reação | 91,49% [90,93%; 92,02%] | 834 | 0 | 17 |
| Reserva: atirador de energia Rank 4 | Ataque sem arma | 0,00% [0,00%; 0,04%] | 10000 | 0 | 0 |
| Reserva: atirador de energia Rank 4 | Marreta | 4,06% [3,69%; 4,46%] | 9594 | 0 | 0 |
| Reserva: atirador de energia Rank 4 | Fast: Lâmina + Marreta | 8,14% [7,62%; 8,69%] | 9186 | 0 | 0 |
| Reserva: atirador de energia Rank 4 | Fast: duas parcelas de Lâmina; Escudo por reação | 3,32% [2,99%; 3,69%] | 8676 | 992 | 0 |
| Reserva: atirador de energia Rank 4 | Marreta + Escudo reativo | 3,76% [3,40%; 4,15%] | 8751 | 873 | 0 |
| Reserva: atirador de energia Rank 4 | Fast: Lâmina + Marreta; Escudo por reação | 7,75% [7,24%; 8,29%] | 8352 | 873 | 0 |

A finalista com Escudo venceu 98,52%, 78,74% e 70,43% nos três espelhos de contato e 91,49% na reserva de contato Rank 4. Contra o atirador com munição, venceu 8,59%, teve zero derrotas observadas e 91,41% de inconclusões. Contra o atirador de energia reservado, venceu 7,75%, perdeu 83,52% e ficou inconclusiva em 8,73%. A imunidade à munição explica a sobrevivência no primeiro atirador; ela não resolve a necessidade de alcançá-lo.

## Comparações com controles

Diferenças de taxa de vitória da finalista com Escudo contra dois controles. Intervalos de diferença usam Wilson/Newcombe para amostras independentes e Bonferroni em uma família de 12 comparações (seis cenários × dois controles). Valores são pontos percentuais; a análise foi acrescentada após as contagens, portanto é uma comparação descritiva ajustada, sem uma nova alegação de pré-registro.

| Cenário | Contra | Diferença [intervalo simultâneo] |
|---|---|---:|
| Espelho com ataque comum | Marreta | +20,35 [+19,13; +21,60] |
| Espelho com ataque comum | Fast: Lâmina + Marreta | +8,71 [+7,79; +9,66] |
| Espelho com Marreta | Marreta | +28,81 [+26,94; +30,65] |
| Espelho com Marreta | Fast: Lâmina + Marreta | +10,89 [+9,11; +12,66] |
| Espelho com Marreta/Escudo | Marreta | +34,18 [+32,26; +36,06] |
| Espelho com Marreta/Escudo | Fast: Lâmina + Marreta | +13,42 [+11,48; +15,34] |
| Atirador com munição, campo aberto | Marreta | +4,07 [+3,07; +5,08] |
| Atirador com munição, campo aberto | Fast: Lâmina + Marreta | -0,16 [-1,30; +0,98] |
| Reserva: combatente Rank 4 | Marreta | +23,71 [+22,15; +25,26] |
| Reserva: combatente Rank 4 | Fast: Lâmina + Marreta | +8,83 [+7,48; +10,18] |
| Reserva: atirador de energia Rank 4 | Marreta | +3,69 [+2,74; +4,65] |
| Reserva: atirador de energia Rank 4 | Fast: Lâmina + Marreta | -0,39 [-1,49; +0,71] |

## Extensões descritivas

Estas baterias usam sementes novas e a mesma regra de dano, mas recortes próprios. São 60.000 combates em cada extensão. Há 600 trilhas completas auditadas em cada uma; não são encontros de campanha com todo o sistema implementado.

### Dois inimigos em contato fixo

G1 usa dois Rank 2 básicos; G2, dois Rank 3 básicos. Fast Strikes deste protótipo usa punhos, sem armas biológicas. A distribuição entre dois alvos é uma extensão conservadora descrita em [GROUP_POOL_V2_ADDENDUM.md](GROUP_POOL_V2_ADDENDUM.md).

| Cenário | Política | Vitória, IC 95% | Rodadas médias |
|---|---|---:|---:|
| G1_two_rank2_brawlers | group_hammer | 100,00% [99,96%; 100,00%] | 2.84 |
| G1_two_rank2_brawlers | group_hammer_shield | 100,00% [99,96%; 100,00%] | 2.99 |
| G1_two_rank2_brawlers | group_bare_fast | 100,00% [99,96%; 100,00%] | 2.71 |
| G2_two_rank3_brawlers | group_hammer | 96,85% [96,49%; 97,17%] | 5.30 |
| G2_two_rank3_brawlers | group_hammer_shield | 100,00% [99,96%; 100,00%] | 5.45 |
| G2_two_rank3_brawlers | group_bare_fast | 84,01% [83,28%; 84,72%] | 5.24 |

Zero derrotas observadas com Marreta/Escudo em G2 resulta do perfil dos inimigos: Rank 3 sem bônus de dano tem três dados, e Escudo + Sturdy reduzem três. Isso não demonstra invulnerabilidade contra um grupo com poderes variados.

### Mental Punch

A tabela usa apenas **F0**, a decisão válida de que Escudo reduz Health e não Focus. F2 permanece nos JSONs como contrafactual e não representa uma opção permitida da mesa. O inimigo permanece em contato e usa apenas Mental Punch.

| Perfil | Política | Vitória, IC 95% | Demoralized alguma vez |
|---|---|---:|---:|
| M3 | hammer | 98,50% [98,12%; 98,80%] | 10,78% |
| M3 | shield_reactive | 98,84% [98,50%; 99,10%] | 11,42% |
| M3 | shield_endturn | 99,08% [98,78%; 99,31%] | 11,42% |
| M4 | hammer | 96,28% [95,72%; 96,77%] | 18,86% |
| M4 | shield_reactive | 97,30% [96,81%; 97,71%] | 18,74% |
| M4 | shield_endturn | 96,50% [95,95%; 96,97%] | 19,26% |

### Atirador em corredor limitado

Comprimentos de 12 e 20 espaços, sem cobertura ou caminhos alternativos. C1 usa munição; C2 é Rank 4 sem munição. O atirador continua com sua política de recuo e encontra a parede. O forte resultado aqui e a falha no campo aberto mostram a dependência da geometria; o adversário não recebeu uma nova política adaptada à parede.

| Comprimento | Perfil | Política | Vitória, IC 95% |
|---:|---|---|---:|
| 12 | C1_rank3_ammo | hammer_attack | 100,00% [99,92%; 100,00%] |
| 12 | C1_rank3_ammo | shield_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 12 | C1_rank3_ammo | shield_blade_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 12 | C2_rank4_nonammo | hammer_attack | 99,98% [99,89%; 100,00%] |
| 12 | C2_rank4_nonammo | shield_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 12 | C2_rank4_nonammo | shield_blade_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 20 | C1_rank3_ammo | hammer_attack | 100,00% [99,92%; 100,00%] |
| 20 | C1_rank3_ammo | shield_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 20 | C1_rank3_ammo | shield_blade_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 20 | C2_rank4_nonammo | hammer_attack | 99,72% [99,53%; 99,83%] |
| 20 | C2_rank4_nonammo | shield_hammer_reactive | 100,00% [99,92%; 100,00%] |
| 20 | C2_rank4_nonammo | shield_blade_hammer_reactive | 100,00% [99,92%; 100,00%] |

## Auditoria e limites

O motor foi salvo no commit `dbce72f`. A camada genérica de fichas foi acrescentada em `3af6672`, preservando os replays anteriores. A suíte atual tem 119 testes aprovados. O teste cruzado recalcula 100 trilhas por célula de 13 políticas × quatro cenários. Os auditores recalculam dano pelas faces registradas sem importar a função de dano de produção. Os JSONs registram hashes, sementes e políticas; `python -m scripts.verify_sources` verifica suas fontes.

O contador de dano mitigado usa faces contrafactuais adicionais para estimar a diferença acoplada sem DR; esse valor não é dano efetivamente recebido. As rolagens de acerto e dano usam fontes aleatórias separadas. A recomendação acima se apoia em resultados de combate, e não em tratar mitigação amostrada como observação causal direta.

Permanecem pendentes: fichas oficiais completas, adversários com repertório mais amplo, Karma, concentração geral, controle e movimento compartilhados entre motores, grupos com posições próprias, penalidades numéricas de membros e todas as famílias de poderes/variantes. A [arquitetura de fichas](CHARACTER_PIPELINE.md) já permite importar e versionar novos dados, mas bloqueia mecânicas sem suporte antes de simular. O exemplo Rank 4 dessa arquitetura é sintético.

## Evidência e reprodução

- [Replicação](results/pool_v2_confirm_summary.json) e [reserva](results/pool_v2_holdout_summary.json).
- [Grupo](results/group_pool_v2_description_summary.json), [Focus](results/focus_pool_v2_description_summary.json) e [corredor](results/corridor_pool_v2_description_summary.json).
- [Vitória no contato reservado](results/pool_v2_demo_H1_fast_shield_0.json), [derrota para energia](results/pool_v2_demo_H2_fast_shield_0.json) e [inconclusão contra munição](results/pool_v2_demo_gunner_confirm_fast_shield_0.json).
- Gerar este relatório novamente: `python -m scripts.pool_v2_report`.
