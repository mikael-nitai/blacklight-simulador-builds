# Pré-registro: Victor, Ram e recorte parcial de Crossbones

Este protocolo é **exploratório**. Ele não é uma confirmação das baterias
anteriores, não usa Crossbones completo e não estabelece uma estratégia
globalmente ótima. O objetivo é verificar se a indicação anterior sobre arma
persiste em dois comportamentos explícitos de um adversário com parte da ficha
oficial, agora permitindo Ram de Victor.

## Cenários e políticas fixadas antes da execução

O adversário usa o recorte `build_crossbones_stopping_subset`: atributos da
página oficial, Accuracy 2, Double Tap, Slow-Motion Dodge, Fast Hands,
Point-Blank Parry, Stopping Power e submetralhadora contra um alvo. Outros
poderes, traços e tags permanecem omitidos e constam em cada resultado. O
host é `StoppingRamDuel`; o personagem coberto pelo encerramento antes da cura
é explicitamente Blacklight. Campo aberto unidimensional, distância inicial
10 espaços, limite de 30 rodadas, e ficha Rank 3 de Victor fornecida pelo usuário.

O adversário tem duas políticas: **estacionário**, que ataca e não se move; e
**recuo**, que busca manter distância e pode mover-se após atacar. Ambas
preferem Stopping Power quando legal, usam Point-Blank Parry quando apropriado,
e podem tratar Bleeding. São políticas simples, não adversários ótimos.

Victor usa uma de três políticas: Marreta comum; Fast Strikes Marreta + Lâmina
com efeitos da Marreta; ou a mesma combinação com efeitos da Lâmina. Cada uma
é executada com Ram permitido ou recusado. Todas usam Escudo reativo; a política
de Ram conserva o Escudo ativo e não executa Ram nessa condição. São assim
**12 células**, 1.000 inícios cada, com os mesmos 1.000 seeds pareados entre
as seis políticas de Victor dentro de cada cenário. Os seeds são calculados a
partir do identificador do cenário e do índice por SHA-256; cenários têm
domínios distintos. Não são amostras de confirmação ou reserva.

## Tratamento de resultados e limites

Cada combate concluído precisa passar pela auditoria independente do host antes
de ser contabilizado. Um Ram que alcance o limiar de morte por autoimpacto é
interrompido e registrado como **indeterminado por regra pendente**, com seed e
diagnóstico; não é descartado nem classificado como vitória, derrota ou empate.
Outras exceções interrompem a célula. O caso de auto-incapacitação não letal de
Victor segue a decisão da mesa: ambos recebem dano e o combate acaba antes da
cura. Inconclusivo ao limite de rodada é registrado separadamente.

Cada célula conserva os 1.000 registros individuais, seus seeds, resultados e
métricas básicas, sem substituir resultados históricos. A taxa observada de
vitória até o limite de rodadas é apresentada sobre **todos os inícios**, junto ao intervalo simples de
possibilidades entre `vitórias/N` e `(vitórias + indeterminados)/N`, que não é
intervalo de confiança estatística. O Wilson de 95% é calculado apenas como
intervalo binomial para o indicador observável de vitória registrada; ele não
resolve a regra pendente nem ajusta comparações múltiplas. Não selecionar uma
vencedora apenas por flutuações da amostra: resultados serão hipóteses para
testes adversariais e confirmação independente posterior.

Seeds e fontes são registrados com SHA-256 e commit imutável, e a execução usa
saída nova fora do inventário certificado. A implementação deve parar se o
total, a auditoria, a integridade das fontes ou o replay de uma célula falhar.
Não reproduzir silenciosamente as taxas antigas com a nova regra.

## Registro de execução interrompida

A primeira tentativa processou as 12 células e auditou os duelos concluídos,
mas a validação final recusou a estrutura do subconjunto: o objeto ainda tinha
conjuntos imutáveis em memória, enquanto o auditor exigia listas JSON. Nenhum
arquivo agregado ou taxa foi publicado ou inspecionado. O gerador foi corrigido
para validar a representação JSON efetiva antes de gravar; a execução deve ser
refeita com os mesmos seeds e com as fontes corrigidas. Essa tentativa é
exploratória e não deve ser apresentada como confirmação independente.
