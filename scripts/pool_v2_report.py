"""Build a local report from validated v2 result JSONs, without resimulation."""

import json
from math import sqrt

from blacklight.experiment import ROOT, wilson
from .verify_sources import verify_result


LABELS = {
    'bare_attack': 'Ataque sem arma', 'hammer': 'Marreta',
    'blade_hammer_fast': 'Fast: Lâmina + Marreta',
    'shield_blade_reactive': 'Fast: duas parcelas de Lâmina; Escudo por reação',
    'shield_hammer_reactive': 'Marreta + Escudo reativo',
    'shield_blade_hammer_reactive': 'Fast: Lâmina + Marreta; Escudo por reação',
}
SCENARIOS = {'mirror_attack': 'Espelho com ataque comum',
             'mirror_hammer': 'Espelho com Marreta',
             'mirror_shield': 'Espelho com Marreta/Escudo',
             'gunner_kiter': 'Atirador com munição, campo aberto',
             'H1_rank4_bruiser': 'Reserva: combatente Rank 4',
             'H2_rank4_energy_kiter': 'Reserva: atirador de energia Rank 4'}


def read_verified(name: str) -> dict:
    path = ROOT / 'results' / name
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('damage_model') != 'literal_marvel_pool_v2':
        raise ValueError(f'{name}: wrong damage model')
    _, issues = verify_result(path)
    if issues:
        raise ValueError(f'{name}: {issues}')
    for row in data.get('rows', []):
        n = row['n']
        counts = row['outcomes']
        if sum(counts.values()) != n or any(type(v) is not int or v < 0 for v in counts.values()):
            raise ValueError(f'{name}: invalid outcome ledger')
        if 'win_rate' in row and row['win_rate'] != counts['win'] / n:
            raise ValueError(f'{name}: win rate disagrees with counts')
    return data


def pct(value: float) -> str:
    return f'{100 * value:.2f}%'.replace('.', ',')


def ci(k: int, n: int) -> str:
    low, high = wilson(k, n)
    return f'{pct(k/n)} [{pct(low)}; {pct(high)}]'


def difference(a: dict, b: dict, *, comparisons: int) -> tuple[float, float, float]:
    """Independent-score/Newcombe difference with Bonferroni family control."""
    pa, pb = a['outcomes']['win']/a['n'], b['outcomes']['win']/b['n']
    la, ua = wilson(a['outcomes']['win'], a['n'], alpha=0.05/comparisons)
    lb, ub = wilson(b['outcomes']['win'], b['n'], alpha=0.05/comparisons)
    delta = pa - pb
    return delta, delta - sqrt((pa-la)**2 + (ub-pb)**2), delta + sqrt((ua-pa)**2 + (pb-lb)**2)


