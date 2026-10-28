# Exploração com as regras atuais de Fast Strikes

Esta etapa executou o [pré-registro](CURRENT_DUEL_STUDY_SPEC.md): 15 células,
1.000 inícios por célula, 15.000 combates ao todo. Todas as trilhas foram
auditadas durante a execução; os resultados guardam cada semente e métricas
por início, mas não as 15.000 trilhas completas. Os 15 JSONs foram congelados
ao commit de fontes `0e9f307`; o verificador conferiu os 52 resultados do
inventário sem divergências. A seleção foi calculada depois do congelamento
com código registrado em `7dc7149`.

## Vitória por cenário e política

Valores são vitórias em 1.000 inícios, não probabilidades para a campanha.
Não houve empates ou combates inconclusivos nessas células. O espelho é uma
hipótese sintética que recebe as mesmas armas biológicas de Victor; os demais
oponentes também são sintéticos, sem certificação de build completa.

| Política | Espelho em contato | Rank 4 físico | Atirador no corredor |
|---|---:|---:|---:|
| Desarmado, Escudo reativo | 5,3% | 92,3% | 100,0% |
| Marreta comum, Escudo reativo | 37,9% | 99,0% | 100,0% |
| Fast Marreta + Lâmina, efeitos da Marreta | **51,9%** | 99,8% | 100,0% |
| Fast Marreta + Lâmina, efeitos da Lâmina | **46,0%** | 99,6% | 100,0% |
| Fast Lâmina + Marreta, efeitos da Lâmina | 42,4% | 99,8% | 100,0% |

Conforme a regra predefinida de maior taxa no pior cenário, as finalistas são
`hammer_fast_hammer` e `hammer_fast_blade`. O controle `bare` acompanha ambas
na confirmação; não foi elegível para as duas vagas. Na exploração, o pior
cenário das duas finalistas foi o espelho. Seus intervalos Wilson individuais
de 95% nesse cenário foram aproximadamente **48,8%–55,0%** e **42,9%–49,1%**,
respectivamente. Esses intervalos individuais não corrigem a seleção de cinco
políticas e não são uma prova confirmatória da diferença entre elas.

No cenário do atirador, 1.000 vitórias em 1.000 não provam probabilidade de
100%: o limite inferior Wilson individual é aproximadamente 99,62%. O corredor,
as políticas e o ataque não classificado como munição definem esse resultado;
ele não demonstra o desempenho de Victor em campo aberto, contra fogo, Focus,
outros atiradores ou adversários com fichas completas.

Para dar contexto às contagens, contra o espelho a primeira finalista registrou
em média 1,69 aplicações de Stunned por início e nenhuma ação extra da Lâmina;
a segunda registrou 0,09 Stunned e 0,94 ação extra da Lâmina por início.
Stunned também pode vir da Marreta usada em Riposte. São médias descritivas
nos confrontos completos, não prova isolada da causa da diferença de vitórias.
As políticas testadas não usam cura voluntária, portanto o Focus gasto médio foi
zero; isso não avalia o valor de Do This All Day.

## Próxima verificação

Confirmação e reserva ainda **não foram executadas**. As duas finalistas e o
controle devem ser testados com sementes distintas conforme o pré-registro,
sem alterar a seleção depois de observar a confirmação. A comparação incluirá
intervalos para diferenças e a multiplicidade declarada. Continuam faltando
adversários oficiais completos, dano de Focus, Karma, mais táticas de inimigos,
grupos validados e mapas menos restritos. Portanto, esta exploração não autoriza
chamar uma dessas políticas de estratégia mais forte em geral.

O registro de seleção [development_selection_v1.json](experiments/current_duel_study/development_selection_v1.json)
contém as 15 contagens, intervalos, métricas e hashes de entrada. Seu SHA-256 é
`87fec028587c5c18ce4a7f55f4a45b3bc282f34241d18d9f4e55f00f23dc4529`;
os 17 hashes de resultados, especificação e seletor coincidem com o commit
`7dc7149`.
