# Inventário da ficha de Victor Halle (Blacklight)

Data da auditoria: 2026-10-26. Este documento registra dados, não certifica a legalidade de poderes ou efeitos. Fonte primária desta conversa: `C:\Users\avada\Downloads\Ficha_victor Halle Rank 3.pdf`, SHA-256 `6C907DFCAA2AF39B904E6144466915BAFC6B6F66F407AEB312DEA112FD3200D1`. O PDF tem duas páginas; os dados abaixo foram lidos dos campos AcroForm e conferidos visualmente nas duas páginas. A página 2 está em branco.

## Ficha fornecida nesta conversa (fonte primária)

| Campo | Valor inscrito | Referência |
| --- | --- | --- |
| Nome e codinome | Victor Halle / Blacklight | PDF da ficha, p. 1 |
| Rank, Health, Focus, Karma | 3; 150; 90; 3 | p. 1 |
| Health Damage Reduction | 1 | p. 1 |
| Focus Damage Reduction | campo vazio | p. 1 |
| Melee | 6; Defense 16; Non-Combat 7 | p. 1 |
| Agility | 1; Defense 11; Non-Combat 2 | p. 1 |
| Resilience | 5; Defense 15; Non-Combat 6 | p. 1 |
| Vigilance | 2; Defense 12; Non-Combat 3 | p. 1 |
| Ego | 1; Defense 11; Non-Combat 2 | p. 1 |
| Logic | 0; Defense 10; Non-Combat 1 | p. 1 |
| Iniciativa | modificador 1 | p. 1 |
| Velocidades | Run 6 m; Climb 3 m; Swim 3 m | p. 1 |
| Dano Melee | `dMarvel × 6 + 6`, como escrito nos campos da ficha | p. 1 |
| Dano Agility | `dMarvel × 3 + 2`, como escrito; **incompatível com Agility 1** se o termo aditivo for a pontuação do atributo | p. 1 |
| Dano Ego | `dMarvel × 3 + 1` | p. 1 |
| Dano Logic | `dMarvel × 3 + 1`, como escrito; **incompatível com Logic 0** se o termo aditivo for a pontuação do atributo | p. 1 |
| Identidade | altura 1,88 m; peso 102 kg; gênero masculino; olhos castanhos; cabelo escrito como “Peto”; porte grande/musculoso; equipe Arca; base San Diego; origem Weird Science; profissão Military | p. 1 |

### Poderes inscritos

| Poder | Resumo escrito na ficha | Página indicada na ficha |
| --- | --- | --- |
| Mighty 1 | `+1 multiplicador melle` | 109 |
| Sturdy 1 | `- 1 multiplicador do inimigo` | 123 |
| Healing Factor | `Ao fim do turno regenera (resilencia) de Health` | 103 |
| Brawling | `Usa Melle para defender ataques de agilidade` | 86 |
| Fast Strikes | `faz dois ataques alvo sofre metade do dano` | não preenchida |
| Attack Stance | `Dobra o bônus de dano de Melee ( concentration)` | não preenchida |
| Riposte | `contra ataque caso errem um ataque` | não preenchida |
| Disguise | `muda a aparencia do victor` | não preenchida |
| Mighty 2 | sem resumo | não preenchida |
| Mighty 3 | `Eleva o bônus para +3. Seu ataque comum fica dMarvel × 6 + 6` | não preenchida |
| Do This All Day | `heals 2 points of Health for everypoint of Focus` | não preenchida |
| Blazing-Fast Fists | `edge on all Melee attacks` | não preenchida |

As grafias e resumos são transcrições dos campos, não descrições normativas. Mighty 1/2/3 aparecem como três linhas; a ficha não afirma expressamente que seus bônus se acumulam. A auditoria das regras deve decidir a progressão e os pré-requisitos.

### Traits, tags e outros campos

