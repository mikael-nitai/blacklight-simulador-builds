# Reserva: estratégias nos duelos físicos atuais

Os três cenários foram previstos antes da exploração; o
[plano operacional](CURRENT_DUEL_HOLDOUT_SPEC.md) foi registrado após a
confirmação e antes de executar esta reserva. São 12 células de 10.000 inícios,
120.000 ao todo, com auditoria de cada combate. Os resultados foram vinculados
ao commit de fontes `4c9a5df`; o inventário de 76 resultados passou na
verificação de fontes. Os arquivos preservam seeds e métricas por início, não
as trilhas completas de todos os combates.

| Política | Espelho com Lâmina: vitórias | Rank 4 Sturdy 2: vitórias | Atirador aberto: vitórias | Atirador aberto: sem vencedor |
|---|---:|---:|---:|---:|
| Desarmado, Escudo reativo | 5,44% | 86,72% | 0,00% | 66,85% |
| Marreta comum, Escudo reativo | 43,86% | 97,38% | 4,47% | 63,30% |
| Fast Marreta + Lâmina, efeito Marreta | 56,17% | 99,56% | 4,81% | 63,26% |
| Fast Marreta + Lâmina, efeito Lâmina | 51,91% | 99,41% | 4,12% | 64,10% |

Na última coluna, **sem vencedor** significa que o limite técnico de 30 rodadas
foi alcançado; não significa derrota. Contra o atirador, as derrotas foram,
respectivamente, 33,15%, 32,23%, 31,93% e 31,78%. Não houve empates. Nos
outros dois cenários houve apenas vitórias e derrotas.

No espelho, ambas as finalistas superaram Marreta comum no critério
pré-registrado. O efeito da Marreta teve vantagem de **12,31 pontos
percentuais** sobre Marreta comum (intervalo conservador ajustado **8,54 a
16,08**) e de **4,26 pontos** sobre o efeito da Lâmina (**0,49 a 8,03**).
Contra o físico Sturdy 2, ambas superaram o controle desarmado, mas comparações
com Marreta comum e entre finalistas foram inconclusivas pelo intervalo
conservador. No campo aberto, as duas finalistas tiveram mais vitórias que o
controle desarmado; as comparações com Marreta comum e entre finalistas foram
inconclusivas. Isso não é prova de equivalência entre políticas.

A família de 15 diferenças usa Hoeffding/união com `alpha=0,05/15` por
comparação; uma diferença foi considerada sustentada apenas se seu intervalo
conservador excluiu zero. A cobertura depende do modelo de inícios independentes
e não certifica o motor ou a representatividade dos cenários. Wilson individual
de 95% e intervalos Newcombe/Wilson ajustados constam no
[arquivo de análise](experiments/current_duel_study/holdout_analysis_v1.json).

Os adversários são **sintéticos**, não fichas oficiais completas. O atirador
recua em campo aberto unidimensional e usa um ataque genérico que não é
classificado como munição. Mais importante, o motor desta bateria não oferece
a reação básica **Ram**, que pode dar a Victor outra opção ao alcançá-lo após
dois movimentos. A [revisão da lacuna](RAM_REVIEW.md) e a
[investigação adversarial](ADVERSARIAL_REVIEW_CURRENT.md) mostram por que as
taxas de campo aberto não podem ser generalizadas para a mesa. Terreno real,
Focus, Karma, outros poderes e adversários também permanecem fora do recorte.

Em conjunto com a confirmação, estes dados sustentam a opção de Fast com efeito
da Marreta **nos dois espelhos avaliados**. Eles não estabelecem uma estratégia
ótima universal nem respondem como Victor se sairia com Ram implementado.

Três exemplos completos e auditados estão disponíveis para inspeção: [espelho](experiments/current_duel_study/demos/mirror_blade_v1.json),
[oponente resistente](experiments/current_duel_study/demos/rank4_sturdy2_v1.json)
e [atirador em campo aberto](experiments/current_duel_study/demos/gunner_open_v1.json).
Foram fixados por seeds próprias para ilustrar a execução, não fazem parte das
amostras estatísticas e não são necessariamente combates representativos. Os
hashes de fontes e os logs completos foram conferidos por repetição.
