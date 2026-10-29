# Quando Victor consegue atacar? Observação exploratória

Uma leitura adicional dos dados já preservados da [reserva atual](CURRENT_DUEL_HOLDOUT_REPORT.md) ajuda a interpretar o confronto contra um atirador que recua em campo aberto. **É uma análise exploratória escolhida depois de observar os dados**, não uma nova bateria ou um teste confirmatório pré-registrado.

Cada linha contém 10.000 combates simulados. A coluna conta quantos terminaram sem que Victor registrasse qualquer tentativa de ataque, inclusive Riposte e os ataques de Fast contados pelo motor.

| Política de Victor | Combates sem ataque de Victor | Proporção observada |
|---|---:|---:|
| Desarmado, Escudo reativo | 7.996 | 79,96% |
| Marreta comum, Escudo reativo | 7.969 | 79,69% |
| Fast Marreta + Lâmina, efeito Marreta | 7.987 | 79,87% |
| Fast Marreta + Lâmina, efeito Lâmina | 7.912 | 79,12% |

Por exemplo, para Fast com efeito da Marreta, o intervalo Wilson individual de 95% é aproximadamente **79,07% a 80,64%**, condicionado ao modelo desse cenário. Esse intervalo é descritivo e não foi ajustado para escolher ou comparar as quatro políticas. As diferenças entre linhas não foram testadas aqui e não autorizam declarar uma arma superior.

**O que isso significa na prática:** no cenário modelado, a oportunidade de fazer ataques próximos é uma limitação relevante; comparar dano de armas sozinho não descreve o confronto. Vale observar distância, obstáculos, posição e alternativas de aproximação na mesa. O resultado não prova que a mesma proporção se repetirá em uma partida real nem que a ausência de ataques tenha uma única causa em cada combate.

**Limites:** trata-se de um atirador sintético com política específica de recuo, campo aberto unidimensional, distância inicial de oito espaços e limite de 30 rodadas. O ataque à distância não foi classificado como munição, e a bateria não incluía Ram, dano de Focus, Karma ou terreno geral. Os combates sem vencedor no limite são inconclusivos, não derrotas. As políticas não usam cura voluntária. A [exploração posterior de Ram](RAM_CROSSBONES_EXPLORATION_REPORT.md) tem outro adversário e não deve ser mesclada com esta amostra.

## Como conferir

Nos quatro arquivos `results/current_duel_holdout_v1_gunner_open_*.json`, localizar `attacks` em `extended_fields` e contar as linhas de `extended_samples_all_starts` cujo valor nessa posição é zero. Todos os 10.000 inícios de cada célula são incluídos; não é filtro apenas de vitórias. Os arquivos e suas fontes permanecem congelados no commit de execução `4c9a5df` e no inventário de resultados.

| Arquivo de resultado | SHA-256 |
|---|---|
| `current_duel_holdout_v1_gunner_open_bare.json` | `c8963a43f5b83a5ed988090001c1e6780f648331ffac10a98fb8e424abe97f96` |
| `current_duel_holdout_v1_gunner_open_hammer.json` | `c5125f7c9545e06d1045ebec7d837194b7b36611aa437752ba4245f4f099cbcb` |
| `current_duel_holdout_v1_gunner_open_hammer_fast_hammer.json` | `ebf77fe447964104008673261eb056626a8836519afb718e76c12c7e5d9d600b` |
| `current_duel_holdout_v1_gunner_open_hammer_fast_blade.json` | `f54df94db1a5ec35f691e6cf1964df981ff1ae80e17244faa6579b459fdedf34` |
