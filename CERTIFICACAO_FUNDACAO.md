# Operação Fundação: escopo e matriz de certificação

## Linha de base e escopo congelado

Esta continuação começou no commit `342e712`, com a árvore Git limpa e
sincronizada com `origin/master`. O diagnóstico anterior está em
[OPERACAO_FUNDACAO.md](OPERACAO_FUNDACAO.md); o objetivo aqui é resolver os
bloqueadores técnicos do escopo abaixo, com uma revisão adversarial final.

O escopo candidato à certificação é o que já era apresentado como funcional:

1. Dados d616, edge/trouble e pools literais de dano das versões de mesa já
   implementadas, incluindo a fronteira `0d6` e a rejeição de bônus ímpar sem
   decisão do mestre.
2. Importação de fichas versionadas, gate de cobertura e duelos físicos de duas
   fichas em campo aberto: ações, movimento, recursos, armas e poderes aceitos
   pelo adaptador, reações e estados explicitamente listados nos contratos.
   Inclui o contrato histórico de Fast e o atual de dois testes por braço.
3. O corredor atual de duas fichas, somente em uma dimensão e dentro das
   capacidades documentadas em [CURRENT_CORRIDOR.md](CURRENT_CORRIDOR.md).
4. Os auditores e os módulos reutilizáveis de cura, ativação de estados e
   duração **nas verificações e fronteiras efetivamente implementadas**.
5. Execução, sementes, estatística e preservação/reprodução de resultados para
   os estudos existentes e as políticas fornecidas com o projeto, respeitando
   seus respectivos snapshots e limites de inferência.

Não entram como funcionalidades certificadas: a migração atual de grupo,
protótipos de Focus/grupo, políticas externas arbitrárias, mapa geral, fichas
oficiais incompletas, penalidade numérica de membros, Karma, poderes não aceitos
pelo adaptador ou qualquer conclusão universal de estratégia. Esses itens não
serão apagados. A confirmação de dois alvos em Fast continua válida; a
capacidade de testá-los em grupo segue experimental. As regras sem decisão do
mestre permanecem bloqueadas ou qualificadas nos pontos em que afetam o escopo.

## Matriz de critérios

| Critério | Situação nesta linha de base | Evidência e trabalho necessário |
|---|---|---|
| 1. Sem defeitos críticos/altos conhecidos no escopo | **Em andamento.** O auditor aceitava bônus e defesa adulterados, desde que a aritmética interna fosse coerente. | Corrigir e falsificar as trilhas; rever dependências reais antes da revisão final. |
| 2. Contratos, testes e verificações independentes proporcionais | **Em andamento.** Há exemplos calculados e auditores, mas alguns ainda confiam em campos fornecidos pelo próprio motor. | Confrontar a trilha com as fichas e os estados; manter testes de limites e integrações. |
| 3. Mudanças hipotéticas em três famílias e compatibilidade histórica | **Em andamento.** Cura e dano Fast tiveram ensaios iniciais; isolamento e terceira família precisam de evidência adequada. | Exercícios reversíveis com alterações locais, controles não afetados e identificação dos resultados históricos pertinentes. |
| 4. Execução, auditoria, versionamento e reprodução documentados e verificados | **Em andamento.** Os comandos e índices existem; permanecem limites de dependências e versão compartilhada. | Verificar fluxos reais em ambientes disponíveis, procedência e tratamento de divergência sem sobrescrita. |
| 5. Experimentais, ambiguidades e limitações controlados | **Em andamento.** Grupo atual está identificado, mas os gates e a rotulagem precisam ser conferidos. | Impedir que saídas experimentais sejam confundidas com conclusões validadas; explicitar bloqueios e alternativas. |

## Triagem inicial

