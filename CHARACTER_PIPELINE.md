# Fichas versionadas e expansão do motor

Em 27/10/2026, o usuário confirmou o objetivo final: adversários com fichas de combate completas, incluindo personagens oficiais do Core quando possível; Victor pode evoluir para outro Rank; qualquer outra ficha deve poder ocupar seu lugar sem reescrever o motor. A implementação é progressiva. O recorte de duelos atual continua uma etapa da missão completa.

## Como entra uma ficha nova

O usuário envia o PDF atualizado. O importador guarda o arquivo de origem, seu hash e os campos encontrados. A conferência da ficha resolve nomes, níveis, equipamentos e diferenças entre valores escritos e derivados. A versão conferida é salva como um novo registro em `characters/`, mantendo a versão anterior para reprodução. Nenhum aumento de Rank inventa atributos, poderes ou decisões do mestre: esses dados vêm da ficha nova.

Cada registro tem identidade e revisão próprias, Rank, seis atributos, seis defesas, Health, Focus, Karma, modos de movimento, iniciativa, poderes com níveis, traits, tags, equipamentos, parâmetros de variantes e referências de fonte. O formato `blacklight.character.v1` está em `combatants/sheets.py`. Parâmetros de uma habilidade nova podem ser preservados mesmo quando sua mecânica ainda não está implementada.

O catálogo de mecânicas verifica a cobertura antes de executar. Ele aceita os efeitos implementados para o cenário escolhido, informa elementos sem efeito naquele contexto e bloqueia habilidades ou variantes de combate desconhecidas. Por exemplo, o Escudo Rank 4 tem reflexão ainda pendente; uma ficha com ele não pode entrar silenciosamente no adaptador Rank 3. Uma defesa oficial modificada também é preservada e sinalizada, sem ser corrigida para satisfazer o motor.

O importador de PDF produz **evidência para revisão**; a extração de campos não certifica regras. A ficha atual teve 432 campos extraídos, com hash igual ao documento já auditado. Textos do PDF são dados de origem, nunca instruções executadas pelo programa.

## O que já funciona

- `characters/victor_halle/rank3_2026-10-27_split_fast.json` contém a revisão atual da mesa. Conserva os valores e o PDF da versão `rank3_2026-10-26.json`, que permanece histórica; não inventa evolução de Rank. Iniciativa/Run continuam com suas divergências registradas em notas.
- `combatants/duel_adapter.py` transforma uma ficha compatível em um combatente do motor físico existente. Mighty, Sturdy e Accuracy usam o nível da ficha; atributos, Rank, recursos e nome são carregados do registro.
- `combatants/runner.py` executa um duelo completo ou uma bateria entre duas fichas arbitrárias. O resultado é contado pela identidade do combatente escolhido, sem depender do nome Blacklight. Cada célula tem sementes, políticas, fichas, cobertura e fontes registradas.
- As [famílias modulares de cura e ativação de estado](MODULAR_STATES.md) resolvem Do This All Day, Attack Stance, Dodge e a ativação padrão do Escudo por definições reutilizáveis. A [duração modular](MODULAR_LIFECYCLE.md) planeja a expiração de Dodge/Stunned no início do turno. O executor genérico usa essas camadas, com equivalência de replay e revisão independente. Ataques, demais durações e reações ainda passam pelo resolvedor anterior.
- Os testes reproduzem o comportamento anterior de Victor em 20 sementes, trocam por outro personagem Rank 4, verificam que a versão anterior permanece intacta e rejeitam poderes/variantes sem suporte. O exemplo Rank 4 é **sintético**, criado para testar substituição; não é uma ficha futura de Victor nem um perfil oficial.

Comandos a partir da pasta do projeto:

```powershell
python -m scripts.character_sheet extract-pdf "C:\caminho\ficha.pdf" --output character_evidence/nova_ficha_draft.json
python -m scripts.character_sheet validate characters/victor_halle/rank3_2026-10-27_split_fast.json
python -m scripts.character_sheet batch --hero characters/examples/synthetic_rank4_split_fast.json --opponent characters/victor_halle/rank3_2026-10-27_split_fast.json --policy attack --opponent-policy shield_blade_hammer_reactive --opponent-effect-limb 1 --master-seed 731 --n 1000 --output results/new_character_rank4_batch.json
```

