# Duração de efeitos em módulos reutilizáveis

27/10/2026. O executor de fichas usa `modular_physical_duel_v3`. Além das famílias de cura e ativação de estado, a expiração de **Dodge e Stunned no início do turno** passa por um planejador imutável. O módulo de duração não conhece Victor, armas, Rank ou políticas de combate.

`TimePoint` identifica o tipo de limite, sua ocorrência e o ator quando se trata de um turno. Os relógios de turno começam em 1; os de rodada aceitam 0, usado pela rodada bônus. `TimedEffect` registra identidade própria, tipo, alvo, causador, referências e prazos alternativos. `expiration_plan` valida as entradas e devolve os efeitos vencidos e restantes, preservando a ordem e sem alterar o combate. Efeitos com o mesmo tipo e alvo podem ter identidades diferentes; decidir se acumulam continua sendo responsabilidade da regra aplicável.

| Efeito integrado | Instante verificado | Resultado |
|---|---|---|
| Dodge | início do próximo turno do próprio defensor | remove Dodge antes de disponibilizar a ação do turno |
| Stunned da Marreta | início do próximo turno do causador, conforme contador gravado ao aplicar | remove Stunned antes de avaliar o impedimento de agir |

A ponte atual projeta os campos já validados do combatente nesse instante; esses campos continuam sendo o estado autoritativo. Ela evita manter dois registros mutáveis do mesmo efeito durante a migração. A ordem de logs também é preservada: fim de Dodge, fins de Stunned na ordem dos combatentes e início do turno.

O planejador puro já representa prazos como “próximo turno do causador **ou** fim de uma rodada”. Os relógios de início/fim de rodada **ainda não estão ligados ao laço do duelo**. Aplicação, remoção antecipada, concentração, empilhamento e resistência de todos os outros efeitos também precisam de módulos e oráculos próprios. Esta etapa não certifica o catálogo completo de poderes.

## Evidência da migração

A suíte completa tem 176 testes aprovados. Além de casos diretos de fontes, alvos, prazos e dados inválidos, os testes comparam 192 estados da ponte e todos os eventos e métricas dos cinco duelos de ficha congelados em `f9c540a`.

A revisão independente criou [scripts/audit_modular_lifecycle.py](scripts/audit_modular_lifecycle.py): 2.352 estados com contagens de turno independentes, Dodge nos dois lados e Stunned simultâneo; 676 pares de relógios; três casos de prazo alternativo; identidades paralelas; rodada bônus; e os cinco replays contra ambos os motores. O script usa oráculos diretos além da comparação com a referência, imprime os hashes e não grava resultados. Não encontrou divergências nesse escopo. As auditorias anteriores de cura e ativação também passaram novamente, incluindo 660 replays completos.

O [controle de versões dos resultados](RESULT_VERSIONING.md) conserva as medições anteriores e exige um nome novo para uma execução nova. Os comandos de bateria agora recusam um destino existente antes de simular. As cópias novas dos cinco duelos e da bateria de troca de ficha podem ser produzidas com:

```powershell
python -m scripts.replay_character_snapshots --output-prefix character_replay_v3
```

Esse comando exige comparação exata de eventos e métricas nos duelos e de sementes, contagens, taxas e métricas na bateria. Ele grava outros arquivos, com fontes atuais e vínculo ao exemplo anterior. É uma verificação de migração, não uma nova busca de estratégia.

A execução desta etapa gerou os seis arquivos `results/character_replay_v3_*`. Os cinco duelos repetiram todos os eventos e métricas anteriores. A [bateria de troca de ficha](results/character_replay_v3_rank4_batch.json), com 1.000 duelos e dez trilhas completas auditadas, conservou 2 vitórias e 998 derrotas do exemplo sintético Rank 4 contra Victor. As sementes e a amostra são as mesmas da referência. O [exemplo de Dodge](results/character_replay_v3_dodge_demo.json) também conservou seu resultado inconclusivo. Para repetir a geração, escolha outro prefixo de saída.

Verificação sem recriar resultados:

```powershell
python -m unittest discover -s tests -q
python -B -m scripts.audit_modular_lifecycle
python -B -m scripts.audit_modular_states
python -B -m scripts.audit_modular_healing
python -m scripts.verify_sources
```

A evolução seguinte precisa incorporar o catálogo de condições e suas interações ao estado comum, depois compartilhar essas famílias entre duelo, grupo, Focus e terreno. A importação de fichas completas permanece condicionada à cobertura real das suas mecânicas.
