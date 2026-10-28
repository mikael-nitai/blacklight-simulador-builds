# Implementação do último balanceamento de Fast Strikes

27/10/2026. Fonte normativa: confirmações mais recentes do usuário em [FAST_STRIKES_RULING.md](FAST_STRIKES_RULING.md), HR-07 a HR-09 de [RULES_AUDIT.md](RULES_AUDIT.md). Este arquivo descreve o contrato executável; não pré-registra uma seleção de estratégia nem converte os resultados anteriores em medições da regra nova.

## Ordem confirmada e dados por braço

Antes de usar Fast, declarar as armas dos dois braços e um braço escolhido para efeitos. `FastAction.effect_limb` vale 0 para o braço principal e 1 para o segundo. A escolha é imutável durante esse uso; quando as armas são iguais, selecionar um braço continua sendo a interpretação operacional do seletor, sem duplicar seus efeitos.

1. Congelar os modificadores, defesas, edges e troubles dos dois testes no estado anterior aos efeitos.
2. Fazer os dois testes d616, incluindo suas rerrolagens. Victor recebe as duas edges confirmadas em cada teste, provenientes de Blazing-Fast Fists e Signature Attack. Outras fichas recebem apenas as fontes que possuírem.
3. Permitir a reação defensiva de Escudo depois dos acertos conhecidos e antes do dano. A proteção persiste e a redução é aplicada separadamente em cada componente elegível.
4. Aplicar os dois resultados já testados. Cada erro causa zero, acerto comum aplica metade dos dados/bônus antes da rolagem, fantástico aplica o componente integral. Somente o braço pré-escolhido aplica Bleeding, membro, Stunned ou elegibilidade da ação extra de Lâmina.
5. Só depois dos danos/efeitos de ambos, resolver a fila de Riposte. Stunned ou incapacitação podem impedir a reação. Um teste já concluído não ganha edge por causa do efeito do primeiro braço.
6. Se o próprio braço escolhido de Lâmina obteve um fantástico com sucesso no turno, permitir uma segunda ação legal com Lâmina. Ela pode ser outro Fast, com nova declaração e dois novos testes; não pode gerar uma terceira ação. Riposte fora do turno não concede essa ação.

Os braços são dois componentes de uma ação padrão. Acertos e métricas de ataques agora contam os testes por braço; a auditoria agrupa ambos pelo identificador do uso para não confundir dois testes com duas ações padrão. A redução que zera N antes da metade zera o componente. Quando N=1 positivo após DR, a metade vira zero dados e conserva metade do bônus: `0d6+3=3` no exemplo confirmado.

## Versões de ficha e execução

`split_fast_v3` seleciona `SplitFastDuel` no executor genérico. A revisão atual de Victor é [rank3_2026-10-27_split_fast.json](characters/victor_halle/rank3_2026-10-27_split_fast.json): mesmos atributos, Rank 3, recursos, poderes e PDF de origem; apenas a revisão da regra de mesa e suas notas mudaram. O exemplo Rank 4 continua sintético, para provar substituição de ficha. Não é progressão presumida de Victor nem um personagem oficial.

Os dois combatentes de um teste precisam declarar a mesma revisão de regras da mesa. A versão `literal_marvel_pool_v2` conserva o Fast de um teste, efeitos de ambas as armas e o antigo piso de zero dados. O comando exige `--historical-rules` para executá-la explicitamente. Os commits e resultados anteriores permanecem intactos.

Exemplo de execução atual, escolhendo os efeitos da Marreta no segundo braço:

```powershell
python -m scripts.character_sheet duel --hero characters/victor_halle/rank3_2026-10-27_split_fast.json --opponent characters/examples/synthetic_rank4_split_fast.json --policy shield_blade_hammer_reactive --effect-limb 1 --seed 51 --output results/my_current_fast_demo.json
```

`--effect-limb 0` escolhe os efeitos da Lâmina nesse arranjo. Essa é uma escolha da política antes da ação, não uma conclusão sobre qual opção é melhor. O motor rejeita um pedido de Fast sem seletor antes de consumir a ação ou dados.

## Validação e limites

Há oráculos diretos com faces de dano fixadas em1: Marreta comum27/fantástica54, Lâmina comum21/fantástica48, ambas comuns48, ambas fantásticas102, combinação mista75. Cada resultado depende de seu próprio teste e nenhum desses totais é garantido em dados aleatórios.

O revisor independente escreveu `scripts/audit_split_fast.py`, com 108 combinações de armas/resultados/seletor, quatro casos de cronologia (incluindo as duas rerrolagens em cada braço), fronteira de zero dados/ação extra e cinco logs adulterados. Ele encontrou duas falhas do auditor: fila de reação aceita antes dos testes e Escudo aceito depois do primeiro dano. Ambas foram corrigidas; essas falsificações passaram a ser rejeitadas. O script executa sem importar o cálculo de dano de produção como oráculo.

A suíte completa passou em 213 testes, incluindo as interações com a ficha versionada, ação extra após Lâmina comum fantástica e ausência de ação extra no Riposte. A execução real da CLI foi conferida nas duas versões, inclusive a recusa de executar o contrato histórico sem a opção explícita. Sessenta duelos de execução com as duas escolhas de efeitos também passaram no auditor; não foram usados para selecionar estratégia.

Os [exemplos com efeitos da Lâmina](results/split_fast_v3_blade_effects_demo.json) e [da Marreta](results/split_fast_v3_hammer_effects_demo.json) foram gerados e auditados: cada um registra três usos de Fast e seis testes por braço. A [bateria de substituição por outra ficha Rank 4](results/split_fast_v3_rank4_integration_batch.json) executou 1.000 duelos e auditou as 1.000 trilhas completas. São controles de integração, sem seleção de estratégia. Os três artefatos estão ligados ao commit `00f06f9`; o verificador conferiu 34 resultados versionados sem divergências.

Reprodução dos controles de integração, com um prefixo novo para não substituir arquivos:

```powershell
python -m unittest discover -s tests -q
python -B -m scripts.audit_split_fast
python -B -m scripts.audit_shared_conditions --timing-only
python -m scripts.split_fast_demos --output-prefix split_fast_v3
```

O duelo genérico e o [corredor atual de duas fichas](CURRENT_CORRIDOR.md) executam a revisão nova. As baterias antigas de grupo/corredor conservam seus contratos históricos e exigem opção explícita. O usuário confirmou posteriormente que cada braço pode mirar um alvo distinto; a migração do grupo começou, mas ainda não está validada. Esta etapa não certifica todos os poderes, os efeitos numéricos de membros ou fichas oficiais completas. Sensibilidade, busca, replicação/reserva e manuais da regra nova ainda precisam de experimentos próprios. A metade de bônus de habilidade ímpar continua bloqueada até decisão da mesa.
