# Fast Hands e Point-Blank Parry: contratos experimentais

Esses poderes constam na ficha oficial de Crossbones, mas ainda **não estão
conectados aos combates** nem incluídos no recorte que o enfrenta com Victor.

- **Fast Hands:** Core p. 99 (PDF p. 100). Fornece uma reação adicional por
  rodada, restrita a poderes do conjunto Ranged Weapons. O módulo
  `experimental/reaction_pools.py` separa as reações comuns dessa reação
  restrita, preserva a escolha de qual gastar e rejeita duas reações do mesmo
  personagem ao mesmo gatilho. O reset no começo da rodada segue a convenção
  conservadora já documentada do simulador.
- **Point-Blank Parry:** Core p. 112 (PDF p. 113). Após um inimigo em até dois
  espaços errar um ataque contra o personagem, uma reação e 5 Focus permitem
  um ataque à distância. O módulo `experimental/point_blank_parry.py` verifica
  o gatilho e os recursos, incluindo a reação restrita de Fast Hands; devolve
  apenas uma solicitação de ataque pendente. Ele ainda não rola ou aplica dano
  nem sangramento. O host deve aplicar dano regular em acerto, ou dano duplo
  e Bleeding em sucesso fantástico, sujeito às imunidades pertinentes.

Os módulos não validam, por si só, a legalidade completa da build nem controlam
alvos, iniciativa ou fila de eventos. A integração precisará respeitar a
decisão da mesa sobre Fast Strikes: ambos os testes e os efeitos dos dois braços
ocorrem antes das reações, com o Escudo tratado na janela já confirmada.
Também deve testar se Stunned ou incapacitação impedem a reação e como a reação
de arma interage com Riposte, Brawling e a trouble da submetralhadora. Enquanto
isso, qualquer resultado do recorte de Crossbones continua sem esses poderes.
