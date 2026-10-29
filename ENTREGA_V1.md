# Blacklight — primeira versão estável, v1.0.0

Esta entrega reúne uma base de simulação e pesquisa para Victor Halle, Rank 3. A estabilidade vale para o **recorte certificado de duelos físicos entre duas fichas compatíveis** e o corredor limitado descritos em [CERTIFICACAO_FUNDACAO.md](CERTIFICACAO_FUNDACAO.md). O pacote também contém pesquisas e funções experimentais claramente identificadas: elas não recebem automaticamente a mesma certificação.

## Como usar agora

- Para jogar com Victor, comece pelo [guia provisório de mesa](GUIA_PROVISORIO_ATUAL.md). Ele descreve as armas, Fast Strikes, Escudo, Riposte, cura e Ram conforme as decisões disponíveis, e explica onde ainda há dúvidas.
- Para entender a ficha e a origem dos dados, consulte [auditoria da ficha](CHARACTER_AUDIT.md) e [registro de regras](RULES_AUDIT.md).
- Para executar o programa, veja as instruções do [README](README.md). É um projeto em Python com execução por comandos, não um aplicativo com interface gráfica. Não é necessário comprar um serviço para executar localmente.
- Para ver o estado de cada parte, consulte [estado do projeto](PROJECT_STATUS.md); para reproduzir ou comparar resultados, consulte [versionamento dos resultados](RESULT_VERSIONING.md).

## O que foi produzido

1. **Motor de duelos e corredor:** testes d616, dados de dano da mesa, movimento e ações, recursos, condições e reações. O Fast Strikes atual faz um teste por braço e permite escolher um único braço para os efeitos de arma. Armas, poderes e combinações são cobertos somente dentro dos limites registrados.
2. **Fichas externas ao motor:** Victor e personagens compatíveis são carregados de registros versionados. Mecânicas desconhecidas ou incompatíveis com o adaptador são bloqueadas, em vez de serem inventadas. Uma ficha nova exige importação e conferência; ela não garante que os poderes novos já estejam implementados.
3. **Pesquisa e evidências:** foram feitas comparações de estratégias com dados reproduzíveis, trilhas, sementes, intervalos de incerteza e adversários sintéticos. Os estudos anteriores às mudanças do mestre continuam guardados como históricos. O estudo atual mais forte usa 120.000 inícios de combate em três cenários específicos, não representa todos os combates possíveis.
4. **Proteções de qualidade:** testes automatizados, auditores independentes em escopos definidos, identificação das regras e fontes, preservação de resultados e [testes automáticos no GitHub](.github/workflows/tests.yml). Nenhum desses mecanismos garante ausência de todos os erros ou que o simulador represente todo o RPG.
5. **Expansões experimentais:** grupo e posições, ataques a Focus, poderes e reações, agarrão, Ram e recortes de Crossbones. O Mental Punch combinado com Fast Strikes atual está documentado em [seu experimento](MENTAL_PUNCH_SPLIT_EXPERIMENT.md); não é um personagem oficial completo nem parte da certificação do duelo físico. A interpretação de agarrão solicitada pelo usuário está [registrada separadamente](GRAPPLE_TABLE_INTERPRETATION.md).

## O que os resultados indicam para a mesa

Na [reserva dos duelos físicos atuais](CURRENT_DUEL_HOLDOUT_REPORT.md), Fast Strikes de Marreta + Lâmina escolhendo o efeito da Marreta superou Marreta comum nos dois espelhos avaliados. No espelho com Lâmina, as taxas foram 56,17% e 43,86%, respectivamente. Isso é uma indicação para situações semelhantes às testadas, não uma estratégia universal. Contra o atirador que recua, muitos duelos chegaram ao limite sem vencedor; essa bateria não incluía Ram.

Uma [exploração posterior de Ram](RAM_CROSSBONES_EXPLORATION_REPORT.md) mostrou mais vitórias dentro de 30 rodadas contra uma política específica de recuo, mas muitos combates continuaram inconclusivos. Crossbones estava representado por um recorte incompleto e o Escudo protegia contra a munição usada. Esses números não provam que Ram, uma arma ou uma política seja melhor em toda mesa. Os estudos de agarrão também não distinguiram as políticas pela taxa de vitória no cenário testado.

**Recomendação prática:** use Fast com efeito de Marreta como uma opção de combate próximo, considere Lâmina quando seus efeitos forem mais úteis e proteja Health com Escudo quando a ameaça justificar a reação. Ajuste à situação; dano de Focus não é reduzido pelo Escudo ou Sturdy. O [guia](GUIA_PROVISORIO_ATUAL.md) detalha condições, custos e cálculos.

## Limites e próximos passos

- O motor ainda **não implementa todo o Marvel Multiverse RPG**. Fichas oficiais completas, todas as habilidades e equipamentos, políticas realmente adaptativas, Karma, múltiplos inimigos, mapas gerais e efeitos numéricos de membros precisam de desenvolvimento e validação.
- As extensões experimentais precisam ser integradas e confrontadas entre si antes de fundamentar estudos confirmatórios. Ram próximo ao limiar de morte continua dependente de decisão; outras ambiguidades estão no registro de regras.
- Para um Victor de Rank superior ou outro personagem, é possível começar por uma ficha nova; poderes, níveis ou combinações ainda não suportados serão apontados e exigirão implementação adicional. Não há progressão inventada para Victor.
- Estudos futuros devem comparar inimigos e cenários mais variados, com Focus, terreno, grupos, decisões adversárias e novas amostras reservadas. Só então será possível fortalecer as recomendações; as amostras históricas não devem ser tratadas como se usassem as regras atuais.
- A entrega atual é um **marco inicial de escopo limitado**, não a conclusão da missão mais ampla de descobrir a melhor estratégia em todas as situações.

## Verificação desta entrega

Em Windows, `python -B -m unittest discover -s tests -q` executou **611 testes com sucesso**. Isso inclui verificações da extensão experimental de Mental Punch; testes aprovados não ampliam a certificação da Fundação. Os demais procedimentos e suas fronteiras constam na documentação técnica.
