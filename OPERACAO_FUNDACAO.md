# Operação Fundação: diagnóstico e passagem

Registro de trabalho de 28/10/2026, consolidado para passagem. Esta avaliação
tem escopo limitado: não certifica todo o RPG. As conclusões se referem aos
arquivos e às verificações identificados abaixo.

## Preservação e contexto

- O repositório estava em `9bb30df`, com quatro arquivos modificados e
  `combatants/group.py` novo. O checkpoint `bfac81b` preserva exatamente esse
  trabalho interrompido e o identifica como migração de grupo não concluída.
- Uma cópia de recuperação anterior ao checkpoint inclui `.git`, arquivos
  rastreados, não rastreados e ignorados. Seus 971 arquivos foram comparados por
  SHA-256 com o ZIP `Simulador Builds - recuperacao-fundacao-20261028-012346.zip`,
  na pasta acima do repositório. SHA-256 do ZIP:
  `f729de3dcdfeec91ce90930f8e9ce125473df38c632f51918ee81f1bb98473d9`.
- Não foi encontrado `AGENTS.md` aplicável à pasta ou aos seus pais. A conversa
  de desenvolvimento anterior foi consultada: a migração de grupo foi
  interrompida, e o usuário confirmou que cada braço de Fast Strikes pode
  escolher um alvo diferente, mantendo dois testes e efeitos apenas do braço
  escolhido. Essa confirmação é posterior aos documentos que chamam a
  distribuição de alvos de pendente.