| Achado ou pendência | Classificação | Tratamento nesta operação |
|---|---|---|
| Bônus, defesa, dano, reações e rolagens declarados apenas pela própria trilha | Alto para a confiança no auditor | Reconciliar fatos verificáveis com fichas e eventos e testar falsificações. |
| Motor antigo executado sob etiqueta da regra atual | Alto, reproduzido | Verificar o contrato declarado da classe antes do combate e os eventos Fast durante a auditoria. |
| Código de dano compartilhado entre versões e motores | Alto para alteração futura | Isolar as variantes existentes e provar que uma mudança hipotética não altera silenciosamente a outra; preservar replays. |
| Dependências externas/transitivas e fontes já carregadas | Alto para alegações de reprodução não qualificadas | Definir e verificar a fronteira de procedência; bloquear ou rotular o que não puder ser demonstrado. |
| Distância, ações fora do turno e resumo do combate adulterados | Alto, reproduzido na revisão de integração | Reconstruir a posição, conferir turnos e reconciliar Health, Focus, vencedor e métricas com a trilha. |
| Resultados antigos e intervalos de largura zero | Corrigido para novas análises; histórico preservado | Manter distinção por versão e comprovar que alterações não reclassificam o passado silenciosamente. |
| Desempate de iniciativa em grupo, múltiplas reações e posições | Experimental, fora da certificação | Não usar o grupo migrado como base de conclusões validadas; manter no backlog. |
| Bônus ímpar em Fast, penalidades de membros, renovação exata de reações, escopo de imunidade | Depende de regra da mesa ou recorte | Bloquear casos sem decisão e explicitar interpretações já usadas, sem inventar regra. |
| Melhores adversários, novas métricas e baterias de eficácia para a regra atual | Expansão futura | Não iniciar nesta operação; controles de integração não são prova de estratégia ótima. |

Os demais itens históricos de preservação, caminhos entre sistemas, nomes de
saída e fórmula declarada de sementes foram corrigidos na primeira operação e
serão rechecados quando afetados. A decisão final e as verificações executadas
substituirão a situação provisória desta matriz; contagem de testes, por si só,
não representa certificação.

## Primeira consolidação: confrontar a trilha com as fichas

Uma falsificação reproduzida acrescentou +7 ao modificador de um ataque e ao
total registrado sem mudar sua classificação: o auditor anterior aceitou a
trilha, embora a ficha não autorizasse o bônus. Também foi possível falsificar
defesa, Rank, bônus de arma, redução e dano aplicado mantendo coerentes os
demais campos. `blacklight/profile_audit.py` passou a confrontar essas entradas
com os perfis e com eventos de postura e Escudo; `blacklight/dice_audit.py`
confere a cadeia de rerrolagens sem chamar o gerador de dados do motor. Esses
verificadores não certificam todas as regras ou a origem aleatória das faces.

Os novos testes incluem um ataque com dano calculado à mão e adulterações
coordenadas, além de exemplos independentes de edge, trouble, dado Marvel e
sucesso fantástico supremo. Os controles atuais reproduziram quatro logs e os
agregados de duas baterias de 1.000 sementes; a verificação dos 37 registros
congelados continuou sem divergências. A suíte de 277 testes passou no Windows e
no Ubuntu via WSL após essa consolidação; verificações atingidas por mudanças
posteriores serão repetidas. O escopo do auditor continua explícito: conferir
consistência não prova que uma política ou uma regra represente toda a mesa.

## Separação de execução e componentes experimentais

Uma troca forçada de motor reproduziu uma falha de versão: o runner declarava
`split_fast_v3`, mas executava Fast com a regra histórica de um único teste.
Os contratos agora são identificados nas classes, o runner recusa uma classe de
versão diferente antes do combate e `blacklight/ruleset_audit.py` confronta o
formato dos eventos com a versão declarada. Um teste adicional força uma classe
a mentir sobre seu nome de versão: quando Fast é usado, a verificação da trilha
recusa o resultado mesmo assim. Versões desconhecidas são recusadas. Duelo e
corredor preservados continuaram reproduzindo os controles anteriores.

