# Snapshot da primeira família modular

Estes três JSONs foram copiados antes da migração de estados e preservam `execution_adapter=modular_physical_duel_v1`. O código correspondente está no commit `b1e4d19`; os manifests registram seus hashes. Para reproduzir exatamente essa versão, usar o commit em um checkout separado.

Os arquivos de mesmo nome na pasta `results/` agora usam o adaptador v2 e fontes atuais. A verificação padrão de fontes examina somente as saídas atuais na raiz de `results/`; arquivos históricos deste diretório não precisam coincidir com o código novo. Não usar o snapshot como prova de cobertura atual.
