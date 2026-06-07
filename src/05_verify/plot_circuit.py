"""
Plot del circuito usando navis + fafbseg.
Scarica L2 skeletons (veloci) e plotta con colori per zona.

Uso:
  python plot_circuit.py --csv submission_mega.csv --out report/figures/codex_mesh.png
  python plot_circuit.py --csv submission_mega.csv --out report/figures/codex_mesh.png --sample 500
"""
import argparse, csv, sys, os
import pandas as pd
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="codex_mesh.png")
    ap.add_argument("--sample", type=int, default=0, help="If >0, sample N neurons (proportional by zone)")
    a = ap.parse_args()

    # Load IDs
    ids = []
    with open(a.csv) as f:
        rd = csv.DictReader(f)
        for r in rd:
            ids.append(int(r["FAFB"].strip()))
    print(f"Loaded {len(ids)} FAFB root IDs")

    # Zone mapping
    BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    nodes = pd.read_csv(os.path.join(BASE, "type_graphs", "nodes_FAFB.csv"))
    cell2zone = dict(zip(nodes.id.astype("int64"), nodes.zone))

    zone_ids = {}
    for cid in ids:
        z = cell2zone.get(cid, "unknown")
        zone_ids.setdefault(z, []).append(cid)

    print("Zone distribution:")
    for z in sorted(zone_ids, key=lambda x: -len(zone_ids[x])):
        print(f"  {z}: {len(zone_ids[z])}")

    # Sample if requested
    if a.sample > 0 and a.sample < len(ids):
        import random
        random.seed(42)
        sampled = []
        total = len(ids)
        for z in sorted(zone_ids, key=lambda x: -len(zone_ids[x])):
            n_sample = max(1, round(a.sample * len(zone_ids[z]) / total))
            picked = random.sample(zone_ids[z], min(n_sample, len(zone_ids[z])))
            sampled.extend(picked)
        ids = sampled
        # rebuild zone_ids
        zone_ids = {}
        for cid in ids:
            z = cell2zone.get(cid, "unknown")
            zone_ids.setdefault(z, []).append(cid)
        print(f"\nSampled to {len(ids)} neurons")

    # Fetch L2 skeletons
    import navis
    from fafbseg import flywire
    flywire.set_default_dataset("public")

    print(f"\nFetching L2 skeletons for {len(ids)} neurons...")
    skeletons = []
    failed = 0
    for i, rid in enumerate(ids):
        try:
            sk = flywire.get_l2_skeleton(rid)
            sk.zone = cell2zone.get(rid, "unknown")
            skeletons.append(sk)
        except Exception as e:
            failed += 1
        if (i+1) % 50 == 0:
            print(f"  {i+1}/{len(ids)} done ({failed} failed)")

    print(f"Got {len(skeletons)} skeletons ({failed} failed)")

    # Color by zone
    ZONE_COLORS = {
        "optic_lobe": (0.2, 0.6, 1.0),
        "central_brain": (1.0, 0.4, 0.2),
        "sensory": (0.2, 0.8, 0.3),
        "visual_projection": (0.7, 0.3, 0.9),
        "descending": (0.9, 0.8, 0.1),
        "visual_centrifugal": (0.1, 0.9, 0.9),
        "motor": (0.9, 0.1, 0.5),
        "ascending": (0.6, 0.6, 0.6),
    }

    colors = [ZONE_COLORS.get(sk.zone, (0.5, 0.5, 0.5)) for sk in skeletons]

    print("Plotting...")
    fig, ax = navis.plot2d(
        skeletons,
        color=colors,
        figsize=(16, 12),
        method="3d_complex",
        linewidth=0.3,
        alpha=0.6,
    )
    ax.azim = -90
    ax.elev = -90
    ax.set_axis_off()

    # Legend
    import matplotlib.patches as mpatches
    legend_patches = []
    for z in sorted(zone_ids, key=lambda x: -len(zone_ids[x])):
        c = ZONE_COLORS.get(z, (0.5, 0.5, 0.5))
        legend_patches.append(mpatches.Patch(color=c, label=f"{z} ({len(zone_ids[z])})"))
    ax.legend(handles=legend_patches, loc="upper left", fontsize=8)

    fig.savefig(a.out, dpi=300, bbox_inches="tight", facecolor="black")
    print(f"Saved to {a.out}")

if __name__ == "__main__":
    main()