- O repositório remoto privado é
  [mikael-nitai/blacklight-simulador-builds](https://github.com/mikael-nitai/blacklight-simulador-builds).

## O que existe e o que as evidências sustentam

| Área | Estado observado | Limite da evidência |
|---|---|---|
| Duelo físico atual | `SplitFastDuel` usa dois testes e um braço de efeitos; há casos com dano calculado à mão em `tests/test_split_fast.py`. | É um recorte de duas fichas, não a totalidade das regras ou uma prova de estratégia ótima. |
| Corredor atual | Usa o mesmo ataque com geometria 1D e testes próprios de movimento. | Não cobre mapa geral, colisões, cobertura ou knockback. |
| Grupo | `experimental/group.py` preserva o contrato anterior; `combatants/group.py` é a migração interrompida. Agora há testes específicos de casos limitados e 1.000 sementes sintéticas executadas sem erros do auditor reforçado. | O auditor tem pontos cegos descritos abaixo; há um desvio de desempate de iniciativa, e a migração não está pronta para medições de eficácia. |
| Focus e estudos antigos | Existem protótipos e resultados históricos documentados. | Resultados `pool_v2` precedem o último balanceamento de Fast Strikes e não medem a regra atual. |
| Proveniência | Em `python -B -m scripts.verify_sources`, 37 resultados congelados passaram na conferência dos hashes declarados e dos commits. | Isso verifica os arquivos declarados, não a fidelidade das regras nem a validade das conclusões. Apenas 6 dos 37 registros têm `table_ruleset` explícito; os demais dependem dos registros históricos. A varredura principal cobre JSONs na raiz de `results/`, não todos os arquivos de subpastas. |
| Testes | A linha de base teve 228 testes; após as correções, 263 passaram no Windows e no Ubuntu via WSL. | Os testes da migração de grupo cobrem casos específicos. Exemplos adversariais demonstraram que o auditor não detecta toda inconsistência, e quantidade de testes não é garantia de correção. |

A conferência pontual do Core local, página impressa 99, distingue o Fast
oficial de teste único da exceção da mesa em `FAST_STRIKES_RULING.md` e HR-09.
O Core, a [FAQ oficial](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Rules-FAQ_20250327.pdf),
a [errata oficial](https://cdn.marvel.com/u/prod/marvel/i/pdf/MMRPG_Errata_20250718.pdf)
e as decisões da mesa têm papéis diferentes. A confirmação de dois alvos não
decide detalhes ainda não esclarecidos, como regras numéricas de membros.

## Achados priorizados antes das correções

1. **Alto — resultado histórico pode ser sobrescrito.**
   `scripts/replay.py` grava no caminho informado sem exclusividade; uma
   reprodução em diretório temporário substituiu um arquivo existente. Outros
   comandos, inclusive `blacklight/search.py` e `blacklight/sensitivity.py`,
   usam nomes históricos fixos com `write_text`. Isso contradiz a orientação
   geral do README e pode destruir dados ou mascarar sua versão. Mapear e
   proteger os caminhos de escrita; não modificar os resultados existentes.
2. **Alto — auditoria insuficiente para afirmar legalidade completa.**
   Ao alterar uma trilha real para atribuir 99 reações a cada participante,
   `blacklight.audit.audit_log` não identificou o problema: sua interface recebe
   Health e Focus, mas não as capacidades que determinam o limite de reações.
   A aritmética e a sequência que ele verifica continuam úteis, porém `audit=OK`
   não comprova sozinho todas as regras.
3. **Médio — movimento inválido aceito no campo aberto.**
   Com `Move('retreat', 0.5)` o motor alterou a distância de 3 para 3,5 e gastou
   movimento; `True` também foi aceito como quantidade. O auditor retornou
   zero problemas. O corredor já rejeita esses tipos. Isso pode distorcer
   alcance e comparações quando uma política fornece dados inválidos.
4. **Médio — versões de regras e grupos podem ser confundidas.**
   O README chama `pool_v2` de histórico no início e de atual na lista de
   arquivos. `RULES_AUDIT.md` e `FAST_STRIKES_RULING.md` ainda dizem que dois
   alvos dependem de confirmação, já obtida na conversa anterior. A existência
   de dois motores de grupo é justificável pela preservação histórica, mas o
   novo arquivo precisa ser marcado como incompleto até ter testes próprios.
5. **Médio — adaptabilidade e procedência exigem mais controle.**
   Ações de cura/estado são declarativas, mas Fast, efeitos das armas, reações
   e partes dos auditores ainda dependem de condições especializadas no motor.
   Mudanças em regras exigem rever testes, auditor e identificação dos
   experimentos. Fontes externas transitivas de políticas personalizadas não
   são automaticamente registradas; o próprio runner explicita essa limitação.
6. **Alto — caminhos históricos dependem do sistema operacional.**
   Resultados congelados contêm nomes como `blacklight\\engine.py`. Em sistemas
   POSIX essa sequência é um nome único, enquanto no Git a fonte é
   `blacklight/engine.py`. A referência do Git com barra invertida falhou e a
   mesma referência com barra normal funcionou. Os resultados precisam continuar
   intactos; o verificador deve entender ambos os formatos.
7. **Médio — fórmula de semente declarada em scripts antigos.**
   `holdout.py`, `secondary_metrics.py` e `adversarial_scenarios.py` chamavam
   `seed_for`, que usa o prefixo `blacklight-pool-v2`, mas declaravam
   `blacklight-v1` em novas saídas. Os JSONs históricos não foram alterados.
8. **Alto — intervalo de diferenças pode perder toda a incerteza.**
   A comparação Wald em `blacklight.experiment.comparisons` devolveu `[0, 0]`
   para duas amostras independentes de 10 vitórias em 10 combates. Mesmo com
   resultados iguais, essas amostras não provam igualdade exata das taxas.
   A correção deve afetar novas análises; os resultados congelados permanecem
   históricos e devem ser interpretados conforme o método que os produziu.
   Foram encontrados 23 desses intervalos em 10 arquivos históricos; dois
   aparecem em `confirm_summary.json`, um em `pool_v2_dev_summary.json` e
   sete em `pool_v2_smoke_summary.json`.
9. **Alto para a expansão de grupo — desempate de iniciativa incompleto.**
   ACT-02 favorece personagem de jogador quando os critérios anteriores empatam.
   `blacklight/engine.py::_initiative` usa a posição na lista no desempate final;
   `combatants/group.py` herda isso, mas não identifica quais fichas são de
   jogadores. Se um NPC vier antes de um personagem de jogador, a ordem pode
   contrariar a regra. Em duelos em que o jogador está na primeira posição,
   a escolha por índice coincide nesse caso. Não é seguro inferir jogador/NPC
   a partir do time ou inventar como resolver empate entre jogadores.

Os achados 1, 3, 6, 7 e 8 foram reproduzidos. O item 2 é uma limitação
demonstrada do verificador, não uma prova de que os combates já executados
tiveram 99 reações. O item 9 decorre do contrato de desempate do código e da
ausência de identificação jogador/NPC. Os itens 4 e 5 são riscos de
interpretação/manutenção, não autorização para reescrever os motores ou
modificar as regras da mesa.

## Sequência de fortalecimento

1. Impedir substituição de resultados e pedir nomes novos nas saídas históricas.
2. Rejeitar movimentos inválidos antes de gastar ação; reforçar o auditor com
   limites independentes conhecidos e testes que falsificam trilhas.
3. Corrigir referências de regras e sinalizar claramente o grupo incompleto.
4. Conferir a classificação e a procedência dos resultados, os scripts
   estatísticos e um ensaio isolado de mudança hipotética de regra.
5. Executar testes completos e verificações adversariais adicionais. Atualizar
   esta passagem com alterações, evidências, restrições e decisão de prontidão.

## Primeira correção: preservação das saídas

Os caminhos de geração de JSON, demonstrações e replays agora criam arquivos
com exclusividade. As buscas e estudos antigos exigem destino novo e aceitação
explícita das regras históricas; o relatório e as figuras também precisam de
novos destinos quando os arquivos originais existem. Isso não altera os dados
já arquivados. Os scripts de reserva, métricas secundárias e adversários também
passaram a declarar o prefixo de semente efetivamente usado em novas saídas.

Quatro testes direcionados passaram, incluindo reprodução real com recusa de
uma segunda gravação, cinco comandos antigos apontados a um arquivo já existente
e duas gravações simultâneas disputando o mesmo nome. A criação exclusiva
impede substituir um arquivo existente; uma interrupção durante a escrita pode
deixar uma saída nova incompleta, que não deve ser tratada como resultado válido.

## Segunda correção: caminhos de proveniência

Novos manifestos usam caminhos relativos ao projeto com `/`. O verificador lê
as barras invertidas dos registros antigos e contém duas correspondências
explícitas para os caminhos absolutos de fichas que aparecem em três resultados;
cada correspondência ainda precisa coincidir com o hash do commit registrado.
Caminhos externos desconhecidos não são convertidos por adivinhação. Os 37
resultados passaram novamente no Windows, no Ubuntu e em uma cópia localizada em
outra pasta. Testes com repositórios Git temporários conferiram também rejeição
de um caminho externo não reconhecido. Os arquivos de resultados históricos não
foram alterados. Isso verifica portabilidade dos caminhos, não garante que todas
as dependências transitivas de uma política externa estejam registradas.

## Terceira correção: movimento e reação

O duelo recusa distâncias iniciais, limites de rodadas e movimentos fracionários
ou booleanos. Movimentos inválidos são recusados antes de consumir ações ou
alterar a distância. O auditor passou a conferir quantidades de movimento e,
quando recebe as fichas, velocidades e quantidade de reações permitidas. O
runner de fichas e os replays físicos fornecem essas capacidades ao auditor.
Uma trilha deliberadamente adulterada para dar 99 reações agora falha; quatro
trilhas antigas de duelo e corredor foram reavaliadas sem divergências.

O auditor ainda não reconstrói todas as capacidades, defesas e efeitos a partir
das fichas; `audit=OK` não certifica a legalidade completa do combate. Se for
chamado diretamente sem os limites opcionais, ele não conhece a velocidade ou
as reações autorizadas. O grupo novo ainda não possui esse runner de produção.

## Quarta correção: incerteza estatística

As novas comparações de vitória entre amostras independentes usam o intervalo
de Newcombe que combina limites de Wilson, com ajuste Bonferroni dentro de cada
cenário. Esse é um método aproximado, não uma garantia de cobertura exata; a
independência e a validade do modelo continuam sendo pressupostos a verificar.
O estudo original do método está em
[Newcombe, 1998](https://pubmed.ncbi.nlm.nih.gov/9595617/). A sensibilidade
passou a usar a mesma abordagem. Para uma única observação, o erro-padrão Monte
Carlo agora é `null`, pois não pode ser estimado pela variância amostral.

Uma enumeração exata de um caso extremo com duas amostras de 10, probabilidades
verdadeiras 0,05 e 1, e intervalo nominal de 95% obteve cobertura de cerca de
91,4% para o intervalo aproximado. Por isso, as novas saídas oferecem também um
intervalo conservador baseado na [desigualdade de Hoeffding](https://doi.org/10.1080/01621459.1963.10500830)
e na união de limites. Ele pode ser bem mais largo; sua garantia depende do
modelo de observações independentes por célula e não prova que o simulador ou os
cenários representem a campanha. O ajuste simultâneo se refere às comparações
dentro de cada cenário, não a todos os cenários conjuntamente.

Todos os 23 intervalos históricos de largura zero puderam ser recalculados em
memória, sem modificar seus arquivos. Por exemplo, no `confirm_summary.json`,
ataque básico e postura contra o atirador registraram cada um 0 vitórias em
10.000 combates: o antigo `[0, 0]` vira aproximadamente
`[-0,000768; +0,000768]` na escala de proporção, com ajuste para as nove
comparações daquela família. Isso não transforma os combates antigos em dados
da regra atual de Fast. Os testes usam casos numéricos independentes, reversão
de ordem das amostras, extremos 0/10 e 10/10, entradas inválidas e amostra única.

## Compatibilidade, grupo e ensaio de mudança

O comando `python -m scripts.result_compatibility --details` verifica antes de
classificar: 6 resultados declaram `split_fast_v3`, 31 pertencem a snapshots
anteriores ao Fast por braço e 36 são escalares no inventário histórico. Os seis
que declaram a regra atual têm ao menos uma fonte listada diferente do projeto
presente. Isso exige revisão ou reprodução com o commit de origem; não prova que
o comportamento relevante mudou. O sistema não infere regras de um resultado
desconhecido. Também verifica as 36 cópias escalares que o inventário declara.
Uma correspondência de hashes não garante completude das dependências, regras
corretas ou conclusões válidas; um cenário antigo que não use Fast pode não ser
afetado por essa regra específica.

Quatro casos manuais da migração de grupo conferiram dano e DR por alvo, efeitos
do braço escolhido, dois Escudos, rejeição de alvo aliado e passagem do turno
inconsciente. Uma bateria adicional de 1.000 sementes em contato fixo passou no
auditor reforçado, e um subconjunto foi incluído na suíte para verificar replay.
Esses controles não cobrem posicionamento, todas as prioridades de reações,
todos os poderes ou uma auditoria independente completa do grupo.

Para testar uma alteração **hipotética**, sem modificar a mesa, aumentamos em
teste a cura por Focus numa definição do registro: 5 Focus curaram 15 em vez de
10, enquanto dez combates sem essa ação mantiveram trilhas idênticas. Outra
injeção hipotética aumentou apenas o bônus de dano de Fast: o auditor detectou a
divergência e o ataque comum permaneceu idêntico. Alterar de verdade a metade de
Fast envolveria pelo menos o cálculo de pools, seu auditor independente, o
campo de divisão no evento, a versão de regras e seus metadados, além de testes
e documentação; o cálculo é compartilhado com o motor histórico. Preservar os
replays antigos exigiria introduzir uma variante versionada, não substituir a
fórmula global. Os testes demonstram esses casos limitados, não isolamento
automático para toda futura regra.

## Quinta correção: procedência durante a execução

Experimentos, replays e demonstrações abrangidos registram suas fontes antes da
execução e recusam publicar o resultado se os hashes declarados mudarem até a
verificação final. As fichas lidas pela linha de comando são analisadas a partir
dos mesmos bytes cujo hash é salvo. Testes injetaram mudanças nas fontes e nas
fichas e verificaram que não houve saída publicada; também conferiram cinco
replays e dois lotes de demonstração. O auditor passou ainda a rejeitar alguns
eventos de ação ou reação atribuídos a um personagem desconhecido ou
inconsciente, e o experimento de corredor usa os limites das fichas na auditoria.

Esse mecanismo compara apenas os arquivos declarados nos dois instantes: não
detecta mudança revertida entre as leituras, código já carregado antes do
primeiro hash ou dependências transitivas externas não declaradas. Para um novo
resultado de referência, registre código e dados em commit, inicie um processo
novo com árvore limpa, preserve também o ambiente e congele a saída conforme
[RESULT_VERSIONING.md](RESULT_VERSIONING.md). Exclusividade do nome impede
sobrescrever um resultado, mas uma interrupção de escrita pode deixar arquivo
novo incompleto.

## Verificação independente e interpretação dos experimentos

- `python -B -m scripts.audit_split_fast` conferiu 108 combinações de resultados,
  casos de cronologia e limites, e rejeitou cinco trilhas adulteradas. Há também
  exemplos calculados à mão nas suítes de Fast e grupo.
- `python -B -m scripts.audit_current_corridor` comparou 50 sementes em contato,
  reviu geometria histórica e verificou 100 situações de mapa. Os motores
  comparados compartilham parte da execução: não são implementações totalmente
  independentes. `python -B -m scripts.audit_modular_lifecycle` verificou 2.352
  casos de ponte de estado, prazos e cinco trilhas congeladas.
- `python -B -m scripts.audit_current_results` conferiu hashes dos seis controles
  atuais, reproduziu exatamente os quatro logs completos e conferiu as sementes,
  contagens e métricas das duas baterias de 1.000 combates. Os registros originais
  das baterias não guardam todos os logs, apenas sementes e agregados; portanto
  não é possível comparar cada evento original. Essas reproduções são controles
  de integração, não testes confirmatórios de qual estratégia é melhor.
- `python -B -m scripts.verify_sources` verifica 37 registros congelados;
  `python -B -m scripts.result_compatibility --details` identifica seis com a
  regra atual declarada, 31 em snapshots anteriores e 36 cópias escalares
  inventariadas. Também identifica conflitos entre declaração e snapshot, sem
  tentar inferir versões de origem desconhecida.

Nos experimentos históricos, cenários e políticas são definidos por célula;
as sementes incluem fase, cenário, política e índice, e células diferentes não
são tratadas como amostras pareadas. Isso ajuda a separar exploração,
confirmação e reserva, mas sementes determinísticas e um gerador
pseudorrandômico são uma aproximação operacional do modelo estatístico, não uma
prova matemática de independência. A seleção de políticas após explorar
resultados requer confirmação separada; a reserva H2 corrigida foi exposta e é
exploratória, como registra [HOLDOUT_SPEC.md](HOLDOUT_SPEC.md). Nenhum desses
resultados históricos mede a última versão de Fast.

O objeto de observação fornecido às políticas comuns contém estado corrente,
sem sementes ou próximos dados. Isso reduz vazamento acidental de informação
futura, mas não é uma caixa de segurança: código de política arbitrário pode
acessar outras fontes do processo, e perfis de adversário e ambiente continuam
simplificados. Comparações só valem para os cenários, políticas e duração
estudados; validade da execução, fidelidade às regras e força das conclusões são
questões separadas.

## Prontidão e próxima fase

**Não recomendo retomar expansão ampla nem usar a migração de grupo para
conclusões de eficácia.** Correções e manutenção pontuais do recorte existente
podem continuar, mas ainda faltam condições para a próxima camada:

1. Definir no contrato de grupo quem é personagem de jogador e como resolver
   empates remanescentes; implementar e verificar ACT-02 sem atribuir papéis
   pelo time. Completar testes independentes de reação, duração, alvos e
   interações antes de usar o grupo como motor de estudo.
2. Delimitar e confirmar as regras necessárias ao cenário que se pretenda
   estudar: arredondamento de bônus ímpar em Fast, efeitos numéricos de membros,
   o instante de renovação de reações e o alcance das imunidades. Não preencher
   essas lacunas por suposição; cenários que não as acionem podem ser tratados
   separadamente.
3. Isolar futuras alterações de regras por versão, especialmente o cálculo de
   dano compartilhado entre motores, e manter replays antigos vinculados à
   fórmula de origem. Acrescentar manifesto completo para dependências de
   políticas externas antes de empregá-las em resultados congelados.
4. Projetar novas baterias de desenvolvimento, confirmação e reserva com a
   regra atual, depois dos gates de regras e de motor; pré-definir cenários,
   políticas, métricas e comparações. Os controles atuais não substituem essas
   baterias e os intervalos históricos de largura zero não devem ser lidos como
   certeza.

Os principais caminhos de execução e auditoria estão no [README](README.md).
Esta passagem registra as evidências para continuar o projeto sem refazer a
investigação; não atribui validade a regras ou cenários que ainda não passaram
pelos respectivos gates.
