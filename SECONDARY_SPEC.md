# Métricas suplementares registradas antes da execução

Após a exploração e durante a confirmação principal, escolhemos cinco políticas já fixas: P1 ataque básico, P3 Marreta, P8 Escudo reativo + Marreta, P9 Marreta + cura t75/s15 e P10 Escudo no fim do turno + Marreta. Nenhuma política será ajustada a partir destas métricas. Em S1–S4 serão executados 1000 combates **novos** por célula com sementes da fase `secondary`.

As métricas adicionais são: sobrevivência até o fim das rodadas 3, 5 e 10; quantis 10%, 50% e 90% do dano acumulado no combate; e dano acumulado dividido pelos **turnos próprios** do Blacklight, incluindo rodada bônus. Vitória antes de um horizonte conta como sobrevivência porque o combate terminou com Blacklight vivo; derrota até o horizonte não conta. Inconclusão aos 30 conta como sobrevivência nos três horizontes. Esses quantis e razões são descritivos, de amostra independente, e não substituem ICs da confirmação de 10 mil combates. O dano acumulado é a perda de Health aplicada, podendo incluir Health negativo até o limite Heroic; a razão por turno não deve ser lida como dano necessário para incapacitar.

Cada trilha será registrada durante a execução e checada pelo auditor independente. O JSON conserva hashes de código, deste pré-registro e do script.