O usuário não precisa editar esses arquivos manualmente ao enviar uma nova ficha pela conversa. O processo de importação e conferência gera o registro apropriado.

Cada execução nova recebe outro nome e os [resultados anteriores preservam suas fontes](RESULT_VERSIONING.md). A troca de Rank ou de ficha muda os dados da célula; a migração do motor é conferida contra combates completos congelados, sem apresentar esses replays como novas amostras estatísticas.

Por padrão, `batch` executa e audita a trilha completa de **cada** combate antes
de somá-lo. Os agregados e os índices/sementes auditados são salvos, mas as
trilhas completas do lote não são guardadas; para inspecionar um combate, é
necessário reproduzi-lo com a mesma versão e a semente registrada. O comando
`--audit-every N`, com N maior que 1, reduz essa verificação a uma amostra e
identifica a saída como `sampled_starts`; ela não pode ser congelada como lote
genérico integralmente auditado. Isso não é evidência de que as simulações não
auditadas estejam erradas, nem de que passaram pela auditoria.

A revisão `split_fast_v3` seleciona o [novo Fast por braço](SPLIT_FAST_SPEC.md). Misturar revisões de regras entre as duas fichas é recusado antes do combate. O teste de seleção de Rank 4 usa o mesmo motor e outra ficha; as regras não são escolhidas pelo nome do personagem.

O mesmo runner aceita um [corredor opcional](CURRENT_CORRIDOR.md), escolhido como dado de ambiente, sem reescrever os ataques da ficha. O mapa e as classes das políticas entram na identidade das células atuais; geometria, fontes e posições são registradas e auditadas. Os valores e as sementes de células históricas v1 permanecem preservados. A política nova pode observar a parede por um snapshot imutável, sem acessar o estado mutável ou dados futuros.

## O que a arquitetura ainda precisa receber

O catálogo atual é um adaptador para o duelo físico já validado. Ele não implementa todos os poderes do Core. O resolvedor atual ainda concentra casos específicos de arma/ação; antes de expandir para muitas fichas, esses casos precisam convergir para módulos compartilhados por duelo, grupo, Focus e terreno.

Cada nova mecânica deve registrar seus pré-requisitos, custo, tipo de ação, alvos, alcance, gatilhos, modificadores, condição resultante, duração e fonte. O resolvedor de ações controla os recursos e a legalidade; o módulo da habilidade descreve os efeitos. Reações usam eventos e prioridades explícitas. Condições, resistência, imunidade, movimento, concentração e recursos devem ser reutilizáveis entre poderes. A implementação de uma mecânica serve a todas as fichas que a possuam; não deve depender do nome de um personagem.

A progressão técnica é: ampliar o registro de ações/efeitos e o estado comum; portar as mecânicas atuais com equivalência de replay; adicionar famílias de poderes com oráculos e testes de interação; depois importar fichas oficiais completas e testar políticas capazes de escolher entre suas opções. Rank X permanece uma situação narrativa segundo o Core, sem uma ficha numérica de combate a inventar.

## Comportamento dos adversários

Hoje as políticas são algoritmos explícitos simples. Um atacante usa seu ataque permitido; o atirador avalia distância, recua, atira e pode tratar sangramento; o grupo concentra ataques em Victor. Eles não enxergam dados futuros. O motor verifica a ação solicitada e aplica o resultado.

No objetivo final, a ficha fornece o repertório de ações legais e os recursos do adversário. A política compara alternativas como atacar Health ou Focus, controlar, manter concentração, curar, recuar, usar terreno, proteger um aliado ou guardar reação. Diferentes níveis de competência e políticas adversariais precisam ser testados. Possuir a ficha completa e ter uma política competente são requisitos distintos; ambos são necessários antes de tratar um confronto como evidência de estratégia robusta.

O [inventário de fichas oficiais](OFFICIAL_PROFILE_GATE.md) continua o ponto de entrada para os perfis do livro. A migração de fichas pode prosseguir conforme as mecânicas ficarem disponíveis, preservando as lacunas no relatório de cobertura.
