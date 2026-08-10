"""Generate the paper's figures from the raw per-trial result JSONs.

Reads directly from the experiment output files rather than hardcoded numbers,
so a re-run of any experiment regenerates the figures with one command:

    ../.venv/bin/python make_figures.py

Outputs vector PDFs into figures/.
"""

import json
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).parent
GW = HERE.parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

BLUE = "#0E6E9E"
RUST = "#C0571A"
INK = "#12191B"
MUTED = "#5C6A6C"
GRID = "#D9E0DE"

plt.rcParams.update({
    "font.size": 9.5,
    "font.family": "sans-serif",
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.linewidth": 0.8,
    "figure.dpi": 150,
})

Z = 1.959964


def wilson(s, n):
    if not n:
        return float("nan"), float("nan")
    p = s / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# ---------------------------------------------------------------- figure 1
def fig_dose_response():
    data = json.loads((GW / "dose_response_results.json").read_text())["results"]
    doses = [0, 6, 12, 24, 48]

    fig, ax = plt.subplots(figsize=(4.9, 3.2))
    for arm, color, label in [("control", RUST, "control (easily rejected)"),
                              ("confusable", BLUE, "confusable")]:
        xs, ys, lo, hi = [], [], [], []
        for d in doses:
            scores = data[str(d)][arm]
            s, n = sum(scores), len(scores)
            l, h = wilson(s, n)
            xs.append(d)
            ys.append(s / n)
            lo.append(s / n - l)
            hi.append(h - s / n)
        ax.errorbar(xs, ys, yerr=[lo, hi], color=color, lw=1.6,
                    marker="o", ms=4.5, capsize=2.5, elinewidth=0.9,
                    label=label, zorder=3)
        ax.annotate(f"{ys[-1]:.3f}", (xs[-1], ys[-1]),
                    textcoords="offset points", xytext=(8, -3),
                    color=color, fontsize=9, fontweight="bold")

    ax.set_xlabel("distractors reaching the controller")
    ax.set_ylabel("accuracy")
    ax.set_xticks(doses)
    ax.set_ylim(0.54, 0.80)
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_dose_response.pdf")
    plt.close(fig)
    print("fig1_dose_response.pdf")


# ---------------------------------------------------------------- figure 2
def fig_leak_rates():
    systems = ["architectural", "prompted_weak", "prompted_mid",
               "prompted_strict", "bare"]
    labels = ["architectural", "prompted (weak)", "prompted (mid)",
              "prompted (strict)", "bare"]

    def leaks(fname):
        d = json.loads((GW / fname).read_text())["results"]
        out = {}
        for s in systems:
            rows = d.get(s, [])
            rows = [r for r in rows if "constraint_verdict" in r]
            n = len(rows)
            k = sum(1 for r in rows if r["constraint_verdict"] == "leaked")
            out[s] = (k, n)
        return out

    gwt = leaks("prompted_passing_gwt2.json")
    ast = leaks("prompted_passing_ast1.json")

    fig, ax = plt.subplots(figsize=(5.4, 3.5))
    y = list(range(len(systems)))[::-1]
    h = 0.34

    for off, data, color, label in [(+h / 2 + 0.02, gwt, BLUE, "GWT-2 (workspace wording)"),
                                    (-h / 2 - 0.02, ast, RUST, "AST-1 (attention wording)")]:
        for yi, s in zip(y, systems):
            k, n = data[s]
            if n == 0:
                continue
            p = k / n
            lo, hi = wilson(k, n)
            ax.barh(yi + off, p, height=h, color=color, zorder=3)
            ax.errorbar(p, yi + off, xerr=[[p - lo], [hi - p]], color=INK,
                        elinewidth=0.8, capsize=2, zorder=4)
            note = f"{p:.2f}" + (f" (n={n})" if n < 350 else "")
            ax.annotate(note, (hi + 0.012, yi + off),
                        textcoords="offset points", xytext=(0, -2.6),
                        fontsize=7.6, color=INK, ha="left", xycoords="data")

    ax.set_yticks(y, labels)
    ax.set_xlabel("leak rate (supplied a value it implied it could not see)")
    ax.set_xlim(0, 1.32)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="GWT-2 (workspace wording)"),
                       Patch(color=RUST, label="AST-1 (attention wording)")],
              frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.17),
              ncols=2, fontsize=8.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_leak_rates.pdf")
    plt.close(fig)
    print("fig2_leak_rates.pdf")


# ---------------------------------------------------------------- figure 3
def fig_benefit_across_designs():
    """The estimated filtering benefit under successive designs."""

    def cell(fname, key):
        d = json.loads((GW / fname).read_text())["cells"][key]["scores"]
        return sum(d), len(d)

    designs = []

    s1, n1 = cell("focused_results.json", "confusable/filtered")
    s2, n2 = cell("focused_results.json", "confusable/flooded")
    designs.append(("unmatched\nrepetition\n(n=3000/cell)", s1, n1, s2, n2))

    s1, n1 = cell("focused_matched_results.json", "confusable/filtered")
    s2, n2 = cell("focused_matched_results.json", "confusable/flooded")
    designs.append(("repetition\nmatched\n(n=3000/cell)", s1, n1, s2, n2))

    d = json.loads((GW / "dose_response_results.json").read_text())["results"]
    b, f = d["0"]["confusable"], d["48"]["confusable"]
    designs.append(("dose-response\nendpoints\n(n=1200/cell)",
                    sum(b), len(b), sum(f), len(f)))

    fig, ax = plt.subplots(figsize=(5.2, 2.9))
    xs = range(len(designs))
    for i, (label, s1, n1, s2, n2) in enumerate(designs):
        p1, p2 = s1 / n1, s2 / n2
        diff = p1 - p2
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        ax.errorbar(i, diff, yerr=Z * se, color=BLUE, marker="o", ms=6,
                    capsize=3.5, elinewidth=1.1, zorder=3)
        ax.annotate(f"{diff:+.3f}", (i, diff), textcoords="offset points",
                    xytext=(9, 2), fontsize=9, color=INK)

    ax.axhline(0, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.set_xticks(list(xs), [d[0] for d in designs], fontsize=8.0)
    ax.set_ylabel("estimated filtering benefit")
    ax.set_xlim(-0.45, len(designs) - 0.35)
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_benefit_designs.pdf")
    plt.close(fig)
    print("fig3_benefit_designs.pdf")


if __name__ == "__main__":
    fig_dose_response()
    fig_leak_rates()
    fig_benefit_across_designs()
