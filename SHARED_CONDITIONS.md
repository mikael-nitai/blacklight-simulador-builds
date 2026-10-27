# Expiração comum entre os protótipos de combate

27/10/2026. A ponte de duração foi extraída para `combatants/condition_bridge.py`. `ConditionTiming` conserva um snapshot imutável dos campos relevantes; `turn_start_plan` valida todo o elenco, contador e escopo antes de planejar as expirações. `expire_at_turn_start` confere também os nomes e o registrador de eventos antes de limpar qualquer flag. Os campos dos combatentes continuam sendo o estado autoritativo.

| Chamador | Escopo que preserva |
|---|---|
| ModularDuel | Dodge do ator e Stunned de todos os alvos, na ordem original |
| GroupBattle | Stunned dos três atores; não implementa Dodge |
| FocusDuel | Stunned apenas do outro alvo; mantém a guarda de inconsciência/shattered antes de avançar o relógio |
| CorridorDuel | herda a camada modular de ações e duração, mantendo seus movimentos e auditoria geométrica |

O planejador aceita elencos de tamanho arbitrário; isso não remove a limitação de três atores do protótipo Group nem adiciona poderes aos demais. A integração do limite de fim de rodada continua pendente, inclusive para o caso em que o causador perde seu próximo turno. A ponte não torna autocast uma habilidade legal; as diferenças dos protótipos nesse estado sintético foram guardadas como gates de migração.

## Evidência do snapshot antes da nova implementação de Fast

A suíte passou em 189 testes. A revisão independente criou `scripts/audit_shared_conditions.py`: 57.528 combinações com oráculo direto, cinco gates da ponte, oito turnos forçados (incluindo KO, shattered e rodada bônus), 300 lutas diferenciais e três demos completos congelados de grupo, Focus e corredor. Estados, logs e geometria coincidiram. O primeiro achado — callback ou nome inválido causando mutação antes do erro — foi corrigido e guardado em testes.

As classes antigas usadas pelo diferencial compartilham helpers atuais de dados, Fighter e políticas. Essa comparação isola a refatoração de duração; não certifica a aritmética histórica após mudanças de regra. Os hashes dos runners das extensões agora incluem a camada `combatants/`, que passou a ser uma dependência real.

O mestre alterou Fast Strikes durante esta etapa. A revisão acima não valida essa decisão nova, que exige motor, oráculos e experimentos próprios. Para continuar verificando só a duração, sem pressupor igualdade de combates sob outra regra:

```powershell
python -B -m scripts.audit_shared_conditions --timing-only
python -m unittest tests.test_shared_conditions -q
```

Os dados anteriores e seus commits permanecem preservados pelo [controle de versões](RESULT_VERSIONING.md).
