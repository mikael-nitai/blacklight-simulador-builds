# Controles executados do corredor atual

27/10/2026. A implementação de [CURRENT_CORRIDOR.md](CURRENT_CORRIDOR.md) foi salva no commit `7d6517a`. O mapa usa duas fichas, posições inteiras e a regra atual de Fast Strikes. A suíte completa passou em **228 testes**.

Foram gerados e conferidos:

- [Efeitos da Lâmina escolhidos](results/current_corridor_v1_blade_effects_demo.json): três usos de Fast, seis testes por braço, posição final `[11,12]`.
- [Efeitos da Marreta escolhidos](results/current_corridor_v1_hammer_effects_demo.json): três usos de Fast, seis testes por braço, posição final `[11,12]`.
- [Bateria de integração](results/current_corridor_v1_integration_batch.json): **1.000 duelos iniciados, 1.000 trilhas auditadas** tanto para combate quanto para geometria, sem divergências.

Os dois exemplos guardam logs completos. O resumo da bateria conserva sementes, fichas, políticas, mapa e parâmetros para reprodução das execuções auditadas. Os três arquivos estão vinculados ao commit executado em `results/source_snapshots.json`; o verificador conferiu os 37 resultados versionados do projeto, preservando também os contratos anteriores.

O revisor independente verificou 50 equivalências em contato com o motor aberto, 50 replays da geometria histórica e 100 combates mapeados. Os gates de observação imutável, cronologia dos dois testes, Escudo, Riposte, consistência de posições, KB positivo/zero, API, CLI e sementes passaram. O replay da classe antiga compartilha o núcleo atual, portanto sua evidência é de migração de geometria.

O adversário é sintético e usa equipamento genérico não classificado como munição; nenhum personagem oficial completo foi simulado nesta etapa. A política que observa a parede evita gastar uma ação padrão num recuo bloqueado quando o ramo se aplica. Estes são controles de execução e integração; a avaliação de eficiência entre estratégias depende de experimentos próprios da versão atual. Grupo, cobertura, colisões e mapas com rotas continuam pendentes.
