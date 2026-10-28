# Emenda antes da confirmação: controle com Marreta

Esta emenda foi feita **após observar o desenvolvimento**, por ter sido
identificada uma lacuna na comparação planejada, e **antes de executar ou
observar qualquer célula confirmatória**. Ela não altera as duas finalistas,
a ficha, os três cenários ou as políticas. O plano original permanece em
`CURRENT_DUEL_CONFIRM_SPEC.md`; esta emenda substitui os números de células e
comparações nos pontos abaixo.

Além de `bare`, incluir `hammer` como segundo controle. Assim, a confirmação
executa **quatro políticas × três cenários × 10.000 inícios = 120.000 inícios**,
com master seed 827104292 e auditoria de todos. `hammer` é Marreta comum com
Escudo reativo, como definida antes da exploração.

Predefinir uma família simultânea de **15 diferenças**: para cada cenário,
cada finalista contra `bare`, cada finalista contra `hammer`, e
`hammer_fast_hammer` menos `hammer_fast_blade`. Usar alpha `0,05/15` em todas
as comparações, com intervalo conservador Hoeffding/união e, em paralelo,
intervalo Newcombe/Wilson como aproximação. A garantia do limite conservador
depende do modelo de inícios independentes, não da mera diferença entre seeds.
Uma comparação fica sustentada nesse conjunto apenas se o intervalo
conservador ajustado excluir zero; saturação no controle pode impedir evidência
de melhora, mesmo quando ambas as políticas vencem quase sempre.

Antes de executar, derivar todas as seeds de confirmação a partir da identidade
pré-definida das células e verificar que não há repetição entre elas nem
interseção com as 15.000 seeds de desenvolvimento. A ausência de colisões não
prova independência estatística. Reserva/holdout continua intocada, e as
limitações mecânicas do plano anterior permanecem.
