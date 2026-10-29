# Blacklight Rank 3 — guia provisório para a mesa

Este guia reúne as decisões que você transmitiu para a ficha atual de Victor:
Health 150, Focus 90, Melee 6, Mighty 3 e Sturdy 1. **É provisório:** os
resultados de estratégia ainda não cobrem todas as situações e adversários.
O Chicote não está disponível neste Rank. A ficha impressa e o cálculo de Run e
iniciativa apresentam divergências registradas em [CHARACTER_AUDIT.md](CHARACTER_AUDIT.md).

## Prioridades de combate

1. Em alcance próximo, **Fast Strikes com Marreta e Lâmina, escolhendo os
   efeitos da Marreta**, é uma opção sustentada por dois confrontos de espelho
   sintéticos. Um fantástico do braço escolhido pode aplicar Stunned. Isso não
   estabelece que seja a melhor opção contra todos os inimigos: os testes ainda
   não incluíam Ram nem fichas oficiais completas.
2. Escolha **Lâmina** como fonte de efeitos quando Bleeding, o efeito em membro
   ou a chance de uma segunda ação com Lâmina forem mais importantes que o
   Stunned da Marreta. A escolha é feita antes dos dois testes.
3. Use o **Escudo** para proteger Health quando a ameaça justificar uma reação.
   Ele pode ser ativado após um ataque inimigo acertar e antes do dano, ou com
   uma reação ao fim do seu turno, mesmo depois de atacar. Fica ativo até você
   desativá-lo; desativá-lo é gratuito e necessário antes de usar Marreta ou
   Lâmina. Escudo não é uma arma de Fast Strikes.
4. Se um ataque próximo errar e você puder reagir, considere **Riposte**. Uma
   reação gasta não fica disponível para Escudo ou outra opção; não use duas
   reações no mesmo gatilho. O simulador usa duas por rodada com Combat Reflexes
   como interpretação conservadora, com a renovação registrada em
   [RULES_AUDIT.md](RULES_AUDIT.md).
5. Se precisar recuperar Health, **Do This All Day** usa ação padrão e pode
   gastar de 5 a 15 Focus no Rank 3, deixando ao menos 1 Focus. Recupera até
   2 Health por Focus gasto, sem ultrapassar o máximo. Healing Factor recupera
   até 5 Health no fim do turno conforme a regra aplicável, sujeito aos limites
   de morte e à decisão específica de Ram abaixo.

## Rolagens e dano

O teste de acerto usa os três dados d616, com o dado Marvel identificado;
some Melee +6 para ataques próximos. Um `1` no dado Marvel vale 6 e é uma
rolagem fantástica; ela ainda precisa ser um sucesso para gerar efeitos de
sucesso fantástico, salvo a regra própria do Ultimate Fantastic. Cada teste de
Fast Strikes recebe as **duas edges** confirmadas para Victor.

Na sua mesa, o número antes de `d6` é a quantidade literal de dados de dano;
em cada dado de dano, uma face `1` vale 6. Os dados de dano são independentes
dos dados do teste de acerto. Antes da redução de dano do alvo:

| Ataque | Dano em acerto comum | Sucesso fantástico |
|---|---|---|
| Desarmado | `6d6 + 6` | Dobra o total rolado, incluindo o +6. |
| Marreta | `8d6 + 6` | Dobra o total; pode aplicar Stunned. |
| Lâmina ou Garra | `7d6 + 6` | Dobra o total; efeitos conforme a arma. |

Em **Fast Strikes**, faça um teste por braço, podendo escolher um alvo para
cada um. Resolva os dois testes antes dos efeitos e reações. Escolha antes qual
braço aplicará seus efeitos; o outro causa dano se acertar, mas não aplica seus
efeitos de arma. Para Marreta + Lâmina, sem redução do alvo:

| Resultado de cada braço | Parcela da Marreta | Parcela da Lâmina |
|---|---:|---:|
| Erro | 0 | 0 |
| Acerto comum | `4d6 + 3` | `3d6 + 3` |
| Sucesso fantástico | `8d6 + 6` | `7d6 + 6` |

Some apenas as parcelas que acertarem o mesmo alvo. Por exemplo, dois acertos
comuns somam `7d6 + 6`; os valores exatos dependem dos dados lançados. Um
fantástico de um braço não muda o resultado do outro. Antes de dividir um
componente comum, reduza sua quantidade de dados pela DR daquele alvo e depois
arredonde a metade dos dados para baixo. Se a DR deixar apenas 1 dado, esse
componente comum causa `0d6 + 3`; se a própria DR zerar a quantidade antes da
metade, ele causa 0. O Escudo defensivo é resolvido após os testes e antes do
dano; os dois danos e efeitos são aplicados antes de Riposte.

Se a Lâmina for escolhida, um acerto aplica Bleeding sem acumular. O efeito
causa 5 de dano de Health no fim de cada turno da vítima, sujeito à redução
de dano aplicável a condições, até ser removido. Um fantástico do braço da
Lâmina no seu próprio turno pode conceder uma segunda ação com Lâmina; ela pode
usar Fast Strikes com novos testes. Fantástico em Riposte não concede essa ação.
Os detalhes mecânicos da inutilização ou perda de membro ainda precisam de
definição para simulações.

## Defesa e aproximação

O Escudo Rank 3 reduz em 2 o multiplicador de ataques Melee ou Agility que
causem **Health**, somando com Sturdy 1: redução total 3 quando ambos se
aplicam. Ele não reduz dano de Focus. A mesa confirmou imunidade a fogo e
munição; a classificação de ataques específicos pode precisar do mestre.

**Ram** é uma reação opcional após mover toda a velocidade em linha reta em
direção ao alvo e usar a ação padrão para movimento adicional até alcançá-lo.
Na regra comunicada para sua mesa, lance o dano do atacante e o do alvo
separadamente e aplique a redução de cada um: o atacante sofre dano regular e
o alvo sofre o dobro, ou o triplo em fantástico, que também aplica Prone. Se o
autoimpacto deixar Victor inconsciente, ambos recebem dano e o combate termina
antes da cura. A possibilidade de o autoimpacto matá-lo ainda não foi decidida;
também não presuma efeitos de armas biológicas no impacto sem decisão da mesa.

## O que os resultados atuais sustentam

A [reserva com 120.000 inícios](CURRENT_DUEL_HOLDOUT_REPORT.md) comparou quatro
políticas em três cenários sintéticos. Fast com efeito da Marreta superou a
Marreta comum no espelho com Lâmina; contra um atirador em campo aberto, muitas
lutas chegaram ao limite de rodadas sem vencedor. Esses resultados **não
incluíam Ram** e não representam adversários oficiais completos. Use-os como
indicação para testar escolhas, não como garantia para a mesa.

Fontes de decisões: [Fast Strikes](FAST_STRIKES_RULING.md),
[dados de dano](DAMAGE_POOL_RULING.md), [Escudo e Focus](FOCUS_RULING.md) e
[Ram](RAM_RULING.md). Este documento substitui o uso prático dos números do
[guia histórico](QUICK_REFERENCE.md), que pertencem a uma regra anterior.
