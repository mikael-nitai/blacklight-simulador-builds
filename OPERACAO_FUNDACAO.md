# Operação Fundação: diagnóstico e passagem

Registro de trabalho iniciado em 28/10/2026. Este diagnóstico é uma linha de
base, não uma certificação de todo o RPG. As conclusões se referem aos arquivos
e verificações identificados abaixo; o estado das correções será atualizado aqui.

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
| Grupo | `experimental/group.py` preserva o contrato anterior; `combatants/group.py` é a migração interrompida. Cem sementes sintéticas da migração executaram sem erros do auditor existente. | Esse auditor tem pontos cegos descritos abaixo; não há testes específicos da nova classe e a migração não está pronta para medições de eficácia. |
| Focus e estudos antigos | Existem protótipos e resultados históricos documentados. | Resultados `pool_v2` precedem o último balanceamento de Fast Strikes e não medem a regra atual. |
| Proveniência | Em `python -B -m scripts.verify_sources`, 37 resultados congelados passaram na conferência dos hashes declarados e dos commits. | Isso verifica os arquivos declarados, não a fidelidade das regras nem a validade das conclusões. Apenas 6 dos 37 registros têm `table_ruleset` explícito; os demais dependem dos registros históricos. A varredura principal cobre JSONs na raiz de `results/`, não todos os arquivos de subpastas. |
| Testes | `python -B -m unittest discover -s tests -q`: 228 testes passaram na linha de base. | Os casos não incluem a nova classe de grupo e os exemplos adversariais abaixo mostram que o auditor não detecta toda inconsistência. |

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

Os achados 1 e 3 são falhas reproduzidas. O item 2 é uma limitação demonstrada
do verificador, não uma prova de que os combates já executados tiveram 99
reações. Os itens 4 e 5 são riscos de interpretação/manutenção, não autorização
para reescrever os motores ou modificar as regras da mesa.

## Sequência de fortalecimento

1. Impedir substituição de resultados e pedir nomes novos nas saídas históricas.
2. Rejeitar movimentos inválidos antes de gastar ação; reforçar o auditor com
   limites independentes conhecidos e testes que falsificam trilhas.
3. Corrigir referências de regras e sinalizar claramente o grupo incompleto.
4. Conferir a classificação e a procedência dos resultados, os scripts
   estatísticos e um ensaio isolado de mudança hipotética de regra.
5. Executar testes completos e verificações adversariais adicionais. Atualizar
   esta passagem com alterações, evidências, restrições e decisão de prontidão.

**Prontidão inicial:** não recomendar expansão de conclusões nem apresentar o
grupo novo como pronto enquanto os achados e os gates acima estiverem abertos.
