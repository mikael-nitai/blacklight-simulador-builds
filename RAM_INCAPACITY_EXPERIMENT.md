# Ram: hipóteses de auto-incapacitação

O Core p. 33 impressa / p. 34 do PDF distingue Health abaixo de 1
(inconsciência) e Health no negativo do máximo (morte). O Core p. 102 / PDF
p. 103 diz que Healing Factor recupera Health no fim do turno; o texto não
exige consciência. O Core p. 36 / PDF p. 37 diz que a morte remove o personagem
de jogo e que poderes específicos podem restaurar a vida. O texto consultado
não resolve expressamente se o impacto sofrido pelo próprio atacante em Ram
pode ser letal. Em 29/10/2026 a mesa confirmou que, se o autoimpacto deixar
Victor inconsciente, ambos sofrem dano e o combate termina antes da cura. A
possibilidade de morte por autoimpacto permanece sem decisão; veja
[RAM_RULING.md](RAM_RULING.md).

O modo experimental `stop_before_heal_reject_lethal` aplica essa ordem ao
atacante explicitamente identificado como Victor. Os dois danos são aplicados;
se ele sobreviver inconsciente, o combate acaba antes de cura ou demais efeitos
de fim de turno. Se o cálculo alcançar o limiar de morte, ou se outro atacante
sofrer auto-incapacitação não esclarecida, a execução é interrompida sem
concluir o combate. O auditor confere o marcador, o encerramento imediato e a
ausência de cura. O executor ainda é experimental e não promove o cenário a
uma bateria estatística.

`experimental/ram_incapacity_duel.py` também preserva duas **hipóteses históricas opt-in**:

* `lethal_impact`: o auto-dano pode atingir o limiar de morte. Um personagem
  morto não executa efeitos de fim de turno neste recorte.
* `nonlethal_impact`: o auto-dano para um ponto antes da morte.

Em ambas as hipóteses históricas, o golpe aplica simultaneamente os danos calculados aos dois
participantes. Um atacante inconsciente, mas vivo, recebe os efeitos automáticos
de fim de turno antes de verificar o resultado; ele não pode realizar outras
ações enquanto estiver inconsciente. A hipótese usa a ordem já configurada de
Healing Factor e Bleeding. Essa variante experimental não é uma decisão da
mesa e agora **contraria a decisão de encerrar antes da cura**; não usar essas
hipóteses para novos resultados que aleguem representar a regra atual. Elas
servem apenas para reprodução histórica. O host original continua recusando
a auto-incapacitação e suas trilhas anteriores não são substituídas.

O auditor de Ram recebe explicitamente o modo e verifica o dano aplicado, o
estado, a sequência de morte e a ausência de efeitos posteriores de fim de
turno quando morto. Um auditor separado reconstrói o valor e a ordem de Healing
Factor e Bleeding no fim de cada turno, incluindo o bloqueio de cura depois da
morte; o próprio registro identifica a hipótese e a ordem de cura. O arquivo
`tests/test_ram_incapacity_duel.py` cobre morte, inconsciência
reversível pela cura, a hipótese não letal, dano simultâneo no alvo, reação,
adulterações e repetição. Um caso de dupla incapacitação muda de empate para
vitória conforme a hipótese e a cura automática, demonstrando por que esses
resultados não podem ser misturados. Não há bateria estatística ou certificação
para essas variantes.

A [comparação ilustrativa preservada](experimental_outputs/ram_self_incapacity_sensitivity_001.json)
usa a mesma seed `1` e os mesmos dados nas duas hipóteses, com dois personagens
sintéticos de Health máximo 1. Os dois recebem dano; a hipótese letal termina
em empate e a não letal permite que a cura automática deixe o atacante consciente,
resultando em vitória. As duas trilhas foram auditadas e reproduzidas byte a
byte. As fontes correspondem ao commit `f858a99` e o SHA-256 do arquivo é
`9748df88fb39addfd6878637e5388dc68ac3cc126a84559252ffd46e461a9fb4`.
Essa é uma comparação de fronteira, não uma estimativa de frequência nem uma
decisão sobre a mesa.

Uma [segunda versão da comparação](experimental_outputs/ram_self_incapacity_sensitivity_002.json)
acrescenta a auditoria independente dos efeitos automáticos de fim de turno.
Ela foi repetida byte a byte; suas fontes correspondem ao commit `a8362f1` e o
SHA-256 é `9cada6241c2ae60e2e76bec61a90ffc1f6a38bc37372cab56ff8763304fe9d63`.
A primeira versão continua preservada com suas fontes originais.
