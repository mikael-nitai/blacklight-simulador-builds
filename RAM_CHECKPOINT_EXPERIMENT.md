# Ram desarmado: ponto de interrupção em duelo experimental

`experimental/ram_checkpoint_duel.py` conecta o gatilho de movimento do duelo
unidimensional ao teste de acerto e ao cálculo de Ram da mesa. A política é
limitada a usar **uma reação desarmada na primeira oportunidade do personagem
selecionado**, sem executar Fast Strikes nem os efeitos de armas biológicas. Usa
o fluxo de dados do duelo, rola pools separados para atacante e alvo, aplica a
redução de cada um e registra o resultado em uma transação auditável.

O duelo é **interrompido na oportunidade** e o experimento termina imediatamente
após a reação; não se continua a luta, não se atualizam estatísticas completas
e não se calculam taxas de vitória. Prone fica registrado na transação quando
aplicável, mas não foi integrado à continuação de combate. O runner certificado
recusa esse host. O resultado é um checkpoint de engenharia, não um duelo completo.

O checkpoint exige trilha, reação disponível e estado inalterado entre detectar
e resolver. Rejeita explicitamente interações ainda não implementadas: Escudo
ativo no atacante ou alvo, Escudo ou Riposte disponíveis ao alvo, Attack Stance
do atacante, Dodge/Stunned do alvo, knockback escolhido por Mighty e dano que
exigiria o limite Heroic. Efeitos de armas, outros poderes que interfiram na
reação, movimento complexo, prioridades simultâneas e continuação de Prone
também estão fora do escopo. O dano aos dois participantes é aplicado de forma
simultânea **como hipótese experimental**, sem decidir a ordem definitiva em
casos onde um deles cai.

Perfis com poderes, traits ou armas fora do catálogo físico já conhecido são
recusados antes do duelo. A aceitação nesse recorte não certifica que a ficha é
uma construção legal do jogo nem que todos os efeitos futuros foram modelados.

`experimental/ram_checkpoint_audit.py` confere a trilha anterior com os
auditores físicos e espaciais existentes, verifica a oportunidade e reconstrói
independentemente os perfis, recursos, rolagens e efeitos da transação. A seed
registrada é confrontada com a seed declarada, mas isso por si só não prova que
o gerador a tenha usado: repetição integral continua necessária. Os testes em
`tests/test_ram_checkpoint_duel.py` abrangem acerto, erro, fantástico, rejeição
de interações não suportadas, adulteração, repetição e uma oportunidade da ficha
atual de Victor contra um atirador sintético.

Um [host experimental posterior](RAM_PRONE_EXPERIMENT.md) já conecta política,
continuação, Prone, parte das reações e Escudo no recorte de Ram desarmado.
Antes de um estudo tático, permanecem a auto-incapacitação, armas, escolhas de
Mighty e outras interações, além de um contrato de resultados separado. A
cobertura das fichas e demais regras continua limitada ao que seus adaptadores
efetivamente suportam.

## Demonstração com Victor

O [checkpoint preservado](experimental_outputs/ram_victor_checkpoint_001.json)
usa a ficha Rank 3 atual, um atirador sintético e a seed `987654`. Victor chega
ao alcance, acerta o Ram desarmado e gasta uma reação: o exemplo registra 66 de
dano no alvo e 27 em Victor, com pools separados e as reduções respectivas.
O Health passa de 150 para 123 em Victor e de 120 para 54 no alvo. A execução
para ali; não há vencedor nem conclusão sobre a campanha. A trilha, a auditoria
independente e os hashes de fonte foram conferidos, e uma segunda execução
produziu bytes idênticos. O SHA-256 do arquivo é
`d510aabc794bd1e0aa0ad15cdb74afc9d90882b4e72e4310133d06d91d45126e`;
as fontes foram vinculadas ao commit `a6f04bd`.
