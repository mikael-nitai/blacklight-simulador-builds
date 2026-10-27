# Duelo exploratório contra Mental Punch

Registrado em 27/10/2026 antes de obter resultados desse duelo. O [gate de Focus](FOCUS_SPEC.md) e os testes da primitiva são pré-requisitos. Esta expansão permanece em `experimental/` e não altera as 400.000 lutas confirmatórias de `blacklight/`.

## Gerador e adversários

Contato corpo a corpo fixo, sem mapa, movimento, Karma, aliados ou outros poderes. Victor usa a ficha Rank 3 atual, ataca com Marreta, tem Healing Factor e Riposte; pode proteger-se com o Escudo por reação após acerto ou ao fim de seu turno, desativando-o gratuitamente antes de atacar. Reações têm o orçamento conservador de duas por rodada, uma por gatilho. O inimigo sintético usa **Mental Punch** a cada turno e não conhece dados futuros. Em M3: Rank 3, Melee 6, Resilience 5, Health 150, Vigilance 2, Focus 60, defesa Melee 16. Em M4: mesmas habilidades/recursos, Rank 4; o aumento de Rank intensifica o dano de Focus sem mudar defesa ou Health. Esse perfil não é personagem oficial nem representativo da frequência de telepatas na campanha.

O acerto de Mental Punch reduz Focus; fantástico dobra e aplica Stunned por uma rodada. Stunned impede ações e reações; Demoralized (Focus ≤0) impõe trouble nos testes seguintes, mas não termina o combate; Shattered (Focus ≤−90) termina como derrota de Victor. Sturdy 1 reduz apenas Health, não Focus. O Escudo contra Focus tem **duas variantes separadas**: F0, sem redução de Focus, e F2, −2 no multiplicador de Mental Punch por ser ataque Melee. Ambas preservam o custo e o timing de reação do Escudo. Esta distinção é necessária porque a decisão da mesa não especificou explicitamente o tipo de dano nesse caso.

Comparar três políticas fixas: FH, Marreta sem Escudo; FR, Marreta + Escudo reativo ao acerto; FE, Marreta + Escudo ao fim do turno, usando também a reação após acerto se ainda estava desativado. FH é controle comum nas duas variantes; repetir sua amostra é permitido, mas não tratá-la como confirmação independente. Todas usam Riposte contra erro em ataque próximo quando há reação e Victor pode agir.

## Medidas e execução

Horizonte de 30 rodadas. Iniciativa e rodada bônus seguem o Core. Desenvolvimento: 1000 combates por célula. Descrição posterior: 5000 sementes novas por célula, todas as 12 células fixadas antes de olhar desenvolvimento. Semente de cada combate: primeiro 8 bytes SHA-256 de `blacklight-focus-v1|fase|cenário|variante|política|índice`. Reportar vitória, derrota e inconclusão com denominador de todos os combates; IC Wilson 95% para cada proporção, Focus final médio, fração que chegou a Demoralized e Shattered, e número médio de rodadas. Não inferir pesos de encontro. Auditor independente deve recalcular dado, dano Health/Focus, proteção, orçamento de reações e estado final de cada centésima trilha descritiva; qualquer divergência bloqueia o relatório.

## Limites

O inimigo usa uma única tática mental e não recua, agarra ou combina ataques físicos. O estudo não resolve prioridade entre reações simultâneas, recuperação por Karma, efeitos de concentração, inimigos que ataquem de longe, ou interações de Escudo com outros tipos de Focus. Os resultados serão **exploratórios**, em especial porque a variante F2 depende de interpretação de mesa. Nenhuma taxa daqui será misturada à confirmação de duelos físicos.
