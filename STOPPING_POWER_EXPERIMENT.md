# Stopping Power em confronto experimental

Fonte: Core Rulebook p. 121 impressa / PDF p. 122. O poder exige Rank 2 e
Double Tap, usa ação padrão e custa 5 Focus. Faz um ataque à distância; um
sucesso fantástico causa dano duplo e permite, à escolha do personagem, outro
ataque normal contra o mesmo alvo. O ataque adicional tem seu próprio teste;
ele não custa outra ação padrão nem outro pagamento do poder. As rolagens de
dano usam a convenção de dados Marvel confirmada pela mesa.

`experimental/stopping_duel.py` combina a opção com Double Tap, Slow-Motion
Dodge, submetralhadora, Fast Hands, Point-Blank Parry e as mecânicas físicas
do host anterior. A política escolhe se usa o poder e se aceita o ataque
adicional. O alvo pode ativar o Escudo após o acerto e antes do dano; se estiver
imune à munição, os disparos podem acertar sem causar dano. Por enquanto, o
host não oferece o ataque adicional contra um alvo inconsciente ou se o
atacante estiver incapacitado ou Stunned; essa é uma restrição conservadora,
não uma decisão atribuída à mesa.

`experimental/stopping_audit.py` verifica a declaração, o custo, os dois
testes, o alvo, a elegibilidade e a ordem das reações. Ele chama depois as
auditorias independentes de reação, armas e dano. O contador de ação padrão
recebe um opt-in separado para este poder: esse opt-in, isoladamente, não
verifica se o segundo ataque foi permitido e não deve ser usado sem a auditoria
específica. O modo padrão e o runner certificado continuam sem esse poder.

Testes incluem acerto comum, falha, sucesso fantástico, escolha de não dar o
segundo tiro, limite de Focus, Escudo imune à munição, alvo incapacitado,
contra-ataque Point-Blank Parry após um erro, falsificação da trilha e
equivalência de replay quando o poder está ausente. O recorte ampliado de
Crossbones já permite exercitar a técnica contra Victor, mas ainda omite outros
poderes e traços. Não é a ficha completa nem uma evidência de qual estratégia
vence a maioria dos confrontos.

O [combate ilustrativo completo](experimental_outputs/crossbones_stopping_victor_001.json)
usa a ficha atual de Victor, o recorte ampliado de Crossbones e a seed `30`.
Ele contém um ataque adicional de Stopping Power. A trilha foi auditada após a
leitura do arquivo e reproduzida byte a byte; as fontes correspondem ao commit
`61c7311` e o SHA-256 é
`e43a37309e7a40d00177b3c7fd6daab9e43a394695f422f476d5fe9cef9f2ec7`.
O exemplo foi selecionado para mostrar a mecânica; não é estimativa de vitória.
