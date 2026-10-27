# Duelo experimental contra dano de Focus

**27/10/2026.** Este estudo é separado dos [duelos físicos confirmatórios](REPORT.md). Usa o [gate normativo](FOCUS_SPEC.md) e o [pré-registro](FOCUS_DUEL_SPEC.md), ambos apoiados no *Core Rulebook* fornecido pelo usuário (pp.33–34, 38 e 108) e na [FAQ oficial de março/2025](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20250327.pdf). O adversário é **sintético**, sempre ao alcance de Victor, e usa exclusivamente Mental Punch. Essa ação Melee reduz Focus, dobra dano e aplica Stunned em sucesso fantástico. Focus 0 impõe Demoralized/trouble; Focus ≤−90 deixa Victor Shattered e encerra o combate como derrota. Sturdy 1 protege Health, não Focus.

## A decisão de mesa que muda o resultado

Após este experimento, o usuário [esclareceu a regra da mesa](FOCUS_RULING.md): o Escudo reduz **somente dano de Health**. Portanto, **F0** é a variante aplicável a Mental Punch; **F2** permanece na tabela apenas como análise contrafactual da hipótese investigada antes do esclarecimento. A decisão posterior não altera as amostras nem torna F2 legal na mesa. As sementes de F0 e F2 são independentes; o mesmo índice de amostra não forma um par causal.

Victor usa Marreta em todas as políticas. `hammer` não ativa Escudo; `shield_reactive` o ativa após ver um acerto; `shield_endturn` o ativa ao fim do turno e após acerto se ainda estava desativado. Riposte é usado quando há reação. Dois perfis sintéticos foram testados: M3, Mental Punch Rank 3; M4, Rank 4. Ambos têm Melee 6, defesa Melee 16 e Health 150. Cada célula teve 1000 combates de desenvolvimento e 5000 novos para a tabela. O recorte não tem movimento, terreno, Karma, cura de Focus, aliados ou opções alternativas para o telepata.

| Inimigo | Variante | Política | Vitórias / 5000, IC Wilson 95% | Demoralized alguma vez | Focus final médio |
|---|---|---|---:|---:|---:|
| M3 | F0 | Marreta | 4.881; 97,62% [97,16; 98,01] | 13,06% | 50,2 |
| M3 | F0 | Escudo reativo | 4.888; 97,76% [97,31; 98,13] | 12,66% | 50,4 |
| M3 | F0 | Escudo no fim do turno | 4.873; 97,46% [96,99; 97,86] | 13,00% | 50,3 |
| M3 | F2 | Marreta | 4.880; 97,60% [97,14; 97,99] | 13,56% | 49,5 |
| M3 | F2 | Escudo reativo | 5.000; 100,00% [99,92; 100,00] | 1,58% | 69,7 |
| M3 | F2 | Escudo no fim do turno | 4.999; 99,98% [99,89; 100,00] | 1,40% | 70,0 |
| M4 | F0 | Marreta | 4.738; 94,76% [94,11; 95,34] | 18,92% | 40,7 |
| M4 | F0 | Escudo reativo | 4.729; 94,58% [93,92; 95,17] | 19,64% | 39,7 |
| M4 | F0 | Escudo no fim do turno | 4.740; 94,80% [94,15; 95,38] | 18,72% | 41,9 |
| M4 | F2 | Marreta | 4.734; 94,68% [94,02; 95,27] | 19,14% | 40,7 |
| M4 | F2 | Escudo reativo | 4.975; 99,50% [99,26; 99,66] | 6,32% | 59,8 |
| M4 | F2 | Escudo no fim do turno | 4.967; 99,34% [99,07; 99,53] | 6,58% | 59,9 |

Não houve inconclusões; as lutas restantes terminaram em Shattered. A política Marreta foi amostrada de novo em F0 e F2 mesmo sendo mecanicamente idêntica nessas variantes, pois as sementes são diferentes. Na variante **F0 válida para a mesa**, os resultados **não** mostram benefício claro do Escudo contra este dano de Focus. Sob F2, agora **contrafactual**, o Escudo reduziria o risco de Shattered e Demoralized. O inimigo só dispõe de um poder e permanece em contato, então essas taxas não se transportam para telepatas que recuam, usam controle, trazem aliados ou atacam outros recursos.

## Auditoria e demonstrações

A suíte passou em **84 testes**, com oráculos forçados para acerto, fantástico, falha fantástica, Ultimate, DR de Focus, limiares de Demoralized/Shattered, proteção Heroic, Escudo antes do dano, trouble após Focus 0, Riposte e duração de Stunned. O auditor independente recalculou **300 trilhas completas da suíte** e **600 da amostra descritiva**, incluindo Health/Focus, dano, orçamento de reações, estado final e integridade do resultado. O [JSON de desenvolvimento](results/focus_dev_summary.json) e o [JSON descritivo](results/focus_description_summary.json) contêm perfis, contagens, sementes, intervalos e hashes. Há duas [trilhas completas auditadas: F0 com derrota](results/focus_demo_M4_F0_loss_28.json) e [F2 com vitória](results/focus_demo_M4_F2_win_28.json). Elas ilustram sequências possíveis, **não** são contrafactuais pareados.

Reproduzir na raiz do projeto:

```powershell
python -m unittest discover -s tests -q
python -m scripts.focus_experiment --stage dev
python -m scripts.focus_experiment --stage description
python -m scripts.focus_replay --scenario M4 --variant F0 --strategy shield_reactive --index 28 --output results/focus_demo_M4_F0_loss_28.json
```

Contra Mental Punch na mesa atual, **não conte com a redução do Escudo nem de Sturdy 1 para proteger Focus**. Ativar o Escudo ainda pode ser útil contra dano de Health de outras fontes, mas contra esse telepata isolado as três políticas F0 tiveram resultados próximos dentro da incerteza. As recomendações físicas do guia principal continuam restritas aos adversários físicos testados.
