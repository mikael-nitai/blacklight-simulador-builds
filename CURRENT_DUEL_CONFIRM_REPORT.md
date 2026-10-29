# Confirmação de estratégias nos duelos físicos atuais

Foram executados 120.000 inícios: quatro políticas em três cenários sintéticos,
com 10.000 inícios por célula. O [plano](CURRENT_DUEL_CONFIRM_SPEC.md) e sua
[emenda anterior à execução](CURRENT_DUEL_CONFIRM_AMENDMENT.md) definiram as
15 comparações. Todas as trilhas foram auditadas durante a execução. Os arquivos
preservam as sementes e métricas por início, não os logs completos de todos os
combates. Os resultados foram vinculados ao commit de fontes `3ee42f9`;
os 64 resultados do inventário passaram na verificação de fontes.

| Política | Espelho em contato | Rank 4 físico | Atirador no corredor |
|---|---:|---:|---:|
| Desarmado, Escudo reativo | 5,03% | 93,29% | 100,00% |
| Marreta comum, Escudo reativo | 39,65% | 98,51% | 100,00% |
| Fast Marreta + Lâmina, efeito Marreta | 50,52% | 99,75% | 100,00% |
| Fast Marreta + Lâmina, efeito Lâmina | 46,06% | 99,72% | 100,00% |

As porcentagens são vitórias observadas no modelo; em todas as células houve
apenas vitórias e derrotas, sem empates ou resultados inconclusivos. O espelho é
uma cópia sintética de Victor com Fast e efeitos da Marreta, não um personagem
oficial. Os demais adversários também são sintéticos. O corredor limita o
movimento; o ataque do atirador não é classificado como munição.

No espelho, as duas variantes de Fast superaram a Marreta comum no critério
pré-registrado. A diferença observada foi **10,87 pontos percentuais** para o
efeito da Marreta, com intervalo conservador ajustado **7,10 a 14,64 pontos**;
para o efeito da Lâmina, **6,41 pontos**, intervalo **2,64 a 10,18 pontos**.
A primeira superou a segunda em **4,46 pontos**, intervalo **0,69 a 8,23 pontos**.
Esses resultados apoiam essa escolha somente no cenário e nas políticas testados.

Contra o físico Rank 4, ambas superaram o controle desarmado, mas a diferença
em relação à Marreta comum e entre as duas variantes ficou inconclusiva pelo
critério conservador. No corredor, todas venceram 10.000 vezes; isso não prova
probabilidade de vitória de 100% e não permite distinguir as políticas. O limite
inferior Wilson individual de 95% é aproximadamente 99,96% para cada célula.

Os intervalos para diferenças usam Hoeffding/união com `alpha = 0,05/15` em
cada uma das 15 comparações. Sua interpretação depende do modelo de inícios
independentes. Intervalos individuais Wilson são descritivos, sem ajuste
simultâneo; intervalos Newcombe/Wilson ajustados constam como aproximação no
arquivo de análise. Diferenças cujos intervalos conservadores incluem zero são
tratadas como inconclusivas, não como equivalência comprovada.

O [arquivo de análise](experiments/current_duel_study/confirmation_analysis_v1.json)
registra as comparações, todos os desfechos, métricas e hashes de entrada. A
reserva em cenários novos ainda não foi executada. Focus, Karma, adversários
oficiais completos, grupos validados e várias opções táticas continuam fora
deste recorte; as ambiguidades de Run/iniciativa e da ordem de algumas regras
permanecem registradas no [pré-registro](CURRENT_DUEL_STUDY_SPEC.md). Nenhum
resultado aqui estabelece uma estratégia ótima para toda a campanha.
