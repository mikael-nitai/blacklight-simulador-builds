# Pré-registro exploratório: escapar ou atacar durante um agarrão

## Pergunta e recorte

Quando o recorte parcial de Crossbones usa Grappling Technique contra o Victor
Rank 3 fornecido, como duas políticas explícitas se comportam neste host de
duelo? O experimento não usa ficha oficial completa e não estabelece uma
estratégia ótima; sua finalidade é produzir hipóteses para contramedidas e
confirmação em cenários independentes.

Campo aberto unidimensional, distância inicial de um espaço, até 30 rodadas.
O recorte de Crossbones usa os poderes implementados no adaptador de Grappling,
submetralhadora contra um alvo, preferência por Grappling quando legal e por
atacar enquanto segura; pode tratar Bleeding, usar Point-Blank Parry e Fast
Hands. Victor usa Fast Strikes com Marreta e Lâmina, selecionando os efeitos da
Marreta, e Escudo reativo. Ram é desativado para ambos neste experimento.

As duas políticas de Victor são: **escapar**, que tenta Escape por reação ao
ser agarrado quando permitido e como ação padrão enquanto permanecer
agarrado; e **atacar**, que não tenta Escape por reação e prioriza Fast Strikes
enquanto estiver agarrado. Ambas usam as mesmas escolhas fora do agarrão.
Isso compara políticas completas, não o efeito isolado de apenas uma decisão.

## Variantes e sementes

Executar a grade fixa de oito células: duas políticas × duas hipóteses para
trouble de ataque entre os participantes × duas hipóteses para a identidade
do gatilho entre Escudo e Escape. As hipóteses não são decisões da mesa.
São 1.000 inícios por célula, com o mesmo conjunto de sementes nas oito
células. Cada seed é derivada de SHA-256 do nome fixo do estudo e do índice,
sem reutilizar sementes de confirmação anteriores. Isso permite comparação
pareada de execuções, mas não garante que eventos diferentes consumam a mesma
sequência de dados em cada variante.

## Métricas, integridade e limites

Registrar todos os inícios: vitória, derrota, empate e inconclusivo no limite
de rodadas; Health e Focus finais; número de agarrões iniciados, bem-sucedidos
e fantásticos, fugas por reação e padrão, e ataques enquanto agarrado. A taxa
de vitória é `vitórias / 1.000`, acompanhada de Wilson 95% individual. Também
registrar quantos combates tiveram pelo menos um agarrão, para não confundir
efetividade global com frequência de exposição. O subconjunto que foi agarrado
é descritivo: condicionar nele não prova um efeito causal. Não selecionar uma
vencedora com base apenas na maior taxa nem interpretar intervalos individuais
como teste de diferença pareada ou corrigido por múltiplas comparações.

Cada duelo concluído deve passar pelo auditor de reações, agarrão e dano. Uma
exceção não prevista interrompe o estudo; ela não será descartada ou contada
como vitória/derrota. O histórico completo não será gravado para cada duelo:
cada registro mantém seed e hash do resultado integral, mais métricas e
desfecho. Um auditor independente verifica contas, sementes, identidade das
políticas e snapshots. Após a execução, reproduzir os índices 0, 500 e 999
de cada célula e comparar o registro completo, com arquivos novos fora do
inventário certificado. Preservar fontes, especificação, commit imutável e
versão/implementação de Python; a reprodução exige o mesmo ambiente registrado.

O host não resolve autoacerto numa falha contra o outro envolvido, terceiros,
transporte, knockback durante o agarrão, todos os poderes de Crossbones, Karma
ou o conjunto de adversários da campanha. Supõe que o agarrão persiste quando o
agarrador fica Stunned. Esses limites podem alterar os resultados. A diferença
entre Escudo e Escape como gatilhos permanece uma hipótese explicitamente
identificada em cada célula. O estudo é exploratório, não uma confirmação.

Os exemplos históricos `entangled_attack_demo_v1.json` e
`entangled_reaction_demo_v1.json` conservaram uma descrição herdada que diz
incorretamente que ataques no agarrão são bloqueados, embora seus hosts os
permitissem. Seus arquivos e fontes não foram alterados. Este estudo usa um
adaptador separado que corrige essa descrição; isso não altera os cálculos
nem corrige retroativamente os metadados dos exemplos históricos.
