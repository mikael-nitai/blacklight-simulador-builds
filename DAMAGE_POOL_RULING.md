# Decisão da mesa: dano como conjunto de d6

Consolidado em 27/10/2026. As fontes desta regra são as confirmações explícitas do usuário nesta conversa; as regras oficiais permanecem identificadas separadamente em [RULES_AUDIT.md](RULES_AUDIT.md). Os esclarecimentos sobre pools foram dados depois das baterias da fórmula escalar e antes dos experimentos `pool_v2`.

A mesa interpreta o multiplicador de dano N como **quantidade de dados d6 de dano lançados**. Todos esses dados usam a face Marvel: **cada face 1 vale 6**. Eles são independentes dos três dados do teste de acerto. O acerto continua sendo d616, com um dado Marvel distinguível e dois dados comuns, mais o atributo; uma face 1 em um dado de dano não cria um novo sucesso fantástico.

Para Victor Rank 3 com Mighty 3 e Melee 6, antes de DR:

| Ataque | Pool completo |
|---|---|
| Sem arma | `6d6+6` |
| Marreta | `8d6+6` |
| Lâmina ou Garra | `7d6+6` |

O +1 da Lâmina e da Garra soma com Mighty 3 de Victor por confirmação posterior; o +2 da Marreta além de Mighty já estava confirmado. Esses são efeitos de mesa, não uma alteração atribuída à regra geral de não acumulação do Core. Fora de Fast Strikes, um sucesso fantástico no teste de acerto **dobra o total de dano rolado, incluindo o bônus**.

**Balanceamento mais recente:** Fast Strikes agora faz um teste de acerto por braço, com duas edges dessas fontes em cada um. Antes do uso escolhe-se um braço/arma para efeitos; só ele pode aplicá-los, e os da outra arma ficam desativados. Erro, acerto comum e fantástico são resolvidos por braço. Isso revoga o contrato anterior de um único teste e efeitos das duas armas; ver HR-09 em [RULES_AUDIT.md](RULES_AUDIT.md).

**Ordem final confirmada:** resolver os dois testes juntos, antes de efeitos e reações, usando o estado anterior a eles. O Escudo defensivo pode ser ativado depois dos acertos e antes do dano. Resolver danos e efeitos permitidos dos dois braços antes de Riposte. Stunned da Marreta escolhida pode, portanto, impedir Riposte ao erro do outro braço; não altera o resultado do teste que já ocorreu.

A aritmética de dois componentes de dano no mesmo alvo, inclusive sem armas diferentes, permanece. Cada componente recebe sua própria DR antes de qualquer metade. No acerto comum, dividir **a quantidade de dados e o bônus par antes de rolar**, com piso na quantidade de dados. Se ambos os braços acertarem comum sem DR, Marreta + Lâmina usa `4d6+3 + 3d6+3 = 7d6+6`. O componente de um braço fantástico é integral, sem dobro genérico adicional; só se **ambos** forem fantásticos a soma sem DR será `8d6+6 + 7d6+6 = 15d6+12`. Se um braço errar, seu componente é zero. A metade de bônus ímpar continua sem decisão e é bloqueada.

**Confirmação posterior de fronteira:** se a DR ainda deixa N=1 num componente Fast comum, a metade reduz os dados a zero, mas o bônus original +6 é dividido para +3 e **sobrevive**: `0d6+3` causa 3 de dano, sem rolar faces de dano. Isso é diferente de a própria DR já deixar N≤0 antes da metade, caso em que o componente inteiro causa zero. A versão anterior estendia a política conservadora de pool vazio a ambos os casos; os resultados dessas versões continuam congelados, e uma execução corrigida precisa registrar suas fontes próprias. Essa confirmação é posterior ao [pré-registro v2](DAMAGE_POOL_V2_SPEC.md), que permanece como registro histórico do protocolo executado.

As faces concretas só determinam o total depois de lançadas. Por exemplo, **se todas as sete faces de dano do Fast comum forem 1**, o combo sem DR causa `4×6+3 + 3×6+3 = 48`; **se todas as quinze faces do fantástico forem 1**, causa `8×6+6 + 7×6+6 = 102`. O antigo exemplo `27+24=51`, baseado em multiplicar o valor de um único dado, não é um oráculo do procedimento literal atual.

Bleeding básico não é um bônus instantâneo adicional do ataque: causa 5 Health no fim de **cada turno da vítima**, até remoção, sujeito à DR aplicável a condições e sem acumular por reaplicação. Os efeitos das armas e a única ação extra da Lâmina no próprio turno continuam definidos em HR-01/02/03/06, agora limitados pelo seletor de HR-09 e [FAST_STRIKES_RULING.md](FAST_STRIKES_RULING.md). Escolher Marreta desativa Bleeding, membro e ação extra da Lâmina do outro braço.

A primitiva `blacklight/pool_damage.py`, os motores de duelo, grupo, Focus e corredor e seus auditores já receberam a regra literal. `blacklight/damage.py` conserva a fórmula escalar para referência; ela não descreve o dano dos experimentos `literal_marvel_pool_v2`. [POOL_V2_REPORT.md](POOL_V2_REPORT.md) reúne os experimentos v2; antes da etapa arquitetural em curso, a suíte completa tinha 176 testes aprovados. A correção de `0d6+3`, o novo contrato por braço e sua ordem final confirmada têm implementação em curso, incluindo `SplitFastDuel` e testes direcionados. Integração, auditoria independente e experimentos de versão própria continuam em andamento; os gates globais não estão concluídos. Os resultados `pool_v2` existentes passam a ser históricos quanto ao novo Fast, além do histórico escalar anterior. Não há certificação de todos os poderes ou de fichas oficiais completas. As taxas escalares, os manuais antigos e seus exemplos continuam históricos; as fontes de cada execução são preservadas conforme [RESULT_VERSIONING.md](RESULT_VERSIONING.md).
