# Double Tap e Slow-Motion Dodge em conjunto

O executor `experimental/ranged_powers_duel.py` combina os dois poderes com o
duelo experimental de Victor, mantendo o mesmo resolvedor de dano, Brawling,
Escudo, Fast Strikes, Prone e Ram. A reação Slow-Motion Dodge é decidida antes
do ataque e só se aplica se a defesa realmente testada for Agility. O uso da
reação impede o mesmo personagem de reagir novamente ao mesmo gatilho, conforme
FAQ e `ACT-03`; uma política que poupe a reação pode ativar o Escudo após o
acerto, antes do dano. O poder e as políticas continuam experimentais.

A auditoria independente confere a reação, a defesa, a associação ao ataque e
a soma de troubles de distância, Dodge, Prone e Slow-Motion Dodge. A rolagem
real e as rerrolagens não são substituídas na auditoria. Uma cópia do registro
sem o marcador novo é usada pelas auditorias anteriores, que recebem apenas
as contribuições de trouble já verificadas. Testes cobrem os dois poderes no
mesmo duelo, Prone, Brawling, Escudo e Fast de Victor, adulteração da trilha e
equivalência com o host anterior quando Slow-Motion Dodge está ausente. Há
também combate completo em que Ram causa Prone e as reações Slow-Motion Dodge
são auditadas no mesmo orçamento.

Esse host ainda não é a ficha completa de Crossbones. A transcrição conferida
visualmente da página oficial está em
`character_evidence/crossbones_core_p155.json`; ela preserva os traços,
poderes e valores impressos e não pode ser executada como ficha. A ficha nomeia
uma submetralhadora e a tabela de armas do Core p. 34 (PDF p. 35) lhe dá
alcance de 10 espaços e bônus +1 ao multiplicador, que não acumula com
Accuracy 2. A regra adicional do Core p. 36 (PDF p. 37) impõe trouble para
alvos a até 5 espaços. O host separado `experimental/smg_duel.py` acrescenta
essa trouble para **um alvo**, com declaração explícita do equipamento; ele
exige alcance 10, munição e bônus de dano já resolvido sem acúmulo. Sua
auditoria verifica a origem da trouble antes de executar as demais auditorias.
O uso de múltiplos alvos permanece pendente. O traço
impresso de Karma é mantido sem conversão e diversas habilidades continuam
pendentes. Nenhuma taxa de
vitória gerada com o subconjunto deve ser atribuída ao Crossbones completo.
