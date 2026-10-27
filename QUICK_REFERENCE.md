# Blacklight Rank 3 — consulta rápida na mesa

**Plano em duelo próximo:** ataque com **Marreta** (`Melee +6` contra defesa Melee). Depois, ative **Escudo** com uma reação ao fim do turno **ou** espere um ataque inimigo acertar e ative como reação antes do dano. O Escudo fica ativo até desativação gratuita. **Desative antes de usar Marreta ou Lâmina.** Escudo é defesa separada, nunca um braço de Fast Strikes.

| Decisão rápida | Ação |
|---|---|
| Alvo a 1 espaço | Marreta normal: `dM×8+6` antes da DR. Fantastic: dobro do dano e **Stunned**; se escolher knockback de Mighty no modelo, substitui o efeito especial. |
| Ataque próximo inimigo errou | Se houver reação e alcance, **Riposte** com arma legal. |
| Ataque inimigo acertou | Pode ativar Escudo com reação **agora**; a proteção já vale neste dano. |
| Escudo ativo | Melee/Agility inimigos: `−2 Escudo −1 Sturdy = −3` no multiplicador de dano. No Rank 3, imunidade a fogo e munição conforme a mesa. |
| Alvo longe | Movimento até 5 espaços; se ainda não alcançar, ação padrão pode virar outro movimento. Não há Extended Reach na ficha atual. |
| Faltam muitos Health e há segurança | Do This All Day: ação padrão, 5–15 Focus, mantém pelo menos 1; cura `2×Focus gasto`. Healing Factor recupera até 5 no fim do turno. |
| Inimigo recua continuamente | Evite perseguir indefinidamente em campo aberto. Busque terreno/objetivo/aliados; o simulador não testou essas saídas. |

**Lâmina + Marreta com Fast Strikes:** uma rolagem de acerto para a ação. Acerto comum causa **metade** do dano após DR, arredondada para cima. Fantastic causa dano **integral**, aplica Bleeding (não acumula), Stunned e o efeito de membro da Lâmina. O primeiro Fantastic **no próprio turno** dá uma segunda ação com Lâmina e **nova** rolagem; ela também pode ser Fast Strikes. Não há terceira ação, e Fantastic em Riposte não dá a segunda ação. Contra um alvo, um uso de Fast Strikes aplica dano uma vez.

**Reações:** duas por rodada com Combat Reflexes na interpretação conservadora do simulador, compartilhadas entre Escudo e Riposte; nunca duas no mesmo gatilho. O Core também menciona renovação no início do próximo turno, então confirme a contagem exata com o mestre se isso decidir a cena. Chicote indisponível no Rank 3.

## Roll'em no Discord

Envie **`3d6ns`** para mostrar três d6 na ordem, sem ordenar. Trate o **dado do meio** como dado Marvel: se sair `1`, ele vale **6** na soma e o teste é Fantastic. Depois some o atributo `+6` para Melee; compare com a defesa. O total automático do bot, se aparecer, **não** substitui essa conta, pois ele não identifica a face Marvel. Para edge/trouble, rerrole o dado escolhido com **`d6`** e aplique manualmente a regra de manter melhor/pior; não some uma edge como bônus fixo. Se o servidor exigir prefixo, a [documentação oficial](https://rollem.rocks/docs/prefix) aceita `r 3d6ns`. A sintaxe `3d6ns`, `d6` e operações aritméticas consta na [referência oficial V1](https://rollem.rocks/docs/v1-syntax). Não foi executado um teste na instância Discord da sua mesa.

**Fórmulas matemáticas, não comandos automáticos de d616:** Marreta contra DR 1: `dM×7+6`; contra Escudo ativo + Sturdy 1: `dM×5+6`. Um fantástico **normal** dobra o resultado todo. Em Fast Strikes fantástico, usa dano integral em vez do dobro. Substitua `dM` pelo dado Marvel do **mesmo teste**; a face `M` vale 6.
