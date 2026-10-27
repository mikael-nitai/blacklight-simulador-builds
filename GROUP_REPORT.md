# Encontro experimental de três participantes

**27/10/2026.** Esta expansão é separada do [relatório confirmatório de duelos](REPORT.md). O [pré-registro específico](GROUP_EXPERIMENT_SPEC.md) fixou dois inimigos sintéticos que atacam Victor em conjunto, todos sempre ao alcance corpo a corpo. [GROUP_SPEC.md](GROUP_SPEC.md) delimita as regras implementadas e as que ainda faltam. O motor de grupo fica em `experimental/`; não foi usado nos 400.000 duelos confirmatórios.

**Bateria histórica:** as taxas abaixo usam a fórmula anterior. O estudo foi refeito com dano literal, duas edges e os componentes de Fast Strikes da mesa; os resultados atuais estão no [relatório v2](POOL_V2_REPORT.md), com os limites da extensão de dois alvos declarados.

## O que foi testado

Uma rolagem de Fast Strikes pode ser comparada a até duas defesas distintas. Cada alvo acertado recebe metade do dano regular, ou o dano integral em sucesso fantástico. A redução de dano é individual. Nesse experimento, Fast Strikes não usa armas biológicas nem gera o golpe adicional caseiro da Lâmina. A política de Marreta escolhe o adversário vivo com menor Health; a variante defensiva ativa o Escudo após um acerto ou ao fim do turno e o desativa gratuitamente antes de atacar. Ambos os inimigos atacam Victor, sem Riposte, armas ou poderes.

G1 usa dois inimigos Rank 2 (Health 90, Melee 4); G2 usa dois Rank 3 (Health 150, Melee 6). Todos têm Resilience coerente com Health. Cada célula teve 1000 combates de desenvolvimento e 10.000 sementes novas para a tabela abaixo. As seis células de descrição totalizam **60.000** combates, com **600 trilhas completas auditadas**. A suíte total passou em **84 testes**, dos quais onze cobrem o protótipo de grupo e seu auditor.

| Cenário | Política de Victor | Vitórias / 10.000 | Taxa de vitória, IC Wilson 95% | Rodadas médias |
|---|---|---:|---:|---:|
| G1, dois Rank 2 | Marreta | 10.000 | 100,00% [99,96%; 100,00%] | 2,24 |
| G1, dois Rank 2 | Marreta + Escudo | 10.000 | 100,00% [99,96%; 100,00%] | 2,35 |
| G1, dois Rank 2 | Fast Strikes sem armas | 10.000 | 100,00% [99,96%; 100,00%] | 2,76 |
| G2, dois Rank 3 | Marreta | 9.523 | 95,23% [94,79%; 95,63%] | 4,60 |
| G2, dois Rank 3 | Marreta + Escudo | 10.000 | 100,00% [99,96%; 100,00%] | 4,79 |
| G2, dois Rank 3 | Fast Strikes sem armas | 7.779 | 77,79% [76,96%; 78,59%] | 5,23 |

Não houve inconclusões nessas seis células; os demais combates foram derrotas. Uma observação de 100% significa **zero derrotas observadas** em 10.000 simulações, não invulnerabilidade universal. G1 saturou nas três políticas e quase não discrimina entre elas. Em G2, os atacantes básicos têm multiplicador de dano ×3; com Escudo ativo, a redução combinada do Escudo (2) e Sturdy 1 (1) zera esse multiplicador. O resultado de Marreta + Escudo depende fortemente desse perfil inimigo e da regra da mesa. Inimigos com bônus de multiplicador, ataques de Focus, controle, dano de área, alcance, terreno ou outras opções podem quebrar esse padrão. Os inimigos daqui cooperam apenas ao concentrar ataques e, portanto, não são um teste completo de tática de grupo.

**Revisão após a primeira execução.** A conferência do Core p.38 encontrou edge para ataques contra alvo Stunned. O protótipo passou a aplicá-la e ganhou um oráculo forçado; as seis células e os exemplos foram reexecutados com os mesmos índices de sementes e novos hashes. As contagens ficaram idênticas porque nenhum dos adversários desse experimento ataca um alvo Stunned. A versão anterior está preservada no commit `af5fc0e`; as taxas desta tabela vêm dos JSONs atuais. Esta correção não transforma a bateria exploratória em confirmação independente.

## Evidência auditável

Os arquivos [desenvolvimento](results/group_dev_summary.json) e [descrição](results/group_description_summary.json) registram perfis, políticas, contagens, sementes, intervalos e hashes de fontes. Dois exemplos completos, recalculados sem compartilhar a função de dano do motor, são [vitória com Escudo, índice 0](results/group_demo_shield_win_0.json) e [derrota com Fast Strikes, índice 8](results/group_demo_fast_loss_8.json). No primeiro, a Marreta causa dano e o Escudo ativo reduz a zero vários ataques básicos; quando um inimigo erra, Victor gasta a segunda reação em Riposte e desativa o Escudo para golpear. No segundo, o inimigo E2 age na rodada bônus, ambos concentram dano em Victor, uma rolagem Fast Strikes erra os dois alvos na quarta rodada e Victor cai na quinta.

Reprodução, a partir da raiz do projeto:

```powershell
python -m unittest discover -s tests -q
python -m scripts.group_experiment --stage dev
python -m scripts.group_experiment --stage description
python -m scripts.group_replay --scenario G2_two_rank3_brawlers --policy group_bare_fast --index 8 --output results/group_demo_fast_loss_8.json
```

Este estudo demonstra um subsistema de grupo auditável **dentro do contato fixo**. A missão maior ainda requer posições individuais, prioridade entre múltiplas reações simultâneas, oponentes com poderes, Focus, obstáculos e cenários que desafiem a defesa do Escudo. As taxas acima não mudam a recomendação condicional para os duelos do relatório principal.
