# Fast Hands e Point-Blank Parry: contratos experimentais

Esses poderes constam na ficha oficial de Crossbones. Agora estão conectados
ao executor experimental `experimental/parry_duel.py` e ao recorte ampliado
`build_crossbones_parry_subset`; a ficha oficial completa continua indisponível.

- **Fast Hands:** Core p. 99 (PDF p. 100). Fornece uma reação adicional por
  rodada, restrita a poderes do conjunto Ranged Weapons. O módulo
  `experimental/reaction_pools.py` separa as reações comuns dessa reação
  restrita, preserva a escolha de qual gastar e rejeita duas reações do mesmo
  personagem ao mesmo gatilho. O reset no começo da rodada segue a convenção
  conservadora já documentada do simulador.
- **Point-Blank Parry:** Core p. 112 (PDF p. 113). Após um inimigo em até dois
  espaços errar um ataque contra o personagem, uma reação e 5 Focus permitem
  um ataque à distância. O módulo `experimental/point_blank_parry.py` verifica
  o gatilho e os recursos; o host resolve o ataque com dano regular em acerto,
  ou dano duplo e Bleeding em sucesso fantástico, sujeito às imunidades.

O host respeita a decisão da mesa sobre Fast Strikes: ambos os testes e efeitos
dos dois braços ocorrem antes de Point-Blank Parry; Escudo mantém sua janela
confirmada. Se ambos os braços errarem, gatilhos distintos podem consumir a
reação restrita e uma comum; Stunned ou inconsciência impedem a reação. Riposte
não responde a um ataque à distância. Foram testadas reações encadeadas,
Brawling, Escudo contra munição, Focus e a trouble da submetralhadora.

O auditor `experimental/parry_audit.py` reconstrói os dois orçamentos, a fila
de oportunidades, cada gatilho, os custos de Focus e a associação entre o
ataque de reação e Bleeding. Depois utiliza as auditorias físicas existentes
em um modo opt-in para ataques e gastos de reação. O modo comum dessas auditorias
continua rejeitando esses eventos. O opt-in isolado não valida o gatilho nem o
orçamento restrito e só deve ser usado após `audit_parry_duel`; não é uma promoção do poder ao runner
certificado. O host ainda aborta auto-incapacitação por Ram, não modela
submetralhadora contra múltiplos alvos e, conservadoramente, não permite usar
Point-Blank Parry contra atacante inconsciente. Outras habilidades de
Crossbones, escolhas táticas e fichas completas continuam pendentes.
