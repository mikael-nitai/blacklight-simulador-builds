# Grappling Technique, Grabbed e Escape: transações experimentais

Esta etapa **ainda não integra o poder aos duelos nem ao recorte de Crossbones**.
São transações determinísticas para verificar a mecânica antes de conectar
movimento, poderes, dano, políticas e fila de reações. Não geram taxas de vitória.

## Fontes e contrato

- Core Rulebook, p. 101 impressa / p. 102 do PDF fornecido: Grappling Technique
  exige Rank 2, ação padrão e 5 Focus; ataque próximo bem-sucedido causa dano e
  agarra, com dano dobrado e Pinned em sucesso fantástico.
- Core, p. 30 / PDF p. 31: Grab, Escape, imobilidade dos envolvidos salvo quando
  conseguem carregar o outro, liberação pelo agarrador e penalidade de Pinned.
  Core p. 31 / PDF p. 32: Escape também pode ser reação quando ocorre o gatilho.
- Core, pp. 37–38 / PDF pp. 38–39: Grabbed e Pinned e limitações de movimento.
- Core, pp. 108–109 / PDF pp. 109–110: Mighty acrescenta seu nível aos testes
  Melee que não são ataques.
- [FAQ oficial de 27/03/2025](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20250327.pdf),
  pp. 4 e 6: testes que não são ataques diretos são não-combate; agarrar é
  ataque e não usa valores não-combate; não se usam duas reações no mesmo gatilho.
  A aplicação de Mighty à fuga é a interpretação dessas regras para Escape, não
  um bônus ao teste ofensivo de Grappling Technique. A restrição de Focus usa
  a regra existente do projeto: conservar pelo menos 1 ponto após o gasto.

`grappling_technique` recebe o acerto e o dano **já resolvidos por outra
camada**, gasta ação e Focus e registra as condições. Uma redução que zere o
dano não impede agarrar quando o teste teve sucesso; isso decorre do texto do
poder, que condiciona ambos os efeitos ao sucesso. O programa isolado não
calcula o dano nem certifica o acerto recebido. O exemplo hipotético de dano
zero é relevante para a proteção de Victor, mas não comprova que um combate
completo com Escudo já resolva esse encontro corretamente.

`escape` valida dados e rerrolagens, aplica Melee + nível de Mighty como
modificador e uma trouble se o alvo estiver Pinned. Um sucesso remove Grabbed
e Pinned. A reação consome uma reação ordinária; Fast Hands não serve para
Escape. O chamador fornece o identificador do gatilho e é responsável por
demonstrar que ele existe e se coincide com uma reação anterior. Em particular,
se ativar o Escudo e ser agarrado são o mesmo gatilho ou gatilhos distintos
precisa ser decidido no host sem presumir uma resposta da mesa.

Movimento dos dois envolvidos é bloqueado neste recorte; carregar o outro não
foi implementado e é rejeitado, não proibido pela regra do jogo. A liberação
voluntária exige um agarrador consciente e não Stunned neste protótipo. Não
há representação de múltiplos agarradores, incapacitação ou soltura automática,
alcance estendido, efeitos sobre armas, ataques de terceiros contra personagens
enredados, recursos de Focus especiais ou outras condições simultâneas. A
interação exata de Escudo, dano e evento de agarrar precisa de integração e
revisão; não se deve apresentar a função isolada como um simulador de combate.

Os testes cobrem ações inválidas, acertos e erros, dano zerado, custo, reações,
trocas de condição, auditoria independente das transições, todos os 216
resultados iniciais de um exemplo de fuga e os 1.296 pares de resultado inicial
e nova face em seu caso Pinned. Os auditores recebem fatos externos e não
validam a origem do acerto ou do dano por si mesmos.
