"""
Type graph with multiplicity. Two SEPARATE tables:
- type_graph_inter.csv : edges A->B (A!=B) conserved across 3 + multiplicity per dataset
- type_graph_intra.csv : edges A->A (same type) conserved across 3 + internal density
Multiplicity counts participating CELLS (not synapses). Zone labels on both.
Edges from provided edge lists.
"""
import os as _os, sys as _sys
_os.chdir(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))
_sys.path.insert(0, _os.path.dirname(__file__))
import pandas as pd
import pickle
from collections import defaultdict

OUT = "type_graphs"
EDGE = {
    "FAFB": "data/fafb_783_edge_list.csv",
    "BANC": "data/banc_626_edge_list.csv",
    "MCNS": "data/mcns_0.9_edge_list.csv",
}

def load_maps(name):
    n = pd.read_csv(f"{OUT}/nodes_{name}.csv", dtype=str).dropna(subset=["type"])
    return dict(zip(n.id, n.type)), dict(zip(n.id, n.zone))

def scan(name, tmap):
    """For each type-edge (ts,tt): returns
       set of source cells, set of target cells, number of cell-pairs."""
    src = defaultdict(set)   # (ts,tt) -> {source cells}
    tgt = defaultdict(set)   # (ts,tt) -> {target cells}
    pairs = defaultdict(int) # (ts,tt) -> number of cell-pairs
    with open(EDGE[name]) as f:
        next(f)
        for line in f:
            s, t = line.rstrip().split(",")
            ts = tmap.get(s); tt = tmap.get(t)
            if ts is None or tt is None:
                continue
            k = (ts, tt)
            src[k].add(s); tgt[k].add(t); pairs[k] += 1
    return src, tgt, pairs

def main():
    tmaps, zmaps, data = {}, {}, {}
    for name in EDGE:
        tmap, zmap = load_maps(name)
        tmaps[name] = tmap; zmaps[name] = zmap
        data[name] = scan(name, tmap)
        print(f"{name}: distinct type-edges {len(data[name][2]):,}")

    # edges conserved across all 3 (including A->A this time)
    keys = set(data["FAFB"][2]) & set(data["BANC"][2]) & set(data["MCNS"][2])
    print(f"\nType-edges conserved across 3 (inter+intra): {len(keys):,}")

    # zone per type
    znode = {}
    for nm in EDGE:
        idx = {tmaps[nm][i]: zmaps[nm][i] for i in tmaps[nm] if i in zmaps[nm]}
        for t, z in idx.items():
            if t not in znode and pd.notna(z):
                znode[t] = z

    inter_rows, intra_rows = [], []
    for (a, b) in keys:
        rec = {"source_type": a, "target_type": b,
               "source_zone": znode.get(a), "target_zone": znode.get(b)}
        for nm in EDGE:
            src, tgt, pairs = data[nm]
            rec[f"{nm}_nsrc"] = len(src[(a, b)])
            rec[f"{nm}_ntgt"] = len(tgt[(a, b)])
            rec[f"{nm}_npairs"] = pairs[(a, b)]
        # minimum cell multiplicity (bound on how many participate in all 3)
        rec["min_nsrc"] = min(rec[f"{nm}_nsrc"] for nm in EDGE)
        rec["min_ntgt"] = min(rec[f"{nm}_ntgt"] for nm in EDGE)
        rec["min_npairs"] = min(rec[f"{nm}_npairs"] for nm in EDGE)
        if a == b:
            intra_rows.append(rec)
        else:
            inter_rows.append(rec)

    inter = pd.DataFrame(inter_rows).sort_values("min_npairs", ascending=False)
    intra = pd.DataFrame(intra_rows).sort_values("min_npairs", ascending=False)
    inter.to_csv(f"{OUT}/type_graph_inter.csv", index=False)
    intra.to_csv(f"{OUT}/type_graph_intra.csv", index=False)
    pickle.dump({"keys": keys, "znode": znode}, open(f"{OUT}/_mult.pkl", "wb"))

    print(f"\nINTER-type (A!=B): {len(inter):,} edges")
    print(f"INTRA-type (A==A): {len(intra):,} edges")
    print(f"\n--- top 12 INTER by min cell-pairs ---")
    print(inter[["source_type","target_type","source_zone","target_zone","min_nsrc","min_ntgt","min_npairs"]].head(12).to_string(index=False))
    print(f"\n--- top 12 INTRA by min cell-pairs ---")
    print(intra[["source_type","source_zone","min_nsrc","min_ntgt","min_npairs"]].head(12).to_string(index=False))

if __name__ == "__main__":
    main()
