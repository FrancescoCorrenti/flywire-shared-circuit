"""
Bar chart: top 50 cell types by neuron count, coloured by class.
Matches the colour palette of the network graph.
Output: figures/cells_per_type.pdf + .png
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Colours matching network graph
ZONE_COLOURS = {
    "optic_lobe": "#4477AA",
    "central_brain": "#EE6677",
    "sensory": "#228833",
    "visual_projection": "#CCBB44",
    "descending": "#AA3377",
    "visual_centrifugal": "#66CCEE",
    "motor": "#BBBBBB",
    "ascending": "#BBBBBB",
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

types = [id2type[i] for i in fafb_ids if i in id2type]
type_cells = pd.Series(types).value_counts()
type2zone = {id2type[i]: id2zone[i] for i in fafb_ids if i in id2type}

# Top 100 types
top = type_cells.head(50)
colours = [ZONE_COLOURS.get(type2zone.get(t, ""), "#BBBBBB") for t in top.index]

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(range(len(top)), top.values, color=colours, edgecolor="white", linewidth=0.3, width=0.85)
ax.set_xticks(range(len(top)))
ax.set_xticklabels(top.index, rotation=70, ha="right", fontsize=5)
ax.set_ylabel("Neurons in circuit", fontsize=9)
ax.set_title("Top 50 cell types by neuron count", fontsize=10, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Legend
legend_zones = ["optic_lobe", "central_brain", "sensory", "visual_projection", "descending"]
handles = [Patch(facecolor=ZONE_COLOURS[z], label=ZONE_LABELS[z]) for z in legend_zones]
ax.legend(handles=handles, fontsize=7, loc="upper right", framealpha=0.9)

plt.tight_layout()
out_dir = ROOT / "figures"
out_dir.mkdir(parents=True, exist_ok=True)
fig.savefig(out_dir / "cells_per_type.pdf", bbox_inches="tight", dpi=300)
fig.savefig(out_dir / "cells_per_type.png", bbox_inches="tight", dpi=200)
print(f"Saved to {out_dir / 'cells_per_type.pdf'}")
