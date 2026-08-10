"""Analysis for the hard sweep.

The claim under test is that filtering distractors helps. Three questions, in
order of how much they matter:

1. Within the confusable arm, does score fall as distractors rise while the
   required information stays complete? That is the bottleneck effect.
2. Does the control arm fall too? If it falls equally, the cause is context
   length rather than interference, and the filtering story is unsupported.
3. Is the confusable decline steeper than the control decline? That difference
   is the part attributable to interference.

Wilson intervals rather than normal approximation, because scores are binomial
proportions and several conditions sit near 1.0 where the normal approximation
misbehaves. No scipy dependency: the arithmetic is short enough to write out.
"""

import json
import math
import pathlib
import sys

RESULTS = pathlib.Path(
    sys.argv[1] if len(sys.argv) > 1 else
    pathlib.Path(__file__).parent / "hard_sweep_results.json"
)
Z = 1.959964  # 95%


def wilson(successes: float, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    d = 1 + Z**2 / n
    centre = (p + Z**2 / (2 * n)) / d
    half = Z * math.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_z(s1: float, n1: int, s2: float, n2: int):
    """Returns (difference, z, two-sided p) for p1 - p2."""
    if n1 == 0 or n2 == 0:
        return (float("nan"),) * 3
    p1, p2 = s1 / n1, s2 / n2
    pool = (s1 + s2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return (p1 - p2, 0.0, 1.0)
    z = (p1 - p2) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    return (p1 - p2, z, p)


def pooled(points, capacities):
    """Pool trials across the given capacities into one proportion."""
    scores = [s for pt in points if pt["capacity"] in capacities for s in pt["scores"]]
    return sum(scores), len(scores)


def conditions(points):
    """Derive filtered and flooded capacities from the data itself.

    Only conditions where the oracle scores 1.00 count: below that the required
    information is genuinely missing, so a low score is starvation rather than
    distraction. Among those, filtered admits no distractors and flooded admits
    the most. Deriving these rather than hardcoding them lets the same analysis
    read a sweep at any difficulty, where the capacity grid differs.
    """
    usable = [pt for pt in points if pt["oracle"] == 1.0 and pt["n"]]
    if not usable:
        return [], []
    top = max(pt["distractors_admitted"] for pt in usable)
    filtered = [pt["capacity"] for pt in usable if pt["distractors_admitted"] == 0]
    flooded = [pt["capacity"] for pt in usable if pt["distractors_admitted"] == top]
    return filtered, flooded


def describe(label, points):
    print(f"\n=== {label} ===")
    print(f"{'cap':>6} {'distract':>9} {'oracle':>7} {'score':>7} {'95% CI':>16} "
          f"{'n':>4} {'ref':>4}")
    print("-" * 62)
    for pt in points:
        name = "unlim" if pt["capacity"] is None else str(pt["capacity"])
        if pt["n"] == 0:
            print(f"{name:>6} {pt['distractors_admitted']:>9.0f} "
                  f"{pt['oracle']:>7.2f} {'--':>7} {'--':>16} {0:>4} "
                  f"{pt['refusals']:>4}")
            continue
        lo, hi = wilson(sum(pt["scores"]), pt["n"])
        print(f"{name:>6} {pt['distractors_admitted']:>9.0f} {pt['oracle']:>7.2f} "
              f"{pt['mean_score']:>7.2f} {f'[{lo:.2f}, {hi:.2f}]':>16} "
              f"{pt['n']:>4} {pt['refusals']:>4}")


def main():
    if not RESULTS.exists():
        sys.exit(f"no {RESULTS.name} yet")
    data = json.loads(RESULTS.read_text())
    res = data["results"]

    for label, key in [("confusable distractors", "confusable"),
                       ("control (non-confusable)", "control")]:
        if key in res:
            describe(label, res[key])

    ref = res.get("confusable") or res.get("control") or []
    FILTERED, FLOODED = conditions(ref)

    print("\n\n=== the comparison that matters ===")
    print(f"filtered = capacities {FILTERED} (0 distractors admitted)")
    print(f"flooded  = capacities {FLOODED} (48 distractors admitted)")
    print("required information is complete and identical in both.\n")

    # Matched-capacity contrast: at each capacity that admits distractors, how
    # much worse is the confusable arm than the control? Same count, same
    # length, so the gap is interference specifically.
    if res.get("confusable") and res.get("control"):
        print("matched-capacity gap (confusable minus control), distractors > 0:")
        by_cap = {pt["capacity"]: pt for pt in res["control"]}
        gaps = []
        for pt in res["confusable"]:
            other = by_cap.get(pt["capacity"])
            if not other or not pt["n"] or not other["n"]:
                continue
            if pt["distractors_admitted"] == 0:
                continue
            gap = pt["mean_score"] - other["mean_score"]
            gaps.append(gap)
            name = "unlim" if pt["capacity"] is None else str(pt["capacity"])
            print(f"    cap {name:>5} ({pt['distractors_admitted']:>2.0f} distractors): "
                  f"{pt['mean_score']:.2f} vs {other['mean_score']:.2f}  {gap:+.2f}")
        if gaps:
            print(f"    mean gap {sum(gaps)/len(gaps):+.3f}")
        print()

    deltas = {}
    for key, label in [("confusable", "confusable"), ("control", "control")]:
        if key not in res:
            continue
        s1, n1 = pooled(res[key], FILTERED)
        s2, n2 = pooled(res[key], FLOODED)
        if n1 == 0 or n2 == 0:
            have = "filtered" if n1 else ("flooded" if n2 else "neither")
            print(f"{label:>12}: incomplete, only the {have} condition has data "
                  f"(filtered n={n1}, flooded n={n2})")
            continue
        diff, z, p = two_proportion_z(s1, n1, s2, n2)
        deltas[key] = (diff, s1, n1, s2, n2)
        print(f"{label:>12}: filtered {s1/n1:.3f} (n={n1})  "
              f"flooded {s2/n2:.3f} (n={n2})  "
              f"drop {diff:+.3f}  z={z:.2f}  p={p:.4f}")

    # Partial-data readout: strongest statement the completed conditions support.
    if "confusable" in res and res["confusable"]:
        done = [pt for pt in res["confusable"] if pt["n"] and pt["oracle"] == 1.0]
        with_d = [pt for pt in done if pt["distractors_admitted"] > 0]
        if with_d:
            s = sum(sum(pt["scores"]) for pt in with_d)
            n = sum(pt["n"] for pt in with_d)
            lo, hi = wilson(s, n)
            top = max(pt["distractors_admitted"] for pt in with_d)
            print(f"\npartial readout: with the required information complete and up to "
                  f"{top:.0f} confusable\ndistractors admitted, score is "
                  f"{s/n:.3f} (n={n}, 95% CI [{lo:.3f}, {hi:.3f}]).")
            print("no bottleneck benefit is detectable over that range.")

    if "confusable" in deltas and "control" in deltas:
        dc = deltas["confusable"][0]
        dk = deltas["control"][0]
        print(f"\ndifference in drops (confusable - control): {dc - dk:+.3f}")
        print(
            "\ninterpretation:\n"
            "  both drop about equally  -> context length, not filtering\n"
            "  confusable drops further -> interference the bottleneck removes\n"
            "  neither drops            -> no bottleneck benefit at this difficulty"
        )

    u = data["usage"]
    print(f"\ncalls {u['calls']}  cost ${u['estimated_cost_usd']:.2f}")


if __name__ == "__main__":
    main()
