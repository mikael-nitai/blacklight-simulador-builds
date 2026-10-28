"""Create publication-style static figures from the frozen confirmation JSON.

Optional dependency: matplotlib. The simulator itself has no external deps.
"""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from blacklight.experiment import ROOT, source_hashes
from blacklight.results_io import require_new_output, write_new_text


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    names = ('fig_win_rates.png', 'fig_win_rates.svg', 'fig_s4_outcomes.png',
             'fig_s4_outcomes.svg', 'figures_manifest.json')
    try:
        for name in names:
            require_new_output(args.output_dir / name)
    except FileExistsError as exc:
        parser.error(str(exc))
    path = ROOT / "results" / "confirm_summary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["source_sha256"] != source_hashes():
        raise RuntimeError("confirmation result does not match current sources")
    rows = {(row["scenario"], row["strategy"]): row for row in data["rows"]}
    selected = [
        ("bare_attack", "Ataque básico"),
        ("hammer", "Marreta"),
        ("shield_hammer_reactive", "Escudo após acerto"),
        ("hammer_heal_t75_s15", "Marreta + cura"),
        ("shield_hammer_endturn", "Escudo no fim do turno"),
    ]
    scenes = [
        ("mirror_attack", "S1 · espelho básico"),
        ("mirror_hammer", "S2 · espelho Marreta"),
        ("mirror_shield", "S3 · espelho Escudo"),
        ("gunner_kiter", "S4 · atirador que recua"),
    ]
    colors = ["#64748b", "#2360ad", "#b64b27", "#7b4b9a", "#15816a"]
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, axs = plt.subplots(2, 2, figsize=(12, 8.5), sharex=True,
                            constrained_layout=True)
    for ax, (scene, title) in zip(axs.flat, scenes):
        y = np.arange(len(selected))[::-1]
        for i, (strategy, label) in enumerate(selected):
            row = rows[scene, strategy]
            p = 100 * row["win_rate"]
            lo, hi = (100 * v for v in row["win_ci95_wilson"])
            ax.errorbar(p, y[i], xerr=[[p - lo], [hi - p]], fmt="o",
                        color=colors[i], capsize=3, markersize=7)
            ax.text(min(p + 2.2, 96), y[i] + .11, f"{p:.1f}%",
                    fontsize=8, color=colors[i])
        ax.set_yticks(y, [label for _, label in selected])
        ax.set_xlim(0, 105)
        ax.set_xticks(range(0, 101, 20))
        ax.grid(axis="x", color="#e5e7eb")
        ax.set_title(title, loc="left", fontsize=11, weight="bold")
        ax.set_xlabel("Vitórias em 10 000 combates (%)")
    fig.suptitle("Blacklight Rank 3: vitórias por cenário e política",
                 fontsize=14, weight="bold")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'fig_win_rates.png').open('xb') as output:
        fig.savefig(output, format='png', dpi=180)
    with (args.output_dir / 'fig_win_rates.svg').open('xb') as output:
        fig.savefig(output, format='svg')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4.4), constrained_layout=True)
    y = np.arange(len(selected))[::-1]
    fractions = {key: np.array([
        rows["gunner_kiter", strategy]["outcomes"][key] / 100
        for strategy, _ in selected])
        for key in ("win", "loss", "inconclusive")}
    left = np.zeros(len(selected))
    for key, color, label in (("win", "#15816a", "Vitória"),
                              ("loss", "#b64b27", "Derrota"),
                              ("inconclusive", "#a9adb8", "Inconclusivo")):
        ax.barh(y, fractions[key], left=left, color=color, label=label)
        left += fractions[key]
    ax.set_yticks(y, [label for _, label in selected])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Desfechos em 10 000 combates (%)")
    ax.set_title("S4 · Atirador em campo aberto: sobreviver não é vencer",
                 loc="left", fontsize=12, weight="bold")
    ax.legend(loc="lower right", ncol=3)
    with (args.output_dir / 'fig_s4_outcomes.png').open('xb') as output:
        fig.savefig(output, format='png', dpi=180)
    with (args.output_dir / 'fig_s4_outcomes.svg').open('xb') as output:
        fig.savefig(output, format='svg')
    plt.close(fig)

    script = Path(__file__)
    manifest = {
        "source_sha256": source_hashes(),
        "confirm_summary_sha256": sha256(path.read_bytes()).hexdigest(),
        "plot_script_sha256": sha256(script.read_bytes()).hexdigest(),
        "figures": ["fig_win_rates.png", "fig_win_rates.svg",
                    "fig_s4_outcomes.png", "fig_s4_outcomes.svg"],
    }
    write_new_text(args.output_dir / 'figures_manifest.json', json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