- Traits inscritos: Weird; Battle Ready (`+30 em focus`); Connections: Military; Situational Awareness (`vantagem em iniciativa`); Combat Reflexes (a ficha resume como `reação adicional por turno`, corrigida para **por rodada** pela errata oficial); Signature Attack (Fast Strikes).
- Tags inscritos: Obligation; Rich; Signature Weapon; Heróic.
- Nenhum campo preenchido detalha Garra, Lâmina, Chicote, Marreta ou Escudo, seus multiplicadores, condições, alcance, custos ou efeitos. A inscrição `Signature Weapon` não identifica a arma nem confere um efeito numérico verificável por si só.

## Fontes conflitantes e dados provisórios

Outra ficha, `C:\Users\avada\Documents\Codex\2026-09-13\para-meu-rpg-quero-que-voc\Ficha_victor_Halle_Rank3_revisada.pdf` (SHA-256 `E54B6D339C409C842C2E4467491D1D9314D00AAB068F9F74F7FEC37FA6E335DE`), também é Rank 3 e foi conferida pelos campos AcroForm e visualmente na p. 1. Ela **não substitui** a ficha explicitamente fornecida nesta conversa. Diferenças relevantes:

| Campo | Ficha fornecida (primária) | Outra ficha (referência conflitante) |
| --- | --- | --- |
| Focus | 90 | 60 |
| Agility / Vigilance | 1 / 2 | 2 / 1 |
| Iniciativa inscrita | 1 | `+1E` |
| Poder da sexta linha | Attack Stance | Extended Reach 1 |
| Trait Signature Attack (Fast Strikes) | presente | ausente |
| Combat Reflexes, como resumido | reação adicional por **turno** | por **rodada** |
| Tags | Signature Weapon; Heróic | Signature Weapon: arsenal biológico; sem Heróic |
| Melee Non-Combat | 7 | 9 |

O texto de missão fornecido pelo usuário menciona Focus 60 e Extended Reach 1, mas declara essas informações preliminares. Portanto, para implementação do personagem atual, os dados da ficha primária prevalecem; o cenário alternativo pode ser estudado apenas com rótulo explícito. Em especial, **Extended Reach 1 não está na ficha primária**. A discrepância foi comunicada à coordenação da pesquisa.

## Regra caseira e lacunas

**Atualização após esta auditoria da ficha:** o usuário esclareceu diretamente as cinco armas, a ação extra condicionada da Lâmina, a interação das armas ofensivas nos dois braços com Fast Strikes, e o Escudo como ação defensiva separada. O registro operacional atualizado é [RULES_AUDIT.md](RULES_AUDIT.md), HR-01 a HR-06. Essas decisões vêm da conversa, **não** do PDF da ficha; o Chicote foi declarado indisponível no Rank 3. A segunda ação da Lâmina exige um sucesso fantástico no primeiro teste de acerto do próprio turno, permite nova rolagem e pode usar Fast Strikes; um Riposte fantástico não a concede. O Escudo pode ser ativado com reação após ver um acerto e já protege contra esse golpe.

A ficha ainda não fornece texto do mestre para alcance e formação das armas, penalidade numérica de membro inutilizado, duração de imobilização ou a distribuição de efeitos entre dois alvos de Fast Strikes. O modelo de duelos implementa somente os aspectos definidos. Essas lacunas limitam a conclusão estratégica e são detalhadas no registro de regras.

## Metodologia de extração

- Pypdf leu os campos AcroForm de ambas as páginas de cada ficha.
- Poppler renderizou a página 1 de cada versão e a página 2 da fonte primária; as imagens confirmaram os atributos, recursos, poderes, traits e tags listados e a ausência de dados na página 2.
- O texto de página extraído sem AcroForm contém apenas os rótulos do formulário, por isso as conclusões usam os valores dos campos e a revisão visual.
- Os resumos inscritos na ficha permanecem dados do jogador; a auditoria normativa deve verificar cada efeito no Core Rulebook, FAQ, errata e regras da mesa.
