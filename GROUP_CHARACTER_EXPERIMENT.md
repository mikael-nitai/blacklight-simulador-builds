# Grupo experimental com fichas versionadas

`combatants.group_runner.run_group` aceita uma ficha versionada por participante,
uma política `GroupPolicy` por ficha, equipes, papéis de jogador/NPC e, quando
necessário, uma ordem declarada para desempates de iniciativa. Utiliza o mesmo
gate de mecânicas físicas das fichas de duelo; ele não certifica a legalidade
da build ou a fidelidade de todas as habilidades no grupo. Exige a regra atual
`split_fast_v3` e produz uma trilha completa identificada como
`experimental_group_uncertified`.

O campo de batalha é **contato fixo entre todos**: não há posições individuais,
movimentação, knockback, Karma ou ataques de Focus. Uma ficha com Healing Factor
e Resilience negativa é bloqueada no adaptador comum e no perfil do motor enquanto o caso extremo
é investigado. Os inimigos de exemplo são sintéticos, não personagens oficiais.

O executor confronta a trilha com os perfis e as contas de dano, a iniciativa,
as equipes, os dois testes de Fast e um resumo independente dos resultados.
Os testes de Fast são comparados com a defesa e com o estado anterior aos efeitos
de cada alvo; uma adulteração coordenada das edges em ambos os registros é
rejeitada. Essas conferências não cobrem todas as transições de condição,
reações e legalidade em grupo: auditoria sem falhas aqui não é certificação.

Após os dois braços e seus efeitos, a ordem inicial de gatilhos de Riposte por
braço é uma interpretação operacional ainda sujeita ao mestre. Uma reação
gerada por um Riposte interrompe esse encadeamento antes de um gatilho anterior
pendente, respeitando o caráter interruptivo de ACT-03. A duração de Stunned
de múltiplas fontes permanece a hipótese de instâncias paralelas sem acúmulo de
penalidade; não é uma regra oficial confirmada. A estratégia `lowest_defense`
compara a defesa de Agility em ataques à distância, ou Melee quando o alvo tem
Brawling, e usa Melee nos ataques próximos.

## Executar um exemplo

No PowerShell, a partir da pasta do projeto, com Python 3.11 ou posterior:

```powershell
python -m scripts.character_group examples/experimental_group_config.json --output experimental_outputs/meu-grupo-001.json
```

O nome de saída precisa ser novo. A pasta de resultados congelados `results/`
é recusada para esses experimentos: ainda não existe um contrato de
congelamento certificado para este schema. O arquivo JSON contém as fichas
normalizadas, parâmetros, equipes, papéis, semente, trilha, escopo e hashes.
O programa lê os bytes das fichas e da configuração uma vez e recusa publicar
se os arquivos mudarem durante a execução. Hashes demonstram quais fontes foram
registradas, não a correção do modelo ou a ausência de dependências ocultas.

Para testar outras fichas, faça uma cópia da configuração, ajuste os caminhos
relativos à pasta onde ela estiver, os times, os papéis e as políticas. O gate
recusa poderes e variações sem suporte. As saídas de grupo não passam pelo
congelamento certificado de duelos e não são base para escolher a melhor
estratégia até os demais gates de grupo serem concluídos.

## Contrato experimental de trilha v2

O schema `blacklight-experimental-character-group-v2` acrescenta eventos para
o começo previsto de cada turno, o resultado de cada teste antes do dano e a
retirada de gatilhos da fila. O auditor independente acompanha o relógio por
participante, cada instância de Stunned, Dodge, ações e reações durante turnos,
e a ordem dos gatilhos; ele vincula o Escudo a um acerto contra o próprio alvo.
O caso de múltiplas fontes ainda usa a interpretação operacional documentada,
e a ordem inicial entre gatilhos de braços diferentes continua uma convenção.

As trilhas v1, inclusive `group_integration_001.json`, permanecem ligadas às
fontes originais e não são reinterpretadas como trilhas v2. Ambos os schemas
continuam bloqueados no congelamento certificado de duelos. A verificação v2
amplia a cobertura, mas ainda não demonstra a legalidade de todos os poderes,
efeitos, custos, configurações de mapa ou decisões dos adversários.

## Verificações desta etapa

- Casos independentes forçados cobrem reações aninhadas, incapacitação antes
  de um Riposte pendente e ação extra de Lâmina que muda para outro alvo vivo.
- Foram executados 300 confrontos sintéticos com auditorias disponíveis; são
  controles de integração, não uma bateria para comparar estratégias.
- O contrato v2 foi exercitado em 400 confrontos adicionais com variações de
  armas, reação defensiva, cura e Dodge. Testes forçados também rejeitam ações
  fora do turno, expiração de Stunned adulterada, gatilho incorreto de Escudo
  e processamento FIFO incorreto de reações aninhadas; o auditor acompanha a
  recuperação de um inconsciente vivo e impede interpretá-la como ressurreição.
- A suíte completa desta revisão passou em 330 testes; um caso adicional
  específico confirmou a expiração no turno previsto de uma fonte inconsciente.
- A suíte completa passou em 323 testes. Quatro logs de controle e duas
  baterias anteriores de 1.000 sementes foram reproduzidos; 37 resultados
  congelados tiveram suas fontes verificadas.
