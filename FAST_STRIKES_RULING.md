# Regra de mesa posterior: Fast Strikes

**Atualização posterior:** a mesa confirmou [rolagem literal de vários dados Marvel em todo dano](DAMAGE_POOL_RULING.md). Para Marreta + Lâmina sem DR, o acerto comum usa **`4d6+3 + 3d6+3 = 7d6+6`**; o fantástico usa **`8d6+6 + 7d6+6 = 15d6+12`**. Cada face 1 desses dados vale 6.

Em 27/10/2026, depois da bateria confirmatória e dos relatórios originais, o usuário esclareceu duas regras já aplicadas na mesa:

1. Victor recebe **duas edges** nos ataques de Fast Strikes: uma de Blazing-Fast Fists e outra de Signature Attack (Fast Strikes).
2. Fast Strikes executa **dois ataques com um único teste de acerto** e uma **conta/rolagem de dano para cada arma**. Marreta + Lâmina usam, antes de redução e divisão, os multiplicadores declarados `×8` e `×7`, com bônus `+6` em cada componente. **Os dois danos atingem o mesmo alvo e se somam.** Cada componente sofre sua própria Damage Reduction **antes** de ser reduzido à metade em acerto comum; em sucesso fantástico, cada componente causa dano integral. Os efeitos das duas armas podem ocorrer no mesmo uso; a Lâmina aplica Bleeding `5` por rodada sem acúmulo. **Mesmo sem duas armas diferentes**, Fast Strikes gera dois componentes contra o mesmo alvo.
3. O bônus `+1` ao multiplicador da **Lâmina e da Garra se soma ao Mighty 3** de Victor, conforme confirmação explícita posterior. Assim, com a ficha Rank 3, a Lâmina e a Garra têm multiplicador declarado `×7`; a Marreta mantém `×8`.

Esta é uma **regra de mesa**, com precedência sobre a leitura conservadora anterior do *Core Rulebook* p.99. O material antigo de [RULES_AUDIT.md](RULES_AUDIT.md), os resultados confirmatórios e as instruções numéricas de Fast Strikes em [REPORT.md](REPORT.md), [MANUAL_BLACKLIGHT.md](MANUAL_BLACKLIGHT.md) e [QUICK_REFERENCE.md](QUICK_REFERENCE.md) ficam **históricos**. A mudança global de [dano por vários d6](DAMAGE_POOL_RULING.md) também invalida para a mesa atual as taxas antigas de Marreta sem Fast Strikes, Focus e corredor.

O usuário esclareceu depois que `8d6` e `7d6` significam lançar literalmente oito e sete dados, e que **todos** os ataques seguem essa convenção. O exemplo anterior `6×8+6` e `6×7+6`, com total `51`, foi aceito sob uma premissa incompatível e **não é um oráculo do procedimento atual**. A mesa confirmou o arredondamento de sete dados para três no acerto comum; esse resultado se soma aos quatro da Marreta. A face 1 dos dados de dano é interpretada como 6, sem reutilizar o valor do dado Marvel do acerto.

Um protótipo que dividia totais **depois** de rolados foi descartado ao receber a explicação de `7d6+6`; ele não foi integrado ao motor. `tests/test_fast_ruling_edges.py` verifica que a variante existente usa as duas edges no único teste de acerto. `experimental/pool_damage.py` e seus testes cobrem a nova rolagem de dano isolada. A integração ao motor, o auditor independente e as novas simulações ainda são necessários.