Políticas internas e externas recebem classificações distintas. O congelamento
de novos resultados genéricos exige política interna identificada e a lista das
fontes Python do núcleo presentes no commit, além das fontes do corredor quando
aplicável. Um teste em repositório Git temporário confirma que uma dependência
omitida bloqueia o congelamento e que acrescentá-la permite a verificação; outro
mantém válido um registro antigo sem os metadados novos. Código externo continua
executável para exploração, mas recebe marca de procedência não verificada e
não pode ser congelado sob a alegação de resultado genérico certificado.

O runner de duas fichas recusa uma classe com escopo experimental. Resultados
da migração de grupo carregam essa identificação, e novos replays/experimentos
históricos de grupo, Focus e corredor indicam escopo exploratório; seus registros
antigos não foram reescritos. Esses mecanismos não são sandbox contra código
arbitrário e não transformam uma auditoria parcial em prova da campanha.

## Ensaio de três mudanças hipotéticas

Em `tests/test_rule_change_resilience.py`, sem alterar as regras vigentes:

1. **Cura:** um registro de ações de teste elevou a cura de 10 para 15 ao
   gastar 5 Focus; dez duelos que não usam cura mantiveram a trilha inteira.
2. **Dano de Fast:** uma subclasse experimental alterou apenas o bônus de dano
   dos braços. O exemplo passou de 42 para 44; um ataque comum e os replays
   históricos e atuais de controle ficaram idênticos. O auditor da regra atual
   rejeitou a variante quando apresentada como se fosse a regra vigente.
3. **Reações:** outra subclasse de teste reduziu o orçamento para uma reação.
   Num caso construído, Escudo consumiu a reação e a segunda reação, Riposte,
   deixou de ocorrer; a regra atual continuou permitindo as duas. Em dez sementes
   com políticas que não reagem, os ataques e desfechos permaneceram idênticos.

As subclasses são exemplos restritos, não novas regras liberadas pelo runner.
Uma revisão real precisará de identidade própria, registro explícito e auditoria
para a nova regra. Os novos resultados genéricos registram identidade derivada da
versão, das definições de ações e das fontes mecânicas. A comparação assinala
diferenças; resultados antigos sem essa identidade recebem estado não verificado,
sem serem alterados ou considerados equivalentes por suposição. A cópia de teste
do repositório no commit `bd67b50` conseguiu executar um duelo novo, congelá-lo e
verificar 38 resultados; uma nova repetição será necessária após esta alteração.

Os auditores de linha de comando agora capturam antes e depois todos os arquivos
Python das pastas de código, scripts e testes como um conjunto conservador de
fontes. A verificação detecta alterações persistentes nesse conjunto e evita
listas manuais que omitiam dependências novas. Não detecta alteração revertida
entre as leituras, alteração do processo em memória nem dependências externas.

## Integridade de combate e lotes

A revisão reproduziu três falhas que os testes anteriores não pegavam: o motor
podia registrar distância 99 quando a distância real era 1; um resumo podia
declarar um vencedor fabricado; e uma ação podia ser deslocada para depois do
fim do turno sem que os auditores a rejeitassem. Essas falhas comprometiam a
confiança nos resultados e foram classificadas como altas.

`blacklight/spatial_audit.py` reconstrói a distância em campo aberto a partir de
movimentos e recuos. `blacklight/turn_audit.py` confere iniciativa, ordem e
limites dos turnos completos e distingue ações de reações. O auditor de resumo
`blacklight/result_audit.py` confronta vencedor, recursos e métricas com os
eventos. O corredor mantém seu auditor espacial próprio. Os testes injetam as
três adulterações e conferem exemplos calculados à mão; essas verificações
continuam limitadas aos eventos registrados e não provam a fidelidade a todas as
regras do jogo.

Lotes genéricos auditam cada início por padrão. Uma amostra explícita recebe
`sampled_starts`; o congelamento exige cobertura completa, índices e sementes
consistentes, contagens e taxas válidas. As trilhas completas dos lotes não são
salvas; apenas os registros de auditoria, sementes e agregados ficam no JSON.
Os resultados históricos continuam ligados aos commits originais, sem receber
uma certificação retroativa por meio de campos novos.
