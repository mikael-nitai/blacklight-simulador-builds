# Ataques entre participantes de um agarrão

O host `EntangledAttackDuel` expande o [duelo experimental de Grappling
Technique](GRAPPLING_EXPERIMENT.md) para permitir ataques corporais entre os
dois participantes do agarrão, incluindo armas e Fast Strikes da mesa atual.
A ficha de Crossbones continua parcial; esta extensão não é certificada e não
produz, por si, uma comparação de estratégias.

O Core Rulebook p. 30 / PDF p. 31 permite agarrar, detalha consequências de
ataques contra personagens enredados e impõe trouble nos testes Melee e
Agility de alguém Pinned. O texto não resolve claramente neste recorte se a
trouble de ataque contra os personagens enredados vale também quando o
atacante é um dos dois envolvidos. Por isso o host exige declarar uma das
duas hipóteses antes do combate:

1. `inside_attack_trouble=False`: sem essa trouble adicional entre os dois.
2. `inside_attack_trouble=True`: aplica uma trouble adicional ao atacar o
   outro envolvido.

Em ambas, o personagem Pinned recebe mais uma trouble nos seus testes Melee ou
Agility. Assim, na hipótese 2, um ataque de Victor Pinned recebe duas troubles;
as duas edges confirmadas para cada braço de Fast Strikes são preservadas.
Cada teste continua independente, e a escolha de efeitos continua anterior aos
dois testes. Nenhuma das hipóteses representa decisão já informada pelo mestre.

Não se resolve um possível **autoacerto** do atacante quando seu ataque erra;
esse redirecionamento é uma limitação assumida explicitamente nas duas variantes.
Não são implementados ataques de terceiros ao par, ataques à distância durante
o agarrão, carregar o outro, knockback durante o agarrão ou reações de
contra-ataque enquanto ambos continuam presos. O host também mantém o agarrão
quando o agarrador fica Stunned; essa é uma hipótese do modelo, não uma
determinação para todos os efeitos de incapacitação. Permanecem as limitações
do [host anterior](GRAPPLING_EXPERIMENT.md).

As políticas podem escolher atacar enquanto agarram ou estão agarradas, ou
continuar usando as escolhas existentes de Escape, espera e liberação. Um
auditor separado reconstrói a situação do agarrão, confere as troubles por
gatilho e as encaminha aos verificadores de dados, poderes, ações, dano,
Escudo e reações. Uma bateria de 50 sementes para cada hipótese reproduz e
audita os duelos, incluindo os dois braços, alvo Pinned e ataques do agarrador;
os testes adulteram marcadores e penalidades. Ela não é uma amostra destinada
a estimar eficácia ou decidir a regra ambígua.
Uma trilha individual auditada pode ser gerada em um destino novo com
`python -m scripts.entangled_attack_demo --output CAMINHO_NOVO`; ela ilustra
Victor Pinned atacando com Fast, sob a hipótese 2.
