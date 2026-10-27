# Plano de validação independente — Blacklight

Estado: contrato e casos de referência. Este documento não certifica o motor nem autoriza experimentos de combate completo.

## Fontes usadas nesta validação

- *Marvel Multiverse Role-Playing Game: Core Rulebook*, arquivo fornecido pelo usuário, páginas impressas 12–15 (PDF 13–16): d616, resultado Fantastic, Ultimate Fantastic, edge e trouble.
- Mesmo livro, páginas impressas 33–34 (PDF 34–35): fórmula de dano, bônus de multiplicador não cumulativos, Fantastic damage e Damage Reduction (DR).
- Mesmo livro, página impressa 36 (PDF 37): armas de vários alvos, uma rolagem para todos e divisão do dano.
- [Compêndio Roll20, Fantastic Rolls](https://roll20.net/compendium/marvel616/Rules%3AFantastic%20Rolls?expansion=0) e [Dealing Damage](https://app.roll20.net/compendium/marvel616/Rules%3ADealing%20Damage), como conferência independente de transcrição.
- [FAQ oficial de 2024](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20241220.pdf): confirma o dobro de dano como padrão para Fantastic success salvo disposição expressa do poder.

## Referências matemáticas congeladas

Cada uma das 216 triplas ordenadas `(dado esquerdo, dado Marvel, dado direito)` tem probabilidade `1/216`. O dado Marvel com face 1 vale 6 e produz Fantastic. Portanto, há 36 Fantastic rolls (`1/6`) e um Ultimate Fantastic (`6,M,6`, `1/216`). A distribuição abaixo é uma referência congelada, independente da rotina de rolagem do motor. Foi calculada pela convolução de dois d6 comuns com as seis faces efetivas do dado Marvel `[6*,2,3,4,5,6]` (`*` = M):

| Total d616 | Contagem | Fantastic |
|---:|---:|---:|
| 4 | 1 | 0 |
| 5 | 3 | 0 |
| 6 | 6 | 0 |
| 7 | 10 | 0 |
| 8 | 16 | 1 |
| 9 | 22 | 2 |
| 10 | 26 | 3 |
| 11 | 28 | 4 |
| 12 | 28 | 5 |
| 13 | 26 | 6 |
| 14 | 20 | 5 |
| 15 | 14 | 4 |
| 16 | 9 | 3 |
| 17 | 5 | 2 |
| 18 | 2 | 1 |

Casos discriminantes de classificação:

| Dados | Modificador | TN | Resultado esperado |
|---|---:|---:|---|
| `1,M,1` | +1 | 10 | Fantastic failure; total 9 |
| `1,M,1` | +2 | 10 | Fantastic success; total 10 |
| `6,6,6` | 0 | 20 | Falha comum (total 18) |
| `6,M,6` | 0 | 20 | Ultimate Fantastic; sucesso automático |

Casos de dano da regra geral, sempre após acerto:

| Marvel | Rank | Ability | Bônus candidatos | DR | Fantastic | Dano | Razão |
|---:|---:|---:|---|---:|---|---:|---|
| 4 | 3 | +6 | `[3,2]` | 1 | não | 26 | `4 × (3 + max(3,2) − 1) + 6` |
| M | 3 | +6 | `[3,2]` | 1 | sim | 72 | `2 × [6 × (3 + 3 − 1) + 6]` |
| 6 | 3 | +6 | `[]` | 3 | sim | 0 | DR zera o multiplicador, inclusive Ability |
| 4 | 4 | +5 | `[4,1]` | 2 | não | 29 | Mighty supera arma; `(4+4−2)×4+5` |
| M | 4 | +3 | `[]` | 2 | sim | 30 | DR antes do dobro: `2×[(4−2)×6+3]` |

**Limite:** a ordem exata entre dividir dano de ataque de múltiplos alvos e aplicar o DR individual de cada alvo ainda não foi estabelecida com segurança a partir do trecho consultado. Deve ser registrada como variante ou esclarecida antes da implementação desses ataques. Não criar teste que pressuponha uma ordem sem fonte.

## ADEMP prévio aos resultados

**Aim.** Comparar políticas legais do Blacklight e detectar quais permanecem eficazes contra adversários competentes, preservando rastreabilidade de regras.

**Data-generating mechanism.** Somente mecânicas com fonte, versão e teste de referência aprovados entram no gerador de combates. Estados, ações legais, fonte de aleatoriedade e política de oponente têm versões registradas. Variantes de regra não se misturam.

**Estimands.** Probabilidade de vitória, derrota e inconclusão até horizonte fixo; diferenças de probabilidade entre políticas no mesmo cenário; dano efetivo até turnos 3/5/10 por combate inicialmente sorteado; Focus gasto e Health final. Sobrevivência condicional é relatório separado, nunca denominador oculto.

**Methods.** Baseline de ataque comum; políticas condicionais explicitadas antes da avaliação; cenários variando um fator de cada vez, mais bateria representativa reservada. Desenvolvimento e confirmação devem usar sementes, inimigos e configurações separados. Para comparar políticas com consumo diferente de sorteios, não chamar resultados de pareados apenas por compartilharem seed.

**Performance measures.** IC Wilson para proporções individuais; IC para diferença obtido de repetição independente ou pareamento válido por eventos exógenos identificados; erro-padrão Monte Carlo ou bootstrap por combate para médias e quantis. Reportar empates/inconclusões e censura explicitamente. Corrigir interpretação após seleção de muitas políticas: exploração escolhe candidatas, confirmação avalia hipóteses pré-registradas.

## Gates de fidelidade

1. **Dados e dano:** 216 triplas e tabela exata coincidem; casos extremos, Ultimate, edge/trouble, bônus não cumulativos, DR e dobro passam. Revisar logs de cálculos; nunca usar a função de produção para calcular o esperado.
2. **Duelo elementar:** invariantes de Health/Focus, turno, incapacitação, custos e ações legais passam; combate curto reproduz exatamente a mesma trilha com seed fixa.
3. **Poderes/armas:** um poder por vez, com casos positivos e negativos, origem da regra e restrição da Lâmina testadas. Não testar arma provisória como confirmada.
4. **Reações/tática:** fila de eventos, ordem de gatilhos, limites por rodada, condições, alcance e ausência de recursão infinita passam; logs completos revisados manualmente.
5. **Combates complexos:** adversários agem para vencer, existe política adversarial, cenários fora da distância ideal e confirmação em conjunto reservado; só então produzir recomendação comparativa.

Falha mecânica conhecida bloqueia o gate seguinte. Simulação impossível é falha de validação; não se descarta o combate silenciosamente. Cada execução registra hash de código/configuração, seed, fonte de regras, política e versão do Python.

## Testes adicionais exigidos antes de conclusão

- Edge: rerrolagem opcional, escolha de um dado pela política, retenção do melhor, múltiplas edges sequenciais; trouble: rerrolar dado de maior valor, M prioritário, manter pior; cancelamento um a um e exceção do Ultimate. Construir oráculos por sequências de faces fixas.
- Damage: casos acima, condições de tipo de dano, efeitos específicos que substituem o dobro, redução de condições e divisão multi-alvo quando a ordem estiver confirmada.
- Estado: ação após inconsciência, Focus insuficiente, reações excedentes, recuperação no timing correto, expiração de condições, gatilhos de Riposte e Fast Strikes, Lâmina somente em Fantastic success.
- Estatística: nenhuma política vê dados futuros; nenhum adversário muda regras; números de combates/denominadores preservados; logs amostrados recalculados por um verificador externo.

O arquivo `tests/test_reference.py` usa os valores congelados aqui. Passar seus testes prova apenas as primitivas cobertas, não a fidelidade do combate completo.
