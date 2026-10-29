# Reações durante um agarrão: Riposte e Point-Blank Parry

O `EntangledReactionDuel` amplia o [duelo experimental de ataques durante
agarrão](ENTANGLED_ATTACK_EXPERIMENT.md): ambos os participantes podem escolher
Riposte ou Point-Blank Parry quando o gatilho, as capacidades, a distância e
os recursos permitirem. Um tiro de Point-Blank Parry é a única ação à distância
admitida enquanto o agarrão persiste neste recorte. A condição Pinned e a
hipótese de trouble por alvo enredado também afetam o teste da reação; a
trouble de curta distância da submetralhadora se soma quando aplicável.

Os dois testes e os dois danos/efeitos de Fast Strikes são concluídos antes de
responder aos erros, conforme a decisão da mesa. Uma reação criada por outra
reação é processada antes dos gatilhos anteriores que ainda estejam na fila;
cada processamento é registrado e auditado em ordem. Uma fonte inconsciente
não recebe um contra-ataque pendente neste host. A decisão de ativar Escudo e
sua imunidade à munição continuam sendo resolvidas antes do dano; o auditor
confere reações, Focus e fontes de trouble.

**Limites:** o possível autoacerto em ataques dentro de um agarrão continua
sem decisão de mesa e não é resolvido; o mesmo vale para o redirecionamento
contra terceiros, carregar o outro e knockback durante o agarrão. As duas
hipóteses para trouble ao atacar o outro participante permanecem separadas.
O Crossbones utilizado é incompleto. O host e as políticas não certificam
combate geral nem justificam uma taxa de vitória.

Os testes reproduzem e auditam 60 sementes para cada hipótese e observam tanto
Riposte quanto Point-Blank Parry dentro de um agarrão. Um caso **sintético**
com Point-Blank Parry, Fast Hands e arma de fogo acrescentados a Victor força
uma cadeia com dois erros de Fast e reações aninhadas: essa ficha alterada só
exercita a fila, não representa o personagem real. Falsificações da ordem e
da origem das reações são rejeitadas. Um exemplo separado com a ficha real de
Victor pode ser salvo em destino novo com
`python -m scripts.entangled_reaction_demo --output CAMINHO_NOVO`.
