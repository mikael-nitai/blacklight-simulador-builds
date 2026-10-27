# Gate de dano de Focus e controle mental

Aberto em 27/10/2026. Este gate não altera o motor confirmatório de duelos nem os JSONs já congelados. O primeiro adversário sintético será baseado no poder **Mental Punch**, e não em um ataque mental genérico: a [FAQ oficial de março/2025, p.1](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20250327.pdf) esclarece que ataques Logic/Ego normalmente exigem um poder. O *Core Rulebook* fornecido, p.108 (PDF p.109), permite Mental Punch sem pré-requisitos: ação padrão, ataque Melee dentro do alcance, dano regular de Focus no acerto e dano dobrado mais Stunned no sucesso fantástico.

O Core pp.33–34 (PDF pp.34–35) separa Health de Focus: Focus 0 deixa o alvo **Demoralized**, encerra concentração e impõe trouble em todos os testes; Focus ≤ negativo do Focus máximo deixa **Shattered**. Um atacante com a tag Heroic não reduz o alvo até Shattered por acidente: para 90 Focus máximo, o piso é −89. O Core p.38 (PDF p.39) faz Stunned impedir ações e conceder edge a ataques contra o alvo; a [FAQ oficial, p.4](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20250327.pdf) fixa a duração de uma rodada até o início do próximo turno do causador. Sturdy 1 da ficha concede **Health** DR, não Focus DR.

## Fronteira da regra da mesa

O usuário definiu que o Escudo Rank 3 reduz em 2 o multiplicador de ataques Melee/Agility e que isso se soma a Sturdy 1 para dano físico. Mental Punch é um ataque Melee que causa Focus. A aplicação do −2 do Escudo ao **dano de Focus** é plausível pelo tipo de ataque, mas a frase da mesa não separou explicitamente o tipo de dano. Implementar `shield_reduction` como parâmetro explícito com variantes 0 e 2; nunca somar Sturdy 1 ao dano de Focus. Não misturar variantes em uma mesma estimativa de vitória. Até haver esclarecimento, qualquer recomendação contra Mental Punch será condicionada à variante.

## Gate inicial

Criar uma primitiva pura para um Mental Punch já rolado, com teste de Melee contra defesa Melee, dano e limite Heroic. Oráculos independentes: acerto comum, fantástico, Fantastic failure, Ultimate Fantastic, DR que zera multiplicador, Focus exatamente 0, Shattered exatamente no limiar e proteção Heroic. A primitiva deve rejeitar entradas inválidas e expor indicadores de Demoralized, Shattered e Stunned. **Ainda não é** um combate, pois não implementa trouble subsequente, fim de concentração, iniciativa, reações, escape/recuperação ou decisão adversária. Somente após integrar e auditar esses estados será permitido produzir taxas de vitória de um adversário de Focus.
