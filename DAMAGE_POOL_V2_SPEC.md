# Gate e pré-registro técnico para a versão de dano da mesa

Registrado em 27/10/2026 **antes de integrar o novo dano ou observar qualquer resultado de combate com ele**. Fonte normativa: [decisão de dano da mesa](DAMAGE_POOL_RULING.md), [decisão de Fast Strikes](FAST_STRIKES_RULING.md), ficha atual e Core Rulebook para todas as demais ações. O commit local `a19ebe3` preserva código e resultados da versão anterior; suas taxas são históricas para a mesa atual.

## Aim e mecanismo

Reavaliar as políticas de Victor sob a regra real da mesa: o multiplicador final, depois de bônus de arma e Damage Reduction, é a **quantidade de d6 de dano**. Cada face 1 desses dados vale 6; os dados de dano não são reutilizações dos dados do teste de acerto. O acerto continua d616 com um único dado Marvel distinguível. Um ataque normal fantástico dobra o total dos dados de dano mais o bônus de habilidade. Quando a redução deixa zero dados, dano zero conforme o piso já adotado; este caso exige oráculo forçado.

Fast Strikes usa um teste de acerto com **duas edges** de Victor e dois componentes de dano contra o mesmo alvo, mesmo sem armas diferentes. Cada componente recebe sua própria redução no número de dados. Em acerto comum, reduzir pela metade **a contagem de dados e o bônus de habilidade antes de rolar**, arredondando a contagem ímpar de dados para baixo. Exemplo sem DR: Marreta `8→4d6+3`, Lâmina `7→3d6+3`, total `7d6+6`. Em fantástico, ambos são integrais, sem o dobro genérico: `15d6+12` no exemplo. Bleeding/Stunned/ação bônus da Lâmina seguem as decisões já documentadas. Bônus de habilidade ímpar sob Fast Strikes não foi definido pela mesa; bloquear esse caso em vez de inventar um arredondamento até haver decisão.

## Gate de validação antes de Monte Carlo

1. Testes de referência para `1→6` em **cada** dado de dano, seis faces exatas, quantidade de dados e bônus de Marreta/Lâmina/Garra, DR antes da divisão, arredondamento ímpar, fantástico normal e fantástico de Fast Strikes.
2. Forçar acerto, erro, fantástico, duas edges, escudo ativado após acerto, Sturdy, alvo com DR alta, dois componentes no mesmo alvo, sangramento sem acúmulo, Stunned e segunda ação da Lâmina (também com dois componentes e nova rolagem).
3. Registrar **todas as faces de dano** e cada componente no log; auditor independente deve recalcular contagem, transformação 1→6, soma, aplicação de DR, estado final, recursos e reações sem importar a função de dano do motor. Qualquer divergência bloqueia os resultados.
4. Oráculo estatístico independente: uma face de dano tem valores `{6,2,3,4,5,6}` e média exata `26/6`; comparar distribuição de somas por convolução para pools pequenos e média/amostragem para pools grandes. Não usar resultado de combate para validar a própria primitiva.
5. Reexecutar a suíte inteira. Testes que codificavam a fórmula antiga devem migrar para histórico ou ser substituídos por oráculos da nova regra; uma suíte verde com testes da fórmula antiga não aprova a versão da mesa.

## Desenho experimental após o gate

Executar desenvolvimento com cerca de 1000 lutas por célula das dez políticas e quatro cenários antigos, usando **novas sementes de versão**, para identificar bugs e políticas inviáveis. Acrescentar explicitamente políticas de Fast Strikes com duas armas, com Escudo reativo e sem ele; só escolher finalistas após inspeção de trilhas. Repetir com amostra maior e sementes novas. Os cenários já vistos na versão antiga constituem **replicação sob outra regra**, não confirmação virgem. Reservar cenários/perfis adicionais, definidos antes de sua execução, para a validação das finalistas. Relatar vitória, derrota, inconclusão, dano, recursos e intervalos por cenário, sem médias da campanha não fundamentadas.

As três políticas acrescentadas antes do desenvolvimento v2 são `hammer_fast` (duas componentes da Marreta), `claw_hammer_fast` (Garra + Marreta) e `shield_blade_hammer_reactive` (Lâmina + Marreta com reação defensiva do Escudo). A política original `blade_hammer_fast` representa as duas armas sem Escudo reativo. O smoke de dez políticas em dez sementes por célula só verificou execução; suas taxas não selecionam finalistas.

As extensões de grupo, Focus e corredor têm seus próprios mecanismos de dano e precisam ser migradas e auditadas separadamente. O esclarecimento F0 do Escudo permanece: somente dano de Health recebe sua redução; dano de Focus não. Nenhuma tabela antiga será copiada para o novo relatório com rótulo de resultado atual.
