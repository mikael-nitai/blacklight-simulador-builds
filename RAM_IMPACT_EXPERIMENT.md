# Ram: hipóteses experimentais de dano de impacto

O trecho do Core sobre Ram distingue dano regular no atacante e dano dobrado
ou triplicado no alvo. O usuário confirmou que o cálculo usa os dados comuns de
dano da mesa e que cada participante subtrai sua própria redução; veja
[RAM_RULING.md](RAM_RULING.md). Ainda não ficou definido se os dois valores
compartilham uma rolagem, nem a aplicação de efeitos de armas biológicas.

`experimental/ram_impact.py` calcula dois cenários explícitos para investigação,
sem afirmar que qualquer um é a regra adotada:

* `shared`: atacante e alvo compartilham o mesmo pool integral de faces;
* `separate`: o impacto no atacante usa outro pool integral fornecido.

Em ambas as hipóteses, cada redução informada retira dados do respectivo pool
antes da multiplicação, os dados usam a regra de mesa em que face 1 vale 6,
e não há bônus de atributo se a redução eliminar todos os dados. Esse último
comportamento acompanha o modelo atual de ataque comum, não constitui uma
decisão específica do mestre sobre Ram. O dano regular do alvo é dobrado no
acerto comum ou triplicado no fantástico; o dano do atacante permanece regular.
O fantástico também sinaliza Prone. O cálculo recebe valores e faces já
definidos: não escolhe arma, custos ou dados; não aplica dano ao estado de um
combatente e não executa reações ou a condição Prone.

Exemplo verificável: seis dados com faces `1,2,3,4,5,6`, atributo `+6`, redução
do alvo `2` e redução do atacante `1`, no cenário `shared`. O dano regular do
alvo é `6+2+3+4+6 = 21` e o do atacante é `6+2+3+4+5+6 = 26`. Ram causa `42`
ao alvo em acerto comum, ou `63` em fantástico, e `26` ao atacante em ambos.
Esses números ilustram a hipótese experimental, não uma jogada aprovada para a
mesa. Os testes em `tests/test_ram_impact.py` cobrem esses casos, pools separados,
redução integral, erro e entradas inválidas.

Para integrar ao motor ainda é necessário decidir quais dados de base e quais
reduções se aplicam, ordenar danos e incapacidade, respeitar o limite Heroic,
conectar o gatilho e o gasto de reação, resolver interações com armas, Escudo,
Riposte e Prone, e revisar logs e testes de não regressão. Os resultados
históricos continuam usando seus contratos preservados.

## Transação isolada

`experimental/ram_transaction.py` combina o gatilho unidimensional com uma das
hipóteses de impacto em um estado sintético imutável. Gasta uma reação mesmo
quando o ataque erra, propõe simultaneamente as perdas de Health, preserva
Prone existente e aplica Prone no fantástico. Rejeita gatilho ausente, reação
indisponível, incapacidade prévia e dados inválidos. Os testes estão em
`tests/test_ram_transaction.py`.

O teste já recebe um resultado de ataque e as faces de dano; não rola dados nem
escolhe uma ação. O cálculo simultâneo é uma **hipótese**, não uma resolução
oficial da ordem entre danos e efeitos. Essa transação não inclui Heroic,
Escudo, Riposte, efeitos de armas ou outras condições, nem está integrada ao
motor. Não executar estudos de eficácia usando-a como combate completo.

`experimental/ram_record.py` registra essas entradas e saídas em uma estrutura
versionada. `experimental/ram_record_audit.py` verifica movimento, disponibilidade,
faces, reduções, dano, reação e estado final por aritmética própria, sem usar as
funções de resolução. A verificação enumerou as faces de dois dados em ambas as
hipóteses e rejeitou registros falsificados em
`tests/test_ram_record_audit.py`. Ela cobre somente a transação sintética, não
valida uma luta completa ou as interpretações ainda não decididas.
