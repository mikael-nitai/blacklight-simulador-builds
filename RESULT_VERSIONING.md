# Resultados ligados à versão executada

27/10/2026. Evoluir o motor não deve apagar os experimentos anteriores nem apresentar suas taxas como medições da versão nova. O índice `results/source_snapshots.json` liga os bytes de cada resultado a um **commit completo do Git**. Todos os hashes declarados no resultado precisam coincidir com arquivos desse mesmo commit.

O verificador exige um objeto Git do tipo `commit`; um nome de branch, tag ou hash de árvore não serve como identidade no índice. Quando os arquivos atuais mudam, a verificação continua consultando o commit registrado. `--live-only` permite exigir coincidência com os arquivos atuais, caso em que diferenças de uma execução histórica são falhas esperadas.

As consultas desativam `refs/replace` do Git, que poderiam trocar silenciosamente os bytes lidos sob um hash antigo. O modo padrão exige registro congelado para todos os resultados atuais. `--allow-unfrozen` é um modo explícito de preparação que aceita conferir resultados novos contra os arquivos atuais, sem alegar que estejam congelados. A publicação do índice usa um arquivo temporário no mesmo diretório e substituição atômica; falhas antes da substituição preservam o índice anterior.

Um nome congelado é imutável. Se os bytes mudarem, a verificação e um novo congelamento falham; uma execução nova deve receber **outro nome de arquivo**. Um arquivo registrado que desapareça também causa falha. O congelamento valida o inventário inteiro antes de gravar e preserva os vínculos anteriores.

Lotes podem declarar a extensão opcional `blacklight-batch-combat-samples-v1`:
ela registra métricas por início e quantis de posto mais próximo, exigindo
auditoria de todos os inícios. O gate recalcula os resumos, confere sementes,
desfechos, recursos e limites de contadores antes de congelar. Essa verificação
não prova a origem de amostras falsificadas de modo inteiramente consistente;
as sementes permitem reproduzir combates. Lotes anteriores sem extensão não são
reescritos e continuam sujeitos aos próprios contratos.

Os 36 JSONs da fórmula antiga ainda presentes na raiz de `results/` foram comparados byte a byte com suas cópias em `results/legacy_scalar_v1/`. Estão enumerados com hash e motivo em `results/historical_inventory.json`. Esses bytes continuam sendo conferidos, mesmo quando seus experimentos não participam da análise atual. Um JSON novo sem manifesto, com modelo desconhecido ou com nome contendo `pre_`/`invalid_` não é excluído automaticamente.

Comandos, a partir da pasta do projeto:

```powershell
python -m scripts.verify_sources --details
python -m scripts.verify_sources --live-only
python -m scripts.freeze_results --ref HEAD
```

Antes do último comando, as fontes da execução precisam estar em um commit. O resultado deve conter os hashes dessas fontes. Fontes externas ao repositório precisam ser preservadas no repositório antes desse tipo de congelamento. A verificação dos hashes comprova proveniência; a correção das regras e das conclusões continua dependendo dos testes e das auditorias.

Para **novos** resultados genéricos de ficha, o congelamento também exige
`policy_provenance: project_builtin`, tipos de política registrados e hashes de
todos os arquivos Python do núcleo presentes no commit; para corredores exige
as fontes e especificações adicionais do corredor. Uma política personalizada
pode executar e produzir dados, mas recebe `external_unverified` e não pode
ser congelada como resultado genérico certificado: suas dependências transitivas
não são conhecidas automaticamente. Essa é uma barreira de procedência, não uma
caixa de segurança para código arbitrário. Os resultados já congelados antes
desse campo conservam seus bytes e continuam verificáveis pelo índice anterior.

Novos lotes genéricos só passam pelo congelamento quando indicam auditoria de
todos os combates e apresentam uma entrada sem falhas para cada índice, com a
semente derivada da célula, contagens, taxas e intervalos Wilson consistentes.
Um duelo genérico novo também precisa registrar uma auditoria sem falhas. O runner faz isso
por padrão; amostragem explícita fica identificada e não passa nesse gate. As
entradas são registros de execução, não uma prova criptográfica contra um autor
que altere o programa ou falsifique coordenadamente os dados. Os lotes guardam
agregados e sementes, não cada trilha completa. A conferência de combate por
combate posteriormente exige reprodução nas condições registradas.

Cada nova saída genérica também registra `mechanics_contract_sha256`, calculado
a partir da versão declarada, dos parâmetros dos módulos de ação e dos hashes
Python registrados de `blacklight/`, `combatants/` e, quando usado, do corredor.
O congelamento recalcula essa identidade e exige coerência. Ela é conservadora:
uma mudança em uma fonte incluída pode disparar revisão mesmo quando não afeta
um combate. Igualdade identifica apenas os dados de contrato registrados, não
comprova regras corretas nem ambientes idênticos.

Use `python -m scripts.result_compatibility --compare PRIMEIRO.json SEGUNDO.json`
com dois nomes presentes no inventário. O comando verifica os registros primeiro
e distingue contratos declarados diferentes, identidades iguais e evidência
insuficiente. Arquivos antigos sem identidade permanecem `not_recorded`; a
ferramenta não inventa um hash retroativo e aponta fontes compartilhadas que
mudaram. Divergência de fonte requer revisão e não prova que um cenário foi
afetado.

Os novos manifestos usam caminhos relativos com `/`. Para preservar os resultados
antigos sem editar seus bytes, o verificador também aceita separadores Windows
relativos e reconhece duas correspondências explícitas para fichas que foram
gravadas com o caminho absoluto da pasta original. Essas correspondências estão
em `scripts/verify_sources.py` e continuam sujeitas aos hashes do commit; caminhos
absolutos externos desconhecidos não são remapeados por suposição. A conferência
de 37 resultados passou tanto no Windows quanto no Ubuntu e numa cópia do
repositório localizada em outra pasta.

`python -m scripts.result_compatibility --details` classifica os resultados
congelados e os 36 arquivos escalares do inventário sem alterá-los. As revisões
antigas sem campo de regra são identificadas somente pelos dois commits
explicitamente reconhecidos; as demais ficam desconhecidas. Para as fontes
listadas, uma diferença em relação ao projeto atual indica necessidade de
revisão ou reprodução com o snapshot: ela não prova, por si só, que uma
mudança afetou o resultado. O comando também sinaliza intervalos históricos de
largura zero. As cópias `legacy_scalar_v1` declaradas no inventário agora são
conferidas individualmente, além dos arquivos da raiz.

Nesta etapa foram vinculados 25 resultados da fórmula literal ao commit `f9c540a`. A revisão independente encontrou e levou à correção de substituição de registro congelado, omissão de resultados ausentes ou malformados, aceitação de árvore Git como commit, aceitação implícita de dados não congelados, interferência de `refs/replace` e escrita parcial do índice. Os 19 testes usam repositórios Git temporários reais e falhas de publicação injetadas, incluindo evolução de fonte, adulteração dos resultados e isolamento de fontes externas.
