"""
Build unified neuron table: neuron -> zone, type, side for FAFB, BANC, MCNS.
- zone = super_class normalized via ZONE_MAP (only zones present in all 3)
- type = primary_type (FAFB) / cell_type (BANC) / flywireType|type (MCNS)
- side = side (FAFB/BANC) / somaSide (MCNS), normalized to L/R/M
Annotations are used ONLY to label neurons; edges come from edge lists (elsewhere).
"""
import os as _os, sys as _sys
_os.chdir(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))
_sys.path.insert(0, _os.path.dirname(__file__))
import pandas as pd
import os

OUT = "type_graphs"
os.makedirs(OUT, exist_ok=True)

ZONE_MAP = {
    # FAFB
    "optic": "optic_lobe",
    "central": "central_brain",
    "sensory": "sensory",
    "visual_projection": "visual_projection",
    "ascending": "ascending",
    "descending": "descending",
    "visual_centrifugal": "visual_centrifugal",
    "sensory_ascending": "sensory_ascending",
    # BANC
    "optic_lobe_intrinsic": "optic_lobe",
    "central_brain_intrinsic": "central_brain",
    # MCNS
    "ol_intrinsic": "optic_lobe",
    "cb_intrinsic": "central_brain",
    "cb_sensory": "sensory",
    "ol_sensory": "sensory",
    "descending_neuron": "descending",
    "ascending_neuron": "ascending",
    # Motor / endocrine
    "motor": "motor",
    "cb_motor": "motor",
    "vnc_motor": "motor",
    "endocrine": "endocrine",
    "ENS": "endocrine",
    "cb_efferent": "motor",
    "vnc_efferent": "motor",
    "efferent_ascending": "motor",
    "efferent_descending": "motor",
}

def norm_side(s):
    if pd.isna(s):
        return None
    s = str(s).lower()
    if s in ("left", "l"):
        return "L"
    if s in ("right", "r"):
        return "R"
    if s in ("center", "midline", "m"):
        return "M"
    return None

def build_fafb():
    cl = pd.read_csv("data/FAFB/classification.csv.gz")
    ct = pd.read_csv("data/FAFB/consolidated_cell_types.csv.gz")
    df = cl.merge(ct[["root_id", "primary_type"]], on="root_id", how="left")
    out = pd.DataFrame({
        "id": df.root_id.astype(str),
        "zone": df.super_class.map(ZONE_MAP),
        "type": df.primary_type,
        "side": df.side.map(norm_side),
    })
    return out

def build_banc():
    df = pd.read_csv("data/BANC/codex_annotations_flat_table.tab", sep="\t", low_memory=False)
    out = pd.DataFrame({
        "id": df.pt_root_id.astype(str),
        "zone": df.super_class.map(ZONE_MAP),
        "type": df.cell_type,
        "side": df.side.map(norm_side),
    })
    return out

def build_mcns():
    df = pd.read_feather("data/MCNS/body-annotations-male-cns-v0.9-minconf-0.5.feather")
    typ = df.flywireType.fillna(df["type"])
    out = pd.DataFrame({
        "id": df.bodyId.astype(str),
        "zone": df.superclass.map(ZONE_MAP),
        "type": typ,
        "side": df.somaSide.map(norm_side),
    })
    return out

def main():
    tables = {"FAFB": build_fafb(), "BANC": build_banc(), "MCNS": build_mcns()}
    for name, t in tables.items():
        t["dataset"] = name
        valid = t.dropna(subset=["zone", "type"])
        print(f"=== {name} ===")
        print(f"  total annotated: {len(t)} | with zone+type: {len(valid)}")
        print("  neurons per zone:")
        print(valid.zone.value_counts().to_string())
        t.to_csv(f"{OUT}/nodes_{name}.csv", index=False)
    zsets = {n: set(t.dropna(subset=["zone","type"]).zone.unique()) for n, t in tables.items()}
    common = set.intersection(*zsets.values())
    print("\n=== ZONES PRESENT IN ALL 3 ===")
    print(sorted(common))

if __name__ == "__main__":
    main()
