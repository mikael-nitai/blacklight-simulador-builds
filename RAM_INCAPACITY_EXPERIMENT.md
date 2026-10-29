# Ram: hipóteses de auto-incapacitação

O Core p. 33 impressa / p. 34 do PDF distingue Health abaixo de 1
(inconsciência) e Health no negativo do máximo (morte). O Core p. 102 / PDF
p. 103 diz que Healing Factor recupera Health no fim do turno; o texto não
exige consciência. O Core p. 36 / PDF p. 37 diz que a morte remove o personagem
de jogo e que poderes específicos podem restaurar a vida. O texto consultado
não resolve expressamente se o impacto sofrido pelo próprio atacante em Ram
pode ser letal nem a decisão da mesa sobre encerrar o combate antes da cura.
As perguntas foram encaminhadas ao usuário; não presumir que uma delas já foi
respondida.

`experimental/ram_incapacity_duel.py` oferece duas **hipóteses opt-in**:

* `lethal_impact`: o auto-dano pode atingir o limiar de morte. Um personagem
  morto não executa efeitos de fim de turno neste recorte.
* `nonlethal_impact`: o auto-dano para um ponto antes da morte.

Em ambas, o golpe aplica simultaneamente os danos calculados aos dois
participantes. Um atacante inconsciente, mas vivo, recebe os efeitos automáticos
de fim de turno antes de verificar o resultado; ele não pode realizar outras
ações enquanto estiver inconsciente. A hipótese usa a ordem já configurada de
Healing Factor e Bleeding. Isso é uma variante experimental, não uma decisão do
mestre nem garantia de resolução das regras. O host original continua recusando
a auto-incapacitação e suas trilhas anteriores não são substituídas.

O auditor de Ram recebe explicitamente o modo e verifica o dano aplicado, o
estado, a sequência de morte e a ausência de efeitos posteriores de fim de
turno quando morto. `tests/test_ram_incapacity_duel.py` cobre morte, inconsciência
reversível pela cura, a hipótese não letal, dano simultâneo no alvo, reação,
adulterações e repetição. Um caso de dupla incapacitação muda de empate para
vitória conforme a hipótese e a cura automática, demonstrando por que esses
resultados não podem ser misturados. Não há bateria estatística ou certificação
para essas variantes.
