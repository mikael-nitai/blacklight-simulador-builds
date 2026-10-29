# Avaliação da arquitetura do Blacklight

Avaliação de 28/10/2026 sobre o código no commit `3ee42f9`, usando a
[certificação da Operação Fundação](CERTIFICACAO_FUNDACAO.md) como linha de
base. A certificação abrange o recorte ali declarado, não o projeto inteiro.
Esta avaliação examina a organização e os principais pontos de mudança,
inclusive o desenvolvimento posterior; não constitui nova certificação nem
inspeção exaustiva de cada linha.

Na árvore avaliada, `python -m unittest discover -s tests -q` passou com
357 testes no Windows. Não foram repetidas as baterias e auditorias da
certificação, pois não houve alteração de código ou regras nesta avaliação.

## Decisão

Não há refatoração de código suficientemente justificada nesta passagem. A
duplicação e os pontos de acoplamento abaixo têm custos reais, mas não há
evidência de que uma reorganização agora produza benefício maior que o risco
para os contratos, a verificação independente e a procedência dos estudos.
Não remover arquivos históricos só por parecerem antigos.

## Achados e decisões

| Ponto | Avaliação | Decisão |
|---|---|---|
| `blacklight/engine.py`, `combatants/modular_duel.py` e `combatants/split_fast.py` | O motor central concentra estado, ações, resolução e registro; as subclasses dependem de seus hooks internos. Isso dificulta mudanças transversais e aumenta a necessidade de testes de integração. A separação atual distingue a migração modular e a regra vigente da histórica. | Manter enquanto não houver alteração funcional concreta que justifique extrair uma responsabilidade. Uma extração deve preservar ordem de eventos, consumo de dados e replays de ambas as versões. |
| `combatants/actions.py` e `combatants/lifecycle.py` | Protocolos, planos imutáveis e ponte de estados acrescentam conceitos para um conjunto ainda restrito de ações e durações. Não são apenas invólucros: permitem validar planos e isolar variações; a certificação inclui ensaios limitados de mudanças de regras. | Manter; não generalizar outras mecânicas antecipadamente. Adicionar novas abstrações apenas com pelo menos um uso concreto e testes das fronteiras. |
| Auditorias e fórmulas repetidas | `blacklight/batch_audit.py` recalcula sementes e Wilson independentemente do executor; auditores de perfil, turno e espaço também confrontam aspectos distintos da trilha. Compartilhar a implementação sob teste reduziria a independência da verificação. | Preservar a duplicação intencional e seus testes de falsificação. Não tratar linhas semelhantes como código morto. |
| Confirmação e executor de lotes | `scripts/current_study_confirm.py` reconstrói a identidade da célula e as sementes de `combatants/runner.py`, além de importar helpers privados. Isso exige manutenção coordenada; `tests/test_current_study_confirm.py` compara a identidade das 12 células com a do executor, mas não transforma o acoplamento em interface pública estável. | Em estudo futuro, considerar contrato versionado explícito para identidade e sementes, mantendo o auditor independente. Primeiro comparar sementes e resultados históricos e testar alterações de versão. Não modificar o estudo confirmatório existente para uma limpeza incidental. |
| Pré-verificação de sementes | O comando de confirmação verifica as sementes antes do laço e `execute_cell` torna a verificar para cada célula. Há trabalho repetido, mas a verificação por chamada também protege execuções individuais e detecta alterações entre células. | Medir antes de otimizar. Qualquer redução precisa preservar as verificações de entradas e fontes em cada execução; não reutilizar um resultado em cache sem invalidá-lo diante de mudanças. |
| Fórmulas e experimentos anteriores | `blacklight/damage.py`, variantes de pool, scripts e resultados históricos representam contratos e evidências de épocas diferentes. Aparente obsolescência não prova ausência de uso ou possibilidade segura de remoção. | Preservar e manter identificações de versão e snapshots; não consolidar fórmulas com comportamentos diferentes. |
| Grupo e grade | `combatants/group.py` e `group_grid.py` acrescentam comportamento e auditores próprios sobre o motor existente. Há acoplamento por herança e hooks, mas grupo permanece experimental e sua geometria tem limites explícitos. | Evitar promover ou unificar com o duelo certificado por conveniência. Avaliar extrações ao implementar requisitos concretos, com testes de grupo e de não regressão do duelo. |
| Procedência conservadora | `combatants/runner.py` inclui fontes do núcleo nos manifestos e a identidade mecânica considera seus hashes. Isso pode sinalizar diferenças sem efeito mecânico, mas mantém rastreabilidade e não afirma equivalência geral. | Manter o conservadorismo. Reduzir o manifesto só com demonstração de dependências e migração versionada dos contratos. |

## Proteção do trabalho em andamento

No início desta avaliação havia 12 arquivos `results/current_duel_confirm_v1_*.json`
não rastreados. Eles foram deixados intactos. Sua presença não demonstra, por
si, que tenham sido auditados, congelados ou interpretados. Alterar fontes do
estudo antes de resolver sua procedência pode dificultar a comparação e o
congelamento; os procedimentos continuam em
[RESULT_VERSIONING.md](RESULT_VERSIONING.md).

## Critério para mudanças futuras

Para qualquer simplificação proposta: identificar o custo ou defeito observado,
medir quando a justificativa for desempenho, preservar as versões e registros,
comparar replays e sementes aplicáveis, testar os contratos afetados e registrar
a alteração em commit próprio. Repetir auditorias mais amplas apenas quando a
mudança atingir suas fronteiras ou exigir nova evidência; uma suíte aprovada não
amplia automaticamente o escopo certificado.
