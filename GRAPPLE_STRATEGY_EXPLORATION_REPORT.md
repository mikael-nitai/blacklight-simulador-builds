# Exploração: escapar ou atacar enquanto agarrado

O [protocolo pré-registrado](GRAPPLE_STRATEGY_EXPLORATION_SPEC.md) comparou
duas políticas de Victor com um recorte incompleto de Crossbones, começando a
um espaço de distância. Cada linha tem 1.000 inícios pareados; há duas hipóteses
para trouble ao atacar o outro envolvido e duas para a identidade do gatilho de
Escudo/Escape. **Essas hipóteses não são decisões da mesa.** Ram não foi usado.

| Política de Victor | Trouble entre envolvidos | Gatilho de Escape | Vitórias | Ao menos um agarrão | Fugas por reação | Fugas como ação | Ataques de Victor durante agarrão |
|---|---|---|---:|---:|---:|---:|---:|
| Escapar | Não | Mesmo ataque | 1.000 | 426 | 230 | 498 | 40 |
| Escapar | Não | Condição distinta | 1.000 | 426 | 578 | 4 | 0 |
| Escapar | Sim | Mesmo ataque | 1.000 | 426 | 233 | 505 | 53 |
| Escapar | Sim | Condição distinta | 1.000 | 426 | 578 | 4 | 1 |
| Atacar | Não | Mesmo ataque | 1.000 | 426 | 0 | 0 | 1.442 |
| Atacar | Não | Condição distinta | 1.000 | 426 | 0 | 0 | 1.442 |
| Atacar | Sim | Mesmo ataque | 1.000 | 426 | 0 | 0 | 1.601 |
| Atacar | Sim | Condição distinta | 1.000 | 426 | 0 | 0 | 1.601 |

Não houve derrotas, empates ou inconclusivos no limite de 30 rodadas. O
intervalo Wilson individual de 95% para vitória registrada é aproximadamente
99,62%–100% em cada célula. **A taxa de vitória não distingue as políticas
neste cenário** e não prova que ambas vençam todos os adversários. Os totais de
fugas e ataques contam eventos, não personagens distintos; um mesmo combate
pode ter vários agarrões e fugas. A política de escapar ainda pode realizar
ataques como reações, daí os números não nulos nessa coluna.

Os resultados são pouco discriminativos: o adversário tem apenas parte da
ficha oficial, enfrenta a imunidade do Escudo a munição e pode ter seu dano
corporal reduzido. O modelo não resolve autoacerto, ataques de terceiros,
carregar, knockback durante agarrão ou todos os poderes da ficha. Ele supõe
que o agarrão persiste se o agarrador ficar Stunned. A seleção de quem foi
agarrado é descritiva e não estabelece um efeito causal. Para buscar uma
recomendação prática é necessário testar adversários e cenários capazes de
ameaçar Victor, com a regra pendente da mesa e confirmação independente.

Cada duelo foi auditado; outra verificação conferiu identidade, sementes,
contagem, médias, intervalos e snapshots das fontes. Um replay fixo dos
índices 0, 500 e 999 de cada célula conferiu 24 registros. Essa amostragem não
é uma reprodução integral independente nem uma confirmação estatística.

- [Dados individuais](experimental_outputs/grapple_strategy_explore_v1.json):
  SHA-256 `ea3ae6b125b15bc640f1b5725e71e159935b10eebd1a864a1c716985b6bcbe28`.
- [Reprodução da amostra](experimental_outputs/grapple_strategy_explore_replay_v1.json):
  SHA-256 `9e1c8047d2f35b8a4a325cab6d7f33d5a51629e1089718e37a7927e57f2fe864`.
- Fontes congeladas no commit `6ec70bed1fab4a30f48a7a6a72c2079282b10337`;
  a versão de Python está registrada nos dados. Resultados históricos anteriores
  permanecem separados e a descrição incorreta herdada em dois exemplos
  anteriores está explicitada no protocolo.
