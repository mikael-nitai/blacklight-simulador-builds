# Lacuna identificada: reação Ram

Uma revisão adversarial independente, enquanto a reserva física estava em
execução, identificou uma opção que o motor de duelo atual não oferece. O Core
Rulebook fornecido, p. 31 impressa / p. 32 do PDF, apresenta **Ram** como reação
básica: depois de mover toda a velocidade em linha reta em direção a um alvo e
usar a ação padrão para movimento adicional até chegar a ele, o personagem pode
gastar uma reação para um ataque próximo. No acerto, sofre dano regular de
impacto e causa dano dobrado; num fantástico, continua sofrendo dano regular,
causa dano triplicado e derruba o alvo em Prone. A reação é opcional.

O texto equivalente consta no [compêndio Roll20: Reactions](https://roll20.net/compendium/marvel616/Reactions).
Não foi encontrado esclarecimento sobre Ram na [FAQ oficial de março de 2025](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20250327.pdf)
nem na [errata consultada](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Errata_20241220.pdf).
Uma atualização de playtest anterior não deve substituir o Core final da mesa.

## Consequência para o estudo

O runner físico atual não oferece Ram. A política de Victor também não pode
escolhê-lo. Uma trilha ilustrativa separada, seed 987654 no cenário sintético
de atirador em campo aberto, mostra Victor, na segunda rodada, mover-se de
distância 10 a 5 e gastar a ação padrão para aproximar-se de 5 a 1. Sob as
hipóteses da geometria unidimensional, isso aparenta satisfazer o gatilho de
movimento; ainda seria necessário verificar reação disponível e legalidade do
ataque. A trilha foi auditada pelo conjunto existente, que não testa Ram.

Logo, resultados dos atiradores caracterizam as políticas e as ações
implementadas; **não provam que Victor não tinha outra resposta legal na mesa**.
Os resultados anteriores e a reserva em andamento permanecem preservados com
seus contratos originais. Nenhuma taxa deve ser retroativamente reinterpretada
como se incluísse Ram. Um estudo com Ram exige fonte, mecanismo e sementes novos.

## Trabalho pendente antes de simular

**Esclarecimento posterior:** a [decisão da mesa sobre o dano de Ram](RAM_RULING.md)
confirma dados comuns de dano e redução individual para atacante e alvo. A
mesa também confirmou rolagens separadas para os dois participantes.

1. Rastrear deslocamento integral, direção, movimento adicional, chegada e
   disponibilidade de reação sem presumir linha reta em mapas mais gerais.
2. Verificar a natureza do ataque próximo e a interação com armas biológicas,
   efeitos especiais, Riposte, Escudo e a regra de dano com múltiplos dados.
3. Aplicar a decisão de redução individual e rolagens separadas e determinar a
   ordem dos dois danos. Não apresentar uma hipótese como esclarecimento
   oficial ou decisão da mesa.
4. Implementar e testar Prone e sua duração conforme o Core, ou impedir
   simulações que silenciosamente omitam o efeito fantástico.
5. Construir casos independentes para gatilhos válidos e inválidos, consumo de
   ação/reação, acerto, erro, fantástico, reduções e interações; depois executar
   testes de integração e replays antigos sem sobrescrever resultados.

Até esses pontos estarem resolvidos e verificados, Ram é uma lacuna registrada,
não uma habilidade implementada ou certificada.

## Primeiro componente experimental

`experimental/ram_trigger.py` verifica apenas uma hipótese conservadora de
gatilho em uma dimensão: duas aproximações consecutivas, mesma pessoa/alvo e
turno, primeiro deslocamento igual à velocidade, segundo pela ação padrão até
distância 1, e reação disponível. A continuidade reta e a ausência de
interrupção são pré-condições fornecidas pelo chamador; a função não as prova em
um mapa real. Os casos positivos e negativos estão em `tests/test_ram_trigger.py`.
O componente **não está ligado ao motor** e não resolve rolagem, dano, reações
aninhadas ou Prone. Ele não modifica os resultados em andamento.
