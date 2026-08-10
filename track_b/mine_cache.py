"""Mine the repo cache for every covariance result that is free. Zero API.

Two halves, matching what the cache actually contains:

  Reports. The prompted_passing runs hold self-reports for four run configs
  (GWT-2 and AST-1, on Haiku and Opus), all at one knob setting: architectural
  capacity 20. The capacity knob was never swept with reports attached, so the
  free report-side question is trial-level: at a FIXED knob, the delivered set
  still varies task by task, and set_tracking asks whether each system's
  claimed set follows that variation. For the imposters the interesting state
  is the set the real architecture would have held (arch_delivered): overlap
  above chance there is accidental tracking, the in-cache incarnation of the
  unlucky imposter.

  Behavior. The Experiment 1 sweeps varied capacity, and the dose-response run
  varied distractor count, with per-trial scores archived in the root JSONs.
  analyze() on (knob, score) shows which knobs demonstrably move behavior,
  and where ceilings make the knob invisible.

Writes track_b/cache_mining_results.json and prints a summary table.

Run from the repo root:
    .venv/bin/python track_b/mine_cache.py
"""

from __future__ import annotations

import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from covariance import analyze, set_tracking
from replay import RUNS, SYSTEMS, jaccard, replay_trial

REPO = pathlib.Path(__file__).parents[1]
OUT = pathlib.Path(__file__).parent / "cache_mining_results.json"

STRENGTH = {"prompted_weak": 1, "prompted_mid": 2, "prompted_strict": 3}


def mine_reports() -> dict:
    """Replay every archived self-report and score set tracking per system."""
    out = {}
    for run in RUNS:
        trials = json.loads((REPO / run.source_json).read_text())["config"]["trials"]
        assert trials == run.trials, f"{run.source_json}: config trials {trials}"
        run_key = f"{run.indicator}/{run.model}"
        out[run_key] = {}
        records_by_system = {}
        for system in SYSTEMS:
            records = []
            misses = 0
            for seed in range(run.trials):
                rec = replay_trial(run, system, seed)
                if rec is None:
                    misses += 1
                else:
                    records.append(rec)
            records_by_system[system] = records
            if not records:
                out[run_key][system] = {"n": 0, "misses": misses}
                continue

            claimed = [set(r["claimed"]) for r in records]
            held = [set(r["delivered"]) for r in records]
            arch = [set(r["arch_delivered"]) for r in records]
            required = [set(r["required"]) for r in records]

            track_held = set_tracking(claimed, held, seed=0, n_permutations=1000)
            track_arch = set_tracking(claimed, arch, seed=0, n_permutations=1000)
            n_claimed = [len(c) for c in claimed]
            req_frac = [
                len(c & r) / len(c) for c, r in zip(claimed, required) if c
            ]
            out[run_key][system] = {
                "n": len(records),
                "misses": misses,
                "mean_n_claimed": statistics.fmean(n_claimed),
                "sd_n_claimed": statistics.pstdev(n_claimed),
                "tracks_held_state": {
                    "mean_jaccard": track_held.mean_jaccard,
                    "null_mean": track_held.null_mean,
                    "p": track_held.p_value,
                },
                "tracks_arch_state": {
                    "mean_jaccard": track_arch.mean_jaccard,
                    "null_mean": track_arch.null_mean,
                    "p": track_arch.p_value,
                },
                "mean_required_fraction": (
                    statistics.fmean(req_frac) if req_frac else None
                ),
            }

        # The imposter's own knob: prompt strength. Reports (n_claimed) pooled
        # across the three prompted systems against strength 1/2/3.
        knobs, reports = [], []
        for system, strength in STRENGTH.items():
            for rec in records_by_system[system]:
                knobs.append(strength)
                reports.append(len(rec["claimed"]))
        if len(set(knobs)) > 1:
            r = analyze(knobs, reports, seed=0, n_permutations=1000)
            out[run_key]["prompt_strength_knob"] = {
                "rho": r.rho, "p": r.p_value, "n": r.n,
                "degenerate": r.degenerate,
            }
    return out


