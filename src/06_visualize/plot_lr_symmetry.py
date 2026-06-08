"""
Scatter plot: L vs R neuron count per cell type, coloured by class.
Shows bilateral symmetry of the conserved circuit (r=0.94).
Output: figures/lr_symmetry.pdf + .png
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ZONE_COLOURS = {
    "optic_lobe": "#4477AA",
    "central_brain": "#EE6677",
    "sensory": "#228833",
    "visual_projection": "#CCBB44",
    "descending": "#AA3377",
}
ZONE_LABELS = {
    "optic_lobe": "Optic lobe",
    "central_brain": "Central brain",
    "sensory": "Sensory",
    "visual_projection": "Visual proj.",
    "descending": "Descending",
}

sub = pd.read_csv(ROOT / "submission_mega.csv")
nodes_fafb = pd.read_csv(ROOT / "type_graphs" / "nodes_FAFB.csv").set_index("id")
fafb_ids = set(sub["FAFB"].values)
id2type = nodes_fafb["type"].to_dict()
id2zone = nodes_fafb["zone"].to_dict()
id2side = nodes_fafb["side"].to_dict()

type2zone = {}
type_side = defaultdict(Counter)
for i in fafb_ids:
    t, s, z = id2type.get(i), id2side.get(i), id2zone.get(i)
    if t and s and z:
        type_side[t][s] += 1
        type2zone[t] = z

# Only types with at least one L or R
data = []
for t, c in type_side.items():
    l, r = c.get("L", 0), c.get("R", 0)
    if l + r > 0:
        data.append((t, l, r, type2zone.get(t, "")))

ls = np.array([d[1] for d in data])
rs = np.array([d[2] for d in data])
zones = [d[3] for d in data]
names = [d[0] for d in data]
colours = [ZONE_COLOURS.get(z, "#BBBBBB") for z in zones]

# Correlation (only types with both > 0)
mask_both = (ls > 0) & (rs > 0)
corr = np.corrcoef(ls[mask_both], rs[mask_both])[0, 1]

fig, ax = plt.subplots(figsize=(5, 5))

# Diagonal
mx = max(ls.max(), rs.max()) * 1.1
ax.plot([0, mx], [0, mx], color="#CCCCCC", linewidth=1, linestyle="--", zorder=0)

# Scatter with slight transparency
ax.scatter(ls, rs, c=colours, s=20, alpha=0.7, edgecolors="white", linewidths=0.3, zorder=2)

# Label outliers and top types
for i, (t, l, r, z) in enumerate(data):
    total = l + r
    asym = abs(l - r) / (l + r) if (l + r) > 0 else 0
    if total >= 80 or (asym > 0.5 and total >= 8):
        ax.annotate(t, (l, r), fontsize=5, ha="left", va="bottom",
                    xytext=(3, 3), textcoords="offset points",
                    color=ZONE_COLOURS.get(z, "#333333"))

ax.set_xlabel("Left-hemisphere neurons", fontsize=9)
ax.set_ylabel("Right-hemisphere neurons", fontsize=9)
ax.set_title(f"Bilateral symmetry per cell type (r = {corr:.2f})", fontsize=10, fontweight="bold")
ax.set_aspect("equal")
ax.set_xlim(-2, mx)
ax.set_ylim(-2, mx)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Legend
handles = [Patch(facecolor=ZONE_COLOURS[z], label=ZONE_LABELS[z]) for z in ZONE_COLOURS]
ax.legend(handles=handles, fontsize=6, loc="upper left", framealpha=0.9)

plt.tight_layout()
out_dir = ROOT / "figures"
out_dir.mkdir(parents=True, exist_ok=True)
fig.savefig(out_dir / "lr_symmetry.pdf", bbox_inches="tight", dpi=300)
fig.savefig(out_dir / "lr_symmetry.png", bbox_inches="tight", dpi=200)
print(f"Saved to {out_dir / 'lr_symmetry.pdf'}")
