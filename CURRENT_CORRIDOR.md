# Corredor com fichas e Fast Strikes atual

27/10/2026. `SplitFastCorridorDuel` combina a mesma geometria do protótipo anterior com `SplitFastDuel`, sem copiar o resolvedor de ataques. O Fast atual mantém os dois testes antes dos efeitos, seleção prévia de um braço para efeitos, Escudo antes do dano e danos/efeitos de ambos antes de Riposte, conforme [SPLIT_FAST_SPEC.md](SPLIT_FAST_SPEC.md).

## MAP-01: geometria e informações disponíveis

O mapa sintético é uma linha de células inteiras `0..L`, sem cobertura, terreno difícil ou passagem por outro personagem. O combatente0 começa à esquerda do combatente1; ambos permanecem nessa ordem. A [especificação histórica](CORRIDOR_SPEC.md) registra essa hipótese geométrica e as referências do Core para movimento e distância; ela não é uma afirmação sobre todos os mapas de RPG.

`CorridorMap` conserva comprimento e posições iniciais imutáveis. O motor limita o movimento às células disponíveis, consome a ação declarada e mantém `distance = posição1 − posição0`. Valores fracionários, booleanos, fora do mapa ou sobrepostos são recusados. A posição visível, o adversário e os limites são expostos em `Observation.terrain`, com tuplas congeladas; a política não recebe o estado mutável nem dados futuros.

Knockback com deslocamento positivo é rejeitado **antes de alterar Health, estatísticas de ataque/dano, distância ou posições**. Regras de colisão ainda não foram implementadas. Uma rolagem e uma defesa podem já ter sido processadas ao chegar a esse gate; não há promessa de rollback de RNG. A instância aborta e o runner não publica um resultado nem descarta silenciosamente só aquela luta. Deslocamento zero por DR não é uma colisão e continua permitido.

## Política que observa a parede

`WallAwarePolicy` mantém as prioridades da política base. Quando ela solicitaria uma ação padrão de recuo contra uma parede sem nenhuma célula livre e tem um ataque à distância válido, atira em vez de gastar essa ação sem se mover. Isso importa, por exemplo, quando o perseguidor corre tão rápido quanto o atirador. Victor atual, com Run5 contra Run6, não aciona necessariamente esse ramo; não se atribui uma vantagem à política sem verificar os casos em que suas ações diferem.

O movimento posterior ainda pode pedir recuo e terminar com zero células. A política não encontra rotas alternativas, não atravessa o adversário, não cria poderes e não foi apresentada como ótima. Ela tem classe e metadados próprios; resultados seus não são replays da política histórica cega à parede.

## API, fontes e reprodução

O executor de fichas aceita `battlefield=CorridorMap(...)` em `run_duel` e `run_batch`. A distância inicial é derivada do mapa; uma distância explícita incompatível é rejeitada. O relatório registra posições finais, chegada à parede, contato e a cobertura real de corredor, em vez de rotular o cenário como campo aberto. Os auditores de combate e posição são executados em conjunto.

Os manifestos incluem geometria, auditor de posições, estas hipóteses de mapa e as implementações das políticas. A identidade das células atuais usa `character-batch-v2`, com as classes das políticas e o mapa incluídos. Isso distingue duas implementações com parâmetros iguais. A fórmula v1 e suas sementes permanecem para o contrato histórico. Comparações novas precisam usar desenho experimental e sementes declarados, sem assumir pareamento entre células.

```powershell
python -m scripts.character_sheet duel --hero characters/victor_halle/rank3_2026-10-27_split_fast.json --opponent characters/examples/synthetic_rank4_nonammo_gunner.json --policy shield_blade_hammer_reactive --effect-limb 1 --opponent-policy kiter --opponent-wall-aware --corridor-length 12 --positions 0 8 --seed 11 --output results/my_current_corridor.json
```

O atirador é uma ficha sintética de integração, com seis atributos explícitos e um equipamento genérico não classificado como munição. Não é um personagem oficial nem um poder de energia do Core. A revisão de Victor preserva os valores da ficha Rank3 recebida. Outras fichas compatíveis entram pelos mesmos parâmetros; poderes e variantes desconhecidos continuam bloqueados pelo adaptador.

## Gates desta migração

O revisor independente criou [scripts/audit_current_corridor.py](scripts/audit_current_corridor.py), com oráculos de geometria, observação congelada e ação na parede, 50 equivalências de contato com o duelo aberto, 50 replays da geometria histórica e 100 combates mapeados com ambos auditores. Também verificou cronologia de Fast, KB positivo/zero, execução pela API/CLI, manifestos e identidade das sementes. O bypass de consistência por um teste já preparado foi reproduzido e corrigido antes da aprovação desses gates.

O replay da classe histórica compartilha o núcleo e as políticas atuais; comprova a migração de geometria nesses casos, não a aritmética de uma versão antiga inteira. Os controles de execução desta etapa são produzidos por `scripts.current_corridor_demos`, sem selecionar uma estratégia como melhor. Cobertura, colisões, mapas com rotas, grupo completo e todas as fichas oficiais continuam fora desta etapa.

A suíte completa passou em **228 testes**, incluindo os quinze gates novos do corredor atual. O script de controles gera dois exemplos completos (efeitos de Lâmina ou Marreta) e uma bateria de 1.000 duelos auditados integralmente; os artefatos recebem nomes próprios, sem sobrescrever resultados anteriores.
