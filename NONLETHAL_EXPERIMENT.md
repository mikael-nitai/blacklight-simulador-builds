# Correção experimental: ataque desarmado não letal

Em resposta à [divergência encontrada](NONLETHAL_GAP.md),
`experimental/nonlethal_ram_duel.py` cria um host novo sobre o duelo
experimental de Ram e Prone. Para um atacante **não Heroic sem armas e sem
equipamento de ataque à distância no perfil**, ataques Melee desarmados e os
componentes desarmados de Fast Strikes recebem o limite não letal presumido
pelo Core p. 36: o Health do alvo não cai além de um ponto antes da morte.
Heroic continua seguindo o limite já existente no duelo. Ram desarmado tem sua
própria aplicação do limite no alvo, com ou sem Heroic.

O host não oferece uma declaração de ataque desarmado letal. Se um perfil não
Heroic com armas ou equipamento à distância tentar atacar desarmado, ele
interrompe a execução: a lista de equipamentos acessíveis não estabelece, por
si só, se o personagem está armado naquela situação. Essa restrição não é
uma afirmação de que tais ataques sejam proibidos pelas regras. Reações,
armas biológicas, decisão de letalidade e mais fichas exigem cobertura
específica antes de ampliar esse limite.

Quando o limite intervém, o motor experimental atualiza Health e métricas de
dano aplicado e registra, no evento do ataque, o Health calculado sem limite,
o limite e o dano impedido. A redução de dano continua calculada separadamente;
o dano evitado por não letalidade não é contado como Damage Reduction.
O host antigo e seus resultados permanecem intactos. Este host é experimental
e não pode ser usado pelo runner certificado nem por estudos estatísticos ainda.

`experimental/nonlethal_ram_audit.py` verifica o limite e seus registros com a
ficha original. Para reutilizar a verificação física existente, usa uma projeção
temporária que atribui o mesmo limite a perfis que não podem portar nenhuma arma
modelada; a ficha original não é alterada. A auditoria de Ram/Prone continua
verificando seus eventos e estados independentemente. Testes cobrem o exemplo
que antes ultrapassava a morte, Fast com dois braços, falta de declaração de
arma, adulterações e replays sem mudança, inclusive Victor contra o atirador
sintético. Esses testes não certificam todo o catálogo de ataques ou o RPG.
