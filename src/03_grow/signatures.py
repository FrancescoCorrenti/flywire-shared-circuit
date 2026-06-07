"""
Same type-edge seed, many cell-level realizations + batch signature growth.

Usage:
  python signatures.py --template cand/lessCB.csv --seed-type Dm14 Tm2 --variants 200 --seconds 7200
"""
import os
import sys
import time
import pickle
import argparse
import random
from collections import defaultdict
from itertools import islice

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TG = os.path.join(BASE, "type_graphs")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grow_circuit import Circuit, DS, build_graphs


def external_signature(g, cell, cell2slot):
    parts = []
    for v in g.successors(cell):
        if v in cell2slot:
            parts.append((cell2slot[v], "o"))
    for u in g.predecessors(cell):
        if u in cell2slot:
            parts.append((cell2slot[u], "i"))
    return tuple(sorted(parts))


def batch_round(C, G, tset):
    added = 0
    for typ in tset:
        by_sig = {d: defaultdict(list) for d in DS}
        for d in DS:
            g = G[d]
            c2s = C.cell2slot[d]
            for c in g:
                if g.nodes[c]["type"] != typ or c in c2s:
                    continue
                sig = external_signature(g, c, c2s)
                if not sig:
                    continue
                by_sig[d][sig].append(c)
        for sig in set(by_sig["FAFB"]) & set(by_sig["BANC"]) & set(by_sig["MCNS"]):
            fa, fb, fm = by_sig["FAFB"][sig], by_sig["BANC"][sig], by_sig["MCNS"][sig]
            k = min(len(fa), len(fb), len(fm))
            ib = list(range(k))
            im = list(range(k))
            random.shuffle(ib)
            random.shuffle(im)
            for i in range(k):
                tr = {"FAFB": fa[i], "BANC": fb[ib[i]], "MCNS": fm[im[i]]}
                if C.try_add_triple(tr, typ, True):
                    added += 1
    return added


def edge_pairs_for_types(G, type_a, type_b, limit):
    out = {d: [] for d in DS}
    for d in DS:
        g = G[d]
        for u, v in g.edges():
            if g.nodes[u]["type"] == type_a and g.nodes[v]["type"] == type_b:
                out[d].append((u, v))
                if len(out[d]) >= limit:
                    break
    return out


def continue_circuit(C, G, tset, typ_of, deadline, max_stall=3):
    stall = 0
    while time.time() < deadline and stall < max_stall:
        n0 = C.nslot
        while batch_round(C, G, tset):
            if time.time() >= deadline:
                break
        if C.nslot > n0:
            stall = 0
            continue
        adj, types = C.frontier_candidates(typ_of)
        added = False
        for typ in types:
            fa = list(adj["FAFB"][typ])
            fb = list(adj["BANC"][typ])
            fm = list(adj["MCNS"][typ])
            random.shuffle(fa)
            random.shuffle(fb)
            random.shuffle(fm)
            for cf in fa[:60]:
                for cb in fb[:60]:
                    for cm in fm[:60]:
                        tr = {"FAFB": cf, "BANC": cb, "MCNS": cm}
                        if C.try_add_triple(tr, typ, True):
                            added = True
                            break
                    if added:
                        break
                if added:
                    break
        if added:
            stall = 0
        else:
            stall += 1
    return C


def grow_from_cells(G, tset, typ_of, cells_a, cells_b, type_a, type_b, deadline, max_stall=3):
    C = Circuit(G)
    if not C.try_add_triple(cells_a, type_a, False):
        return C
    if not C.try_add_triple(cells_b, type_b, True):
        return C
    return continue_circuit(C, G, tset, typ_of, deadline, max_stall)


def run(template_rel, type_a, type_b, variants, seconds, pair_sample=40):
    name = os.path.splitext(os.path.basename(template_rel))[0]
    tag = f"{type_a}_{type_b}".replace("/", "-")
    out_path = os.path.join(TG, f"_variant_{name}_{tag}.pkl")
    path = template_rel if os.path.isabs(template_rel) else os.path.join(TG, template_rel)
    _, tset, _, G = build_graphs(path)
    typ_of = {d: {c: G[d].nodes[c]["type"] for c in G[d]} for d in DS}

    pairs = edge_pairs_for_types(G, type_a, type_b, variants)
    print(
        f"[variants {name} {type_a}->{type_b}] pairs: "
        + ", ".join(f"{d}={len(pairs[d])}" for d in DS),
        flush=True,
    )
    if not all(pairs[d] for d in DS):
        print("missing pairs in some dataset", flush=True)
        return None

    t0 = time.time()
    deadline = t0 + seconds
    per = max(45, seconds / max(variants, 1))

    best = Circuit(G)
    if os.path.exists(out_path):
        try:
            prev = pickle.load(open(out_path, "rb"))
            best = Circuit(G)
            for s in sorted(prev["slot2cell"]["FAFB"]):
                tr = {d: prev["slot2cell"][d][s] for d in DS}
                typ = G["FAFB"].nodes[tr["FAFB"]]["type"]
                best.try_add_triple(tr, typ, touch_required=False)
            print(f"  resume best N={best.nslot} from {out_path}", flush=True)
        except Exception:
            best = Circuit(G)

    tried = 0
    fafb_list = pairs["FAFB"]
    random.shuffle(fafb_list)
    for i, (uf, vf) in enumerate(islice(fafb_list, variants)):
        if time.time() > deadline:
            break
        dl = min(deadline, time.time() + per)
        random.shuffle(pairs["BANC"])
        random.shuffle(pairs["MCNS"])
        for (ub, vb) in pairs["BANC"][:pair_sample]:
            for (um, vm) in pairs["MCNS"][:pair_sample]:
                if time.time() > dl:
                    break
                cells_a = {"FAFB": uf, "BANC": ub, "MCNS": um}
                cells_b = {"FAFB": vf, "BANC": vb, "MCNS": vm}
                C = grow_from_cells(G, tset, typ_of, cells_a, cells_b, type_a, type_b, dl)
                tried += 1
                if C.nslot > best.nslot:
                    best = C
                    print(
                        f"  variant {i}: N={C.nslot} edges={len(C.E['FAFB'])} (NEW BEST)",
                        flush=True,
                    )
                    pickle.dump(
                        {
                            "name": name,
                            "template": template_rel,
                            "slot2cell": best.slot2cell,
                            "E": best.E,
                            "N": best.nslot,
                            "seed_types": (type_a, type_b),
                        },
                        open(out_path, "wb"),
                    )
            if time.time() > dl:
                break

    print(f"[variants] tried {tried}. BEST N={best.nslot} -> {out_path}", flush=True)
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="cand/lessCB.csv")
    ap.add_argument("--seed-type", nargs=2, required=True)
    ap.add_argument("--variants", type=int, default=200)
    ap.add_argument("--seconds", type=int, default=600)
    ap.add_argument("--pair-sample", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    r