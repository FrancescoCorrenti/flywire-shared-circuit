"""
Conserved directed type->type graph.
For each dataset: maps neuron (from provided edge list) -> type, projects
cell->cell edges into directed type->type edges. Retains ONLY edges
present in all 3 datasets. Reciprocal A->B and B->A are distinct edges.
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

def load_type_map(name):
    n = pd.read_csv(f"{OUT}/nodes_{name}.csv", dtype=str)
    n = n.dropna(subset=["type"])
    return dict(zip(n.id, n.type)), dict(zip(n.id, n.zone))

def project(name, tmap):
    """Project edge list -> directed type->type edges. Returns set of (tsrc, ttgt)."""
    edges = set()
    n_lines = n_kept = 0
    with open(EDGE[name]) as f:
        next(f)
        for line in f:
            n_lines += 1
            s, t = line.rstrip().split(",")
            ts = tmap.get(s); tt = tmap.get(t)
            if ts is None or tt is None:
                continue
            if ts == tt:
                continue  # type-level self-loop: discarded (uninformative)
            edges.add((ts, tt))
            n_kept += 1
    return edges, n_lines, n_kept

def main():
    tmaps = {}
    zmaps = {}
    proj = {}
    for name in EDGE:
        tmap, zmap = load_type_map(name)
        tmaps[name] = tmap; zmaps[name] = zmap
        e, nl, nk = project(name, tmap)
        proj[name] = e
        print(f"{name}: edge list {nl:,} edges | projected to type: {nk:,} cell edges | distinct type->type edges: {len(e):,}")

    # conserved edges = present in all 3 (directed)
    conserved = proj["FAFB"] & proj["BANC"] & proj["MCNS"]
    print(f"\nDirected type->type edges conserved across 3: {len(conserved):,}")

    # nodes involved
    nodes = set()
    for a, b in conserved:
        nodes.add(a); nodes.add(b)
    print(f"Types (nodes) in skeleton: {len(nodes):,}")

    # zone per node (from FAFB, fallback to others)
    znode = {}
    for nm in ["FAFB", "BANC", "MCNS"]:
        z = zmaps[nm]
        idx = {tmaps[nm][i]: z[i] for i in tmaps[nm] if i in z}
        for t in nodes:
            if t not in znode and t in idx and pd.notna(idx[t]):
                znode[t] = idx[t]

    df = pd.DataFrame(sorted(conserved), columns=["source_type", "target_type"])
    df["source_zone"] = df.source_type.map(znode)
    df["target_zone"] = df.target_type.map(znode)
    df.to_csv(f"{OUT}/type_graph_conserved.csv", index=False)
    pickle.dump({"conserved": conserved, "nodes": nodes, "znode": znode,
                 "proj": proj}, open(f"{OUT}/_type_graph.pkl", "wb"))
    print(f"\nSaved {OUT}/type_graph_conserved.csv")

    # inter-zone vs intra-zone edge statistics
    df["cross"] = df.source_zone != df.target_zone
    print("\nConserved edges intra-zone:", (~df.cross).sum(), "| inter-zone:", df.cross.sum())

if __name__ == "__main__":
    main()