def mine_behavior() -> dict:
    """(knob, score) covariance from the archived sweep and dose files."""
    out = {}

    def sweep(path: str, label: str) -> None:
        p = REPO / path
        if not p.exists():
            return
        data = json.loads(p.read_text())
        for arm, rows in data["results"].items():
            # Two regimes, two claims. Below oracle 1.0 the capacity knob
            # starves the controller of required facts, so behavior tracking
            # the knob there means "the knob controls what arrives", which is
            # the mechanism the perturbation design relies on. At oracle 1.0
            # the information is complete and any residual slope would be the
            # distraction effect.
            regimes = {"starved_included": lambda o: True,
                       "oracle_complete": lambda o: o == 1.0}
            for regime, keep in regimes.items():
                knobs, scores = [], []
                excluded = []
                for row in rows:
                    cap = row["capacity"]
                    # Capacity 0 is a floor check (information absent) and
                    # None is unlimited (no numeric knob value); neither
                    # belongs on a dose curve.
                    if cap in (0, None) or not keep(row["oracle"]):
                        excluded.append(cap)
                        continue
                    knobs.extend([cap] * len(row["scores"]))
                    scores.extend(row["scores"])
                if len(set(knobs)) < 2:
                    continue
                r = analyze(knobs, scores, seed=0, n_permutations=1000)
                out[f"{label}/{arm}/{regime}"] = {
                    "model": data["config"]["model"],
                    "knob": "capacity_tokens",
                    "settings": sorted(set(knobs)),
                    "excluded_settings": excluded,
                    "rho": r.rho, "p": r.p_value, "n": r.n,
                    "degenerate": r.degenerate,
                    "mean_score": statistics.fmean(scores),
                }

    sweep("haiku_r12_results.json", "sweep_haiku_r12")
    sweep("hard_sweep_results_haiku_r8.json", "sweep_haiku_r8")
    sweep("hard_sweep_r14_sonnet-5.json", "sweep_sonnet_r14")
    sweep("hard_sweep_results.json", "sweep_opus_r8")

    dose = json.loads((REPO / "dose_response_results.json").read_text())
    arms = {}
    for count, cell in dose["results"].items():
        for arm, scores in cell.items():
            arms.setdefault(arm, ([], []))
            arms[arm][0].extend([int(count)] * len(scores))
            arms[arm][1].extend(scores)
    for arm, (knobs, scores) in arms.items():
        r = analyze(knobs, scores, seed=0, n_permutations=1000)
        out[f"dose_response/{arm}"] = {
            "model": dose["config"]["model"],
            "knob": "n_distractors",
            "settings": sorted(set(knobs)),
            "rho": r.rho, "p": r.p_value, "n": r.n,
            "degenerate": r.degenerate,
            "mean_score": statistics.fmean(scores),
        }
    return out


def main() -> None:
    reports = mine_reports()
    behavior = mine_behavior()
    results = {"reports": reports, "behavior": behavior}
    OUT.write_text(json.dumps(results, indent=2))

    print("\nREPORTS: does the claimed set track trial-level state at the "
          "fixed knob (capacity 20)?\n")
    print(f"{'run':>22} {'system':>16} {'n':>4} {'miss':>5} {'n_clm':>6} "
          f"{'J(held)':>8} {'null':>6} {'p':>7} {'J(arch)':>8} {'null':>6} {'p':>7}")
    for run_key, systems in reports.items():
        for system, row in systems.items():
            if system == "prompt_strength_knob":
                continue
            if row.get("n", 0) == 0:
                print(f"{run_key:>22} {system:>16} {'0':>4} {row['misses']:>5}")
                continue
            th, ta = row["tracks_held_state"], row["tracks_arch_state"]
            print(f"{run_key:>22} {system:>16} {row['n']:>4} {row['misses']:>5} "
                  f"{row['mean_n_claimed']:>6.1f} "
                  f"{th['mean_jaccard']:>8.3f} {th['null_mean']:>6.3f} {th['p']:>7.4f} "
                  f"{ta['mean_jaccard']:>8.3f} {ta['null_mean']:>6.3f} {ta['p']:>7.4f}")
        k = systems.get("prompt_strength_knob")
        if k:
            print(f"{run_key:>22} {'strength knob':>16} rho={k['rho']:.3f} "
                  f"p={k['p']:.4f} n={k['n']}")

    print("\nBEHAVIOR: does the score track the knob?\n")
    print(f"{'cell':>28} {'model':>16} {'knob':>14} {'n':>6} {'rho':>7} {'p':>7}")
    for cell, row in behavior.items():
        rho = "degen" if row["degenerate"] else f"{row['rho']:.3f}"
        print(f"{cell:>28} {row['model']:>16} {row['knob']:>14} {row['n']:>6} "
              f"{rho:>7} {row['p']:>7.4f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
