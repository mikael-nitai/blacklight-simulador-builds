# Grupo experimental em grade quadrada

O executor experimental aceita uma grade retangular com uma posição por
participante, permitindo confrontos com mais de dois personagens e alvos em
posições diferentes. A ficha continua versionada e o mesmo gate de mecânicas
impede o uso silencioso de poderes sem suporte. Este cenário não certifica
fichas oficiais completas nem permite concluir qual estratégia é melhor.

No Core, p.26 impressa (p.27 do PDF), cada passo para uma das oito casas
vizinhas custa um espaço, inclusive na diagonal. Por isso a distância usada em
terreno plano é `max(|x1-x2|, |y1-y2|)`. O alcance próximo implementado é de
uma casa, conforme o alcance habitual de personagens de tamanho médio descrito
no Core p.30. O modelo **pressupõe esse alcance para todos os participantes**;
a ficha atual não declara tamanho ou alcance de outras criaturas.

O mapa é um cenário limitado, com as seguintes escolhas explicitamente
operacionais, não regras universais do Core:

- Cada personagem ocupa uma única casa; casas ocupadas não podem ser atravessadas.
  Todos os participantes permanecem representados na grade, inclusive se
  incapacitados ou mortos. Não se modela compartilhamento de casas, tamanhos
  diferentes ou as interações especiais da FAQ de 2025 p.3.
- Ataques à distância só são aceitos até 200 casas, nas mesmas linhas horizontal,
  vertical ou diagonal de 45 graus, sem outro participante entre origem e alvo.
  Outras linhas são recusadas por falta de um algoritmo de visão validado; isso
  **não significa que o Core as proíba**. Não são modeladas cobertura, quinas,
  elevação, objetos ou exceções do Narrador. O Core p.27 trata de linha de visão;
  p.30 exige visão e limita o ataque a duas vezes o alcance, com trouble além do
  alcance normal.
- A política pode percorrer um caminho de casas vazias, de até Run Speed, antes
  da ação padrão. Esta etapa não oferece converter a ação padrão em movimento
  nem dividir o mesmo movimento antes e depois da ação, opções do Core ainda
  pendentes no cenário. Também não implementa terreno difícil, knockback, Karma
  ou ataques de Focus.

Cada braço de Fast declara e valida seu próprio alvo antes de gastar a ação.
O alvo precisa continuar em alcance ao aplicar um teste já preparado; Riposte
usa a distância até o atacante que gerou o gatilho. O observador expõe um
instantâneo imutável das posições atuais, e a política só escolhe alvos
permitidos pelo alcance e visão do cenário. As políticas são controles simples
de aproximação e ataque; não representam oponentes taticamente completos.

O auditor espacial independente reconstitui posições e passos, verifica limites
de movimento, alcance, visão e trouble de distância, e compara o resultado com
o log. O executor combina-o com os auditores existentes de ficha, iniciativa,
ações/condições, fila e dano. A verificação é parcial: não certifica toda a
legalidade das regras ou efeitos e não prova a origem aleatória dos dados.
O schema próprio `blacklight-experimental-character-group-grid-v1` é bloqueado
no congelamento certificado de duelos. Os resultados de contato fixo anteriores
conservam seus schemas e fontes.

## Executar

No PowerShell, a partir da pasta do projeto:

```powershell
python -m scripts.character_group examples/experimental_group_grid_config.json --output experimental_outputs/meu-grupo-em-grade-001.json
```

Escolha um nome novo para cada saída. O exemplo usa Victor e dois adversários
**sintéticos**. Para trocar fichas ou posições, copie a configuração e ajuste
os caminhos, as coordenadas, equipes, papéis e políticas. O resultado registra
os parâmetros, posições, fontes, semente e trilha completa; continua sendo um
experimento e não é publicado na pasta de resultados congelados.

## Controles desta etapa

- Casos calculados conferem diagonal, caminhos inválidos, dois alvos de Fast,
  proteção contra alvo que se afasta após o teste preparado, alcance de Riposte,
  visão bloqueada e trouble de longa distância. Trilhas com distância ou caminho
  adulterado foram rejeitadas pelo auditor de posição. Uma revisão independente
  encontrou e levou à correção da aceitação de booleanos como coordenadas e como
  `trouble` zero em registros adulterados.
- Foram executados 200 encontros com Victor e dois perfis sintéticos, com todas
  as auditorias disponíveis. Uma revisão independente executou 150 encontros
  adicionais de quatro personagens: sementes 0–149, quatro casas sorteadas sem
  reposição em grade 12×12, dois contra dois, espelhos sintéticos de Victor,
  cura, Escudo e armas variadas, até 12 rodadas. São controles de integração,
  não uma avaliação comparativa de estratégias.
- A suíte completa passou em 342 testes antes da última correção de tipagem;
  os 30 testes direcionados de grupo e grade passaram após essa correção.
