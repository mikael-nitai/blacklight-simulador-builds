# Duelo experimental: Ram desarmado e Prone

`experimental/ram_prone_duel.py` combina o duelo unidimensional de Prone com a
detecção de Ram. Uma política explícita escolhe usar ou recusar Ram desarmado
na oportunidade. O golpe usa uma reação, faz um teste Melee, rola dano separado
para cada participante conforme [a decisão da mesa](RAM_RULING.md), aplica a
redução de cada um, e causa dobro ao alvo no acerto comum ou triplo em
fantástico. No fantástico, aplica Prone ao alvo se ele ainda não estiver caído.
O combate pode continuar, com a decisão de levantar custando uma casa de
movimento. Não usa Fast Strikes ou efeitos de arma no Ram.

O alvo pode ativar Escudo após o acerto e antes do dano; sua redução soma com
Sturdy. Em erro, a fila permite Riposte, inclusive reações posteriores dentro
dos orçamentos existentes. O limite Heroic do atacante sobre o dano ao alvo é
aplicado conforme o duelo físico atual. A política de Ram escolhida aqui não
seleciona knockback de Mighty; um Escudo ativo no atacante faz a política padrão
recusar Ram, sem presumir uma interação não decidida. Attack Stance ativo no
atacante é recusado. O dano dos dois participantes é simultâneo como hipótese
experimental; se o dano próprio incapacitar o atacante, a simulação é
interrompida em vez de adivinhar a ordem dos efeitos. Nenhum combate que falhe
deve ser descartado silenciosamente em uma futura bateria.

O host é **experimental** e não entra no runner certificado. Não implementa
Ram com armas biológicas, movimento dividido, rastejar, cobertura, Karma, Focus,
regras gerais de grupo ou todas as fichas. A falta dessas mecânicas impede usar
os exemplos desta etapa como conclusão global sobre Victor.

`experimental/ram_prone_audit.py` verifica a sequência, oportunidade, decisão,
teste, pools, reações, Escudo, reduções, Health e métricas. Para reutilizar os
auditores físicos já existentes, produz internamente uma projeção temporária
dos dois danos de Ram como eventos de Health; a trilha original é preservada e
os valores projetados são conferidos independentemente antes da projeção. O
auditor de Prone verifica o contexto de cada teste e a aplicação/remoção da
condição. A seed registrada é confrontada com a declarada; a repetição completa
é a verificação adicional da sequência pseudoaleatória.

Os testes em `tests/test_ram_prone_duel.py` incluem confrontos auditados com
acerto, erro, fantástico, Prone, Escudo, Riposte e Ripostes aninhados; custo de
levantar; limite Heroic; bloqueios; replay; e adulteração de eventos e métricas.
Esses testes não certificam todo o jogo nem substituem uma revisão adversarial
mais ampla das políticas e regras ausentes. Nenhuma taxa de vitória foi
produzida por esta etapa.
