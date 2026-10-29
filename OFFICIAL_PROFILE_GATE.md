# Inventário inicial de adversários oficiais do Core Rulebook

Fonte visual: `C:\Users\avada\Downloads\Marvel Multiverse Role-Playing Game - Rulebook (Bookmarks Searchable).pdf`, capítulo 8. Foram conferidas as páginas completas abaixo, inclusive as caixas de Rank, defesas, dano, poderes e traits; a extração automática de texto omite parte desses números. **Nenhum destes perfis foi inserido nos experimentos até validar sua cobertura mecânica.**

| Perfil oficial | Página impressa / PDF | Dados conferidos na página | Principal lacuna do motor atual |
|---|---:|---|---|
| Crossbones | 155 / 156 | Rank 3; Health 90, Focus 90; Melee 4/defesa 14; Agility 5/defesa 15; Run 6; sem DR; dano impresso Melee `dM×3+4`, Agility `dM×5+5`. | O perfil lista Accuracy 2, Slow-Motion Dodge e várias técnicas de Ranged Weapons, incluindo Double Tap e Fast Hands. Um atirador básico com os mesmos atributos seria uma **versão restrita**, não Crossbones completo. |
| Kingpin (Wilson Fisk) | 194 / 195 | Rank 3; Health 90, Focus 60; Melee 5/**defesa 14**; Agility 1/**defesa 14**; Run 6; sem DR; dano Melee `dM×3+5`. | O trait **Big** explica Melee 14 (`10+5−1`) e Run 6 (`5+1`), mas deixa a defesa Agility 14 impressa sem explicação: `10+1−1=10`. Seu Reach 2, grapples e vários poderes de Martial Arts também faltam. Não corrigir silenciosamente a ficha oficial para caber no validador. |
| Misty Knight | 206 / 207 | Rank 3; Health 90, Focus 60; Melee 5/defesa 15; Agility 3/defesa 13; Run 5; sem DR; dano Melee `dM×5+5` (Mighty 2). | O motor cobre parte da pressão Melee e da cura, mas não modela sua bionic arm, Elemental Blast/Burst, Defense Stance, Brace for Impact ou Smash. |

Uma próxima bateria com esses nomes só deve usar perfis completos após auditar os poderes relevantes e adaptar o estado, ou ser rotulada explicitamente como **subconjunto mecânico do perfil oficial**. A regra **Big** foi conferida no Core p.60 (PDF p.61): ela reduz em 1 as defesas Melee e Agility, acrescenta 1 a Run e dá Reach 2. Ela **não** resolve Agility 14 de Kingpin; a diferença deve ficar aberta até outra fonte oficial ou decisão da mesa. A decisão recente sobre rolagem de dano da mesa pode alterar as expressões usadas em qualquer simulação, mas os números acima são transcrições da **impressão oficial** e permanecem separados das house rules.

O primeiro contrato isolado para [Slow-Motion Dodge](SLOW_MOTION_DODGE_EXPERIMENT.md)
está em desenvolvimento experimental. Ele ainda não integra os confrontos nem
libera Crossbones ou qualquer outra ficha completa no catálogo.
