# Exploração: Ram contra recorte parcial de Crossbones

Estudo exploratório de 12.000 inícios, conforme o [pré-registro](RAM_CROSSBONES_EXPLORATION_SPEC.md), com 1.000 por combinação. O adversário é um **recorte incompleto** da ficha oficial, com duas políticas simples, em campo aberto unidimensional e até 30 rodadas. Victor tem Escudo reativo em todas as políticas. Permitir Ram não obriga seu uso: a política o emprega quando a situação permite, e conserva Escudo ativo quando já ativado.

| Adversário | Ataque de Victor | Ram permitido | Vitórias | Inconclusivos | Usos de Ram |
|---|---|---:|---:|---:|---:|
| Estacionário | Marreta | Não | 1.000 | 0 | 0 |
| Estacionário | Marreta | Sim | 1.000 | 0 | 637 |
| Estacionário | Fast, efeito Marreta | Não | 1.000 | 0 | 0 |
| Estacionário | Fast, efeito Marreta | Sim | 1.000 | 0 | 637 |
| Estacionário | Fast, efeito Lâmina | Não | 1.000 | 0 | 0 |
| Estacionário | Fast, efeito Lâmina | Sim | 1.000 | 0 | 637 |
| Recuo | Marreta | Não | 47 | 953 | 0 |
| Recuo | Marreta | Sim | 416 | 584 | 676 |
| Recuo | Fast, efeito Marreta | Não | 64 | 936 | 0 |
| Recuo | Fast, efeito Marreta | Sim | 418 | 582 | 672 |
| Recuo | Fast, efeito Lâmina | Não | 73 | 927 | 0 |
| Recuo | Fast, efeito Lâmina | Sim | 418 | 582 | 673 |

Não houve derrotas, empates ou casos no limiar de morte por autoimpacto nesta amostra; isso não resolve a regra pendente nem prova que esses resultados sejam impossíveis. A imunidade do Escudo a munição, confirmada para esta mesa, é uma característica importante desse confronto contra submetralhadora. As vitórias contam apenas até a 30ª rodada; inconclusivos não são derrotas. Como nenhuma observação atingiu a regra pendente, os limites de identificação de vitória coincidem com a proporção registrada em cada célula; os intervalos Wilson individuais, sem ajuste para comparações múltiplas, constam nos dados.

Sob a política de recuo, permitir Ram esteve associado a mais vitórias dentro do prazo para as três estratégias, mas ainda houve 582–584 inconclusivos por 1.000. Isso sugere uma hipótese sobre aproximação a examinar em cenários novos; não é prova de vantagem geral de Ram nem demonstra qual arma é melhor. As células usam sementes pareadas e as políticas diferem apenas nos parâmetros descritos; os intervalos individuais não são testes das diferenças pareadas. Contra o adversário estacionário todas venceram dentro do prazo, o que impede distinguir as estratégias por taxa de vitória nesta amostra.

Cada duelo concluído passou pelos auditores do host; fontes e contagem foram conferidas separadamente. Uma verificação reproduziu os índices inicial, central e final de cada célula (36 registros), comparando os dados individuais. Isso não substitui uma reprodução integral independente nem cobre todos os comportamentos e poderes. Os casos excepcionais de morte por autoimpacto teriam sido registrados separadamente e seu prefixo reproduzido, mas não ocorreram nesta execução.

- [Dados experimentais individuais](experimental_outputs/ram_crossbones_explore_v1.json): SHA-256 `225097014e9c608813889d3ba2fa88fc68949bf79023adcaf4c757e66d4c8e29`.
- [Reprodução da amostra fixa](experimental_outputs/ram_crossbones_explore_replay_v1.json): SHA-256 `e06ad511c144e119dc2455864cfe3bb5ee488efddcf7360c7c89ce1a600b9d63`.
- Fontes congeladas no commit `b483568d46f19f4784287608a341c9452ed4ab5a`. A tentativa anterior interrompida está registrada no pré-registro; nenhum agregado dela foi publicado ou observado.