def main() -> None:
    confirm = read_verified('pool_v2_confirm_summary.json')
    holdout = read_verified('pool_v2_holdout_summary.json')
    group = read_verified('group_pool_v2_description_summary.json')
    focus = read_verified('focus_pool_v2_description_summary.json')
    corridor = read_verified('corridor_pool_v2_description_summary.json')
    lines = ['# Resultados históricos da primeira versão de dano literal', '',
             '**O balanceamento posterior de Fast Strikes mudou para um teste por braço e efeitos de um único braço escolhido. '
             'As tabelas abaixo usam o contrato anterior; não medem a regra atual de '
             '[FAST_STRIKES_RULING.md](FAST_STRIKES_RULING.md).**', '',
             '27/10/2026. As tabelas desta versão usam vários dados Marvel de dano: cada face 1 vale 6. '
             'A replicação contém 240.000 duelos e a reserva 120.000, além de 52.000 duelos de desenvolvimento. '
             'Os resultados da fórmula anterior permanecem históricos em `results/legacy_scalar_v1/`.', '',
             'Entre as políticas testadas, **Lâmina + Marreta em Fast Strikes com Escudo reativo** teve a maior taxa de vitória '
             'nos três cenários de contato da replicação e no combatente Rank 4 reservado. Isso sustenta uma recomendação '
             'condicional para contato. Contra o atirador de energia Rank 4 em campo aberto, essa mesma política perdeu '
             '83,52% das lutas. Não foi estabelecida uma estratégia universal nem um resultado contra fichas oficiais completas.', '',
             '## Método e regra usada', '',
             'As seis finalistas foram escolhidas no desenvolvimento e fixadas em [POOL_V2_CONFIRM_SPEC.md](POOL_V2_CONFIRM_SPEC.md) '
             'antes da replicação e da reserva. Cada célula abaixo tem 10.000 sementes novas e independentes por política. '
             'Os quatro cenários da replicação já eram conhecidos; os dois perfis reservados foram definidos antes de observar seus resultados. '
             'Os adversários são sintéticos e usam políticas explícitas. As frequências dos encontros da campanha são desconhecidas, '
             'portanto não se calcula uma média global de vitória.', '',
             'Os hashes dos JSONs e suas fontes estão vinculados a commits imutáveis em '
             '[results/source_snapshots.json](results/source_snapshots.json). A verificação usa essa versão declarada '
             'quando o código atual evolui; não atribui taxas antigas automaticamente ao motor novo.', '',
             'Marreta usa oito dados de dano antes de DR, Lâmina e Garra sete. Fast Strikes faz um teste com duas edges '
             'e aplica dois componentes. No acerto comum, DR reduz a quantidade de dados de cada componente antes da metade, '
             'com piso nos dados ímpares e metade do bônus +6. Sem DR, Lâmina + Marreta usa `3d6+3 + 4d6+3`; '
             'no fantástico usa `7d6+6 + 8d6+6`, sem dobro adicional. Um ataque normal fantástico dobra seu total rolado. '
             'Bleeding não acumula; o fantástico da Marreta aplica Stunned; o da Lâmina pode conceder apenas uma segunda ação '
             'no próprio turno, com nova rolagem. O Escudo é uma ação defensiva separada.', '',
             '## Replicação e reserva', '',
             'Taxas entre colchetes são intervalos Wilson de 95% por célula. Vitória exige incapacitar o adversário primeiro. '
             'Inconclusão após 30 rodadas e empate não contam como vitória.', '',
             '| Cenário | Política | Vitória, IC 95% | Derrotas | Inconclusões | Empates |',
             '|---|---|---:|---:|---:|---:|']
    rows = confirm['rows'] + holdout['rows']
    for row in rows:
        c = row['outcomes']
        lines.append(f"| {SCENARIOS[row['scenario']]} | {LABELS[row['strategy']]} | {ci(c['win'], row['n'])} | {c['loss']} | {c['inconclusive']} | {c['draw']} |")
    lines += ['', 'A finalista com Escudo venceu 98,52%, 78,74% e 70,43% nos três espelhos de contato e 91,49% na reserva de contato Rank 4. '
              'Contra o atirador com munição, venceu 8,59%, teve zero derrotas observadas e 91,41% de inconclusões. '
              'Contra o atirador de energia reservado, venceu 7,75%, perdeu 83,52% e ficou inconclusiva em 8,73%. '
              'A imunidade à munição explica a sobrevivência no primeiro atirador; ela não resolve a necessidade de alcançá-lo.', '',
              '## Comparações com controles', '',
              'Diferenças de taxa de vitória da finalista com Escudo contra dois controles. Intervalos de diferença '
              'usam Wilson/Newcombe para amostras independentes e Bonferroni em uma família de 12 comparações '
              '(seis cenários × dois controles). Valores são pontos percentuais; a análise foi acrescentada após as contagens, '
              'portanto é uma comparação descritiva ajustada, sem uma nova alegação de pré-registro.', '',
              '| Cenário | Contra | Diferença [intervalo simultâneo] |', '|---|---|---:|']
    for scenario in SCENARIOS:
        block = {r['strategy']: r for r in rows if r['scenario'] == scenario}
        for control in ('hammer', 'blade_hammer_fast'):
            delta, low, high = difference(block['shield_blade_hammer_reactive'], block[control], comparisons=12)
            values = f'{100*delta:+.2f} [{100*low:+.2f}; {100*high:+.2f}]'.replace('.', ',')
            lines.append(f'| {SCENARIOS[scenario]} | {LABELS[control]} | {values} |')
    lines += ['', '## Extensões descritivas', '',
              'Estas baterias usam sementes novas e a mesma regra de dano, mas recortes próprios. São 60.000 combates em cada extensão. '
              'Há 600 trilhas completas auditadas em cada uma; não são encontros de campanha com todo o sistema implementado.', '',
              '### Dois inimigos em contato fixo', '',
              'G1 usa dois Rank 2 básicos; G2, dois Rank 3 básicos. Fast Strikes deste protótipo usa punhos, sem armas biológicas. '
              'A distribuição entre dois alvos é uma extensão conservadora descrita em [GROUP_POOL_V2_ADDENDUM.md](GROUP_POOL_V2_ADDENDUM.md).', '',
              '| Cenário | Política | Vitória, IC 95% | Rodadas médias |', '|---|---|---:|---:|']
    for r in group['rows']:
        lines.append(f"| {r['scenario']} | {r['policy']} | {ci(r['outcomes']['win'],r['n'])} | {r['mean_rounds']:.2f} |")
    lines += ['', 'Zero derrotas observadas com Marreta/Escudo em G2 resulta do perfil dos inimigos: Rank 3 sem bônus de dano '
              'tem três dados, e Escudo + Sturdy reduzem três. Isso não demonstra invulnerabilidade contra um grupo com poderes variados.', '',
              '### Mental Punch', '',
              'A tabela usa apenas **F0**, a decisão válida de que Escudo reduz Health e não Focus. F2 permanece nos JSONs como '
              'contrafactual e não representa uma opção permitida da mesa. O inimigo permanece em contato e usa apenas Mental Punch.', '',
              '| Perfil | Política | Vitória, IC 95% | Demoralized alguma vez |', '|---|---|---:|---:|']
    for r in focus['rows']:
        if r['variant'] == 'F0':
            lines.append(f"| {r['scenario']} | {r['strategy']} | {ci(r['outcomes']['win'],r['n'])} | {pct(r['ever_demoralized']/r['n'])} |")
    lines += ['', '### Atirador em corredor limitado', '',
              'Comprimentos de 12 e 20 espaços, sem cobertura ou caminhos alternativos. C1 usa munição; C2 é Rank 4 sem munição. '
              'O atirador continua com sua política de recuo e encontra a parede. O forte resultado aqui e a falha no campo aberto '
              'mostram a dependência da geometria; o adversário não recebeu uma nova política adaptada à parede.', '',
              '| Comprimento | Perfil | Política | Vitória, IC 95% |', '|---:|---|---|---:|']
    for r in corridor['rows']:
        lines.append(f"| {r['length']} | {r['opponent']} | {r['policy']} | {ci(r['outcomes']['win'],r['n'])} |")
    lines += ['', '## Auditoria e limites', '',
              'O motor foi salvo no commit `dbce72f`. A camada genérica de fichas foi acrescentada em `3af6672`, preservando '
              'os replays anteriores. Ao consolidar a versão v2, a suíte tinha 119 testes aprovados; etapas posteriores estão no README. O teste cruzado recalcula 100 trilhas por célula '
              'de 13 políticas × quatro cenários. Os auditores recalculam dano pelas faces registradas sem importar a função '
              'de dano de produção. Os JSONs registram hashes, sementes e políticas; `python -m scripts.verify_sources` verifica suas fontes.', '',
              'O contador de dano mitigado usa faces contrafactuais adicionais para estimar a diferença acoplada sem DR; '
              'esse valor não é dano efetivamente recebido. As rolagens de acerto e dano usam fontes aleatórias separadas. '
              'A recomendação acima se apoia em resultados de combate, e não em tratar mitigação amostrada como observação causal direta.', '',
              'Permanecem pendentes: fichas oficiais completas, adversários com repertório mais amplo, Karma, concentração geral, '
              'controle e movimento compartilhados entre motores, grupos com posições próprias, penalidades numéricas de membros e '
              'todas as famílias de poderes/variantes. A [arquitetura de fichas](CHARACTER_PIPELINE.md) já permite importar e versionar '
              'novos dados, mas bloqueia mecânicas sem suporte antes de simular. O exemplo Rank 4 dessa arquitetura é sintético.', '',
              '## Evidência e reprodução', '',
              '- [Replicação](results/pool_v2_confirm_summary.json) e [reserva](results/pool_v2_holdout_summary.json).',
              '- [Grupo](results/group_pool_v2_description_summary.json), [Focus](results/focus_pool_v2_description_summary.json) e [corredor](results/corridor_pool_v2_description_summary.json).',
              '- [Vitória no contato reservado](results/pool_v2_demo_H1_fast_shield_0.json), [derrota para energia](results/pool_v2_demo_H2_fast_shield_0.json) e [inconclusão contra munição](results/pool_v2_demo_gunner_confirm_fast_shield_0.json).',
              '- Gerar este relatório novamente: `python -m scripts.pool_v2_report`.', '']
    output = ROOT / 'POOL_V2_REPORT.md'
    output.write_text('\n'.join(lines), encoding='utf-8')
    print(f'{output}: 36 duel rows, 12 adjusted comparisons, 24 extension rows; source hashes checked')


if __name__ == '__main__':
    main()
