# Segunda família modular: ativação de estados

Esta página registra a etapa `modular_physical_duel_v2`. A evolução atual da duração está em [MODULAR_LIFECYCLE.md](MODULAR_LIFECYCLE.md); os exemplos abaixo permanecem congelados e ligados à versão executada.

27/10/2026. O executor genérico usa `modular_physical_duel_v2`. A autocura paga com Focus continua modular, e **Attack Stance, Dodge e a ativação padrão do Escudo** passaram a ser definições reutilizáveis da família `StateActivation`. Nenhum nome de personagem é usado para decidir esses efeitos.

| Definição | Requisito | Custo de Focus | Efeito de ativação | Referência |
|---|---|---:|---|---|
| Attack Stance | poder `attack_stance` | 0 | ativa stance se ainda inativo | Core p.83; POW-09 |
| Dodge | ação comum, sem poder obrigatório | 0 | ativa a defesa até o próximo turno | Core p.30; ACT-07 |
| Escudo padrão | arma `shield` | 0 | ativa o Escudo usando a ação padrão | decisão da mesa HR-04 |

As três gastam a ação padrão. Ativar sem pagar Focus continua permitido com Focus zero ou negativo; isso não elimina as condições associadas a Focus, que ainda dependem do modelo de combate utilizado. A ativação por reação do Escudo, a expiração de Dodge, a perda de concentração de Attack Stance e a desativação do Escudo ao atacar continuam no resolvedor físico anterior. Os efeitos de estado gravam os mesmos campos que esses caminhos já leem.

## Contrato das definições e execução

Os requisitos podem vir de poderes, traits ou armas e são conferidos em conjunto. O contexto do módulo contém apenas dados imutáveis. O módulo informa as ações disponíveis e um plano; o motor valida a ação, os tipos, os custos e o efeito antes de alterar o estado. Um pedido de custo zero deve usar inteiro `0`: valores `0.0` ou `False` são recusados, mesmo que Python os compare como iguais.

O contrato atual admite exatamente um efeito por plano em duas famílias já verificadas: autocura com Focus positivo ou ativação de estado com custo zero. Combinações múltiplas, ativação de estado paga e tipos de efeito desconhecidos são bloqueados. A ampliação para poderes com vários efeitos exige um ledger de ações agrupadas e uma auditoria própria; essa limitação não foi apresentada como cobertura completa do sistema.

Os construtores recusam referências de regras, fontes e requisitos em formatos inválidos. O motor também mantém a rejeição sem mutação para módulos customizados malformados. Um efeito não pode escolher um atributo arbitrário do combatente: os estados aceitos são `stance`, `shield_active` e `dodging`.

## Proveniência diretamente na API

`run_duel` e `run_batch` registram agora parâmetros completos dos módulos, requisitos, fontes, versão e implementação do Python e hashes do núcleo, da camada de fichas e do arquivo da política. Esse registro é produzido mesmo sem o comando de terminal. O manifesto é conferido no início e no fim; uma mudança de fonte durante a execução impede publicar o resultado. A CLI acrescenta seu próprio hash e os arquivos de fichas usados.

As políticas atuais do projeto usam a biblioteca padrão. Dependências transitivas de políticas Python externas ainda precisam de um manifesto próprio; esse limite é declarado nos resultados. Importar outra ficha compatível não exige trocar a política por código externo.

## Evidência executada

A suíte completa passou em **142 testes**. A [revisão independente](MODULAR_STATES_REVIEW.md) verificou 1.280 estados de legalidade, 240 transições, oito combinações de requisitos e 360 combates completos, com estados, métricas e logs iguais ao motor de referência. Os 36 testes direcionados e os dois retornos de API usados na revisão também passaram. As regressões da primeira família de cura continuam na suíte.

A revisão encontrou dois problemas de extensão, reproduzidos antes de corrigir: definições inválidas podiam ser listadas como legais, e pedidos de custo zero com tipos numéricos equivalentes passavam pela igualdade. Ambos foram corrigidos e guardados como testes. O [script independente](scripts/audit_modular_states.py) registra o snapshot final e seus limites.

Os [exemplos completos](scripts/modular_state_demos.py) usam a ficha atual de Victor e um oponente Rank 4 **sintético**, com políticas de controle da migração:

- [Attack Stance, semente 7](results/generic_sheet_stance_demo.json): duas ativações durante o combate; a perda de estado pode exigir reativação.
- [Escudo padrão, semente 8](results/generic_sheet_standard_shield_demo.json): quatro ativações com custo de ação padrão, alternadas com ataques.
- [Dodge, semente 9](results/generic_sheet_dodge_demo.json): dez ativações e resultado inconclusivo no horizonte de dez rodadas, preservado como inconclusão.

Esses controles demonstram execução e integração; não são uma comparação de eficiência estratégica. A bateria de troca de ficha de 1.000 duelos manteve as mesmas 2 vitórias e 998 derrotas observadas antes da refatoração. Os três artefatos da etapa modular anterior foram preservados em `results/modular_v1/`, ligados ao commit `b1e4d19`.

Reprodução:

```powershell
python -m unittest discover -s tests -q
python -B -m scripts.audit_modular_states
python -m scripts.modular_state_demos
python -m scripts.verify_sources
```

Ataques, condições, duração e reações ainda precisam convergir para módulos comuns a duelo, grupo, Focus e terreno. A cobertura completa de poderes e fichas oficiais permanece um objetivo posterior a esses gates, conforme [CHARACTER_PIPELINE.md](CHARACTER_PIPELINE.md).
