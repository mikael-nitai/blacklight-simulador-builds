# Resultados ligados à versão executada

27/10/2026. Evoluir o motor não deve apagar os experimentos anteriores nem apresentar suas taxas como medições da versão nova. O índice `results/source_snapshots.json` liga os bytes de cada resultado a um **commit completo do Git**. Todos os hashes declarados no resultado precisam coincidir com arquivos desse mesmo commit.

O verificador exige um objeto Git do tipo `commit`; um nome de branch, tag ou hash de árvore não serve como identidade no índice. Quando os arquivos atuais mudam, a verificação continua consultando o commit registrado. `--live-only` permite exigir coincidência com os arquivos atuais, caso em que diferenças de uma execução histórica são falhas esperadas.

As consultas desativam `refs/replace` do Git, que poderiam trocar silenciosamente os bytes lidos sob um hash antigo. O modo padrão exige registro congelado para todos os resultados atuais. `--allow-unfrozen` é um modo explícito de preparação que aceita conferir resultados novos contra os arquivos atuais, sem alegar que estejam congelados. A publicação do índice usa um arquivo temporário no mesmo diretório e substituição atômica; falhas antes da substituição preservam o índice anterior.

Um nome congelado é imutável. Se os bytes mudarem, a verificação e um novo congelamento falham; uma execução nova deve receber **outro nome de arquivo**. Um arquivo registrado que desapareça também causa falha. O congelamento valida o inventário inteiro antes de gravar e preserva os vínculos anteriores.

Os 36 JSONs da fórmula antiga ainda presentes na raiz de `results/` foram comparados byte a byte com suas cópias em `results/legacy_scalar_v1/`. Estão enumerados com hash e motivo em `results/historical_inventory.json`. Esses bytes continuam sendo conferidos, mesmo quando seus experimentos não participam da análise atual. Um JSON novo sem manifesto, com modelo desconhecido ou com nome contendo `pre_`/`invalid_` não é excluído automaticamente.

Comandos, a partir da pasta do projeto:

```powershell
python -m scripts.verify_sources --details
python -m scripts.verify_sources --live-only
python -m scripts.freeze_results --ref HEAD
```

Antes do último comando, as fontes da execução precisam estar em um commit. O resultado deve conter os hashes dessas fontes. Fontes externas ao repositório precisam ser preservadas no repositório antes desse tipo de congelamento. A verificação dos hashes comprova proveniência; a correção das regras e das conclusões continua dependendo dos testes e das auditorias.

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
