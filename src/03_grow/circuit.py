"""
Cell-level circuit growth from seed -> large CONNECTED isomorphic subgraph.

Builds a cell mapping (common slots across FAFB/BANC/MCNS) by GROWING from a seed,
accepting each new triplet ONLY if it preserves:
  (1) isomorphism  -> induced edges in slot-space are identical across all 3 datasets
  (2) connectivity -> the new triplet touches the existing circuit in ALL 3 datasets

The result is by construction a single connected component, isomorphic across 3.

Algorithm (greedy + multi-restart):
  - seed = a strong type-edge (A->B) in all 3; pick one cell-pair per dataset
    realizing that edge -> 2 initial slots, already connected and isomorphic.
  - frontier = candidate triplets (same type in all 3) adjacent to the circuit.
    A candidate is a choice of (cf, cb, cm) cells of the same type, each adjacent
    (in/out) to at least one cell already inserted in the SAME slot role.
  - accept if, once added, the set of induced edges remains IDENTICAL in all 3
    (slot-space) -> isomorphism preserved. Connectivity is guaranteed by adjacency.
  - repeat until frontier is empty; multi-restart on different seeds, keep the
    largest connected circuit.

Usage:
  python circuit.py --template cand/best305.csv --seconds 3600 --restarts 200
"""
import os, sys, time, pickle, argparse, random
from collections import defaultdict
import networkx as nx

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TG = os.path.join(BASE, "type_graphs")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cell_graph import load_template_type_edges, build_cell_graph

DS = ["FAFB", "BANC", "MCNS"]


def build_graphs(template_rel):
    tpl, tset, te = load_template_type_edges(template_rel)
    G = {d: build_cell_graph(d, tset, te, intra_ok=True) for d in DS}
    return tpl, tset, te, G


def strong_type_edges(G):
    """Type-edges present in all 3, sorted by min cell-edge count (strongest seeds first)."""
    cnt = {d: defaultdict(int) for d in DS}
    for d in DS:
        g = G[d]
        for u, v in g.edges():
            cnt[d][(g.nodes[u]["type"], g.nodes[v]["type"])] += 1
    pairs = set(cnt["FAFB"]) & set(cnt["BANC"]) & set(cnt["MCNS"])
    out = [(p, min(cnt[d][p] for d in DS)) for p in pairs]
    out.sort(key=lambda r: -r[1])
    return [p for p, _ in out]


class Circuit:
    """Maps common slot -> (cell per dataset); maintains induced edges per dataset."""
    def __init__(self, G):
        self.G = G
        self.cell2slot = {d: {} for d in DS}   # cella -> slot
        self.slot2cell = {d: {} for d in DS}   # slot -> cella
        self.slot_type = {}                    # slot -> tipo
        self.E = {d: set() for d in DS}         # archi indotti (in spazio-slot)
        self.nslot = 0

    def _edges_if_added(self, d, cell, slot):
        """New edges (slot-space) introduced by adding `cell` as `slot` in dataset d."""
        g = self.G[d]; c2s = self.cell2slot[d]; new = set()
        for v in g.successors(cell):
            if v in c2s: new.add((slot, c2s[v]))
        for u in g.predecessors(cell):
            if u in c2s: new.add((c2s[u], slot))
        # self loop cell->cell
        if g.has_edge(cell, cell): new.add((slot, slot))
        return new

    def try_add_triple(self, cells, typ, touch_required):
        """
        Try to add a triplet {d: cell} as a new slot.
        Returns True if isomorphism is maintained (new edges identical across 3) and,
        if touch_required, connectivity (touches the circuit in all 3).
        """
        slot = self.nslot
        newE = {}
        for d in DS:
            if cells[d] in self.cell2slot[d]:
                return False  # cell already used
            newE[d] = self._edges_if_added(d, cells[d], slot)
        if touch_required and self.nslot > 0:
            if any(len(newE[d]) == 0 for d in DS):
                return False  # not connected in some dataset
        # isomorphism: new edges must be identical across all 3
        if not (newE["FAFB"] == newE["BANC"] == newE["MCNS"]):
            return False
        # commit
        for d in DS:
            self.cell2slot[d][cells[d]] = slot
            self.slot2cell[d][slot] = cells[d]
            self.E[d] |= newE[d]
        self.slot_type[slot] = typ
        self.nslot += 1
        return True

    def frontier_candidates(self, typ_of):
        """
        Generate candidate triplets (same type in all 3) adjacent to the circuit.
        For each dataset, cells adjacent to inserted cells; intersect by type.
        """
        adj = {d: defaultdict(set) for d in DS}   # type -> candidate cells
        for d in DS:
            g = self.G[d]
            for cell in self.cell2slot[d]:
                for nb in list(g.successors(cell)) + list(g.predecessors(cell)):
                    if nb not in self.cell2slot[d]:
                        adj[d][g.nodes[nb]["type"]].add(nb)
        types = set(adj["FAFB"]) & set(adj["BANC"]) & set(adj["MCNS"])
        return adj, types


def grow_from_seed(G, type_edges_sorted, seed_pair, typ_of, deadline):
    A, B = seed_pair
    C = Circuit(G)
    # find a cell-pair (src->tgt) per dataset that realizes A->B
    seed_cells = {}
    for d in DS:
        g = G[d]; found = None
        for u, v in g.edges():
            if g.nodes[u]["type"] == A and g.nodes[v]["type"] == B:
                found = (u, v); break
        if not found:
            return C
        seed_cells[d] = found
    # insert src (slot0) then tgt (slot1)
    if not C.try_add_triple({d: seed_cells[d][0] for d in DS}, A, False):
        return C
    if not C.try_add_triple({d: seed_cells[d][1] for d in DS}, B, True):
        return C

    # growth
    while time.time() < deadline:
        adj, types = C.frontier_candidates(typ_of)
        added = False
        for typ in types:
            # try to match one cell per dataset of this type (greedy: first viable)
            fa = list(adj["FAFB"][typ]); fb = list(adj["BANC"][typ]); fm = list(adj["MCNS"][typ])
            random.shuffle(fa); random.shuffle(fb); random.shuffle(fm)
            done = False
            for cf in fa:
                for cb in fb:
                    for cm in fm:
                        if C.try_add_triple({"FAFB": cf, "BANC": cb, "MCNS": cm}, typ, True):
                            added = True; done = True; break
                    if done: break
                if done: break
        if not added:
            break
    return C


def run(template_rel, seconds, restarts):
    name = os.path.splitext(os.path.basename(template_rel))[0]
    best_path = os.path.join(TG, f"_grow_{name}.pkl")
    tpl, tset, te, G = build_graphs(template_rel)
    typ_of = {d: {c: G[d].nodes[c]["type"] for c in G[d]} for d in DS}
    seeds = strong_type_edges(G)
    print(f"[{name}] {sum(g.number_of_nodes() for g in G.values())} celle tot, "
          f"{len(seeds)} archi-tipo seed")

    best = None
    t0 = time.time(); deadline_all = t0 + seconds
    tried = 0
    for seed in seeds[:restarts]:
        if time.time() > deadline_all: break
        per_seed = min(deadline_all, time.time() + 30)  # cap per seed
        C = grow_from_seed(G, seeds, seed, typ_of, per_seed)
        tried += 1
        if best is None or C.nslot > best.nslot:
            best = C
            print(f"  seed {seed[0]}->{seed[1]}: N={C.nslot} archi={len(C.E['FAFB'])} "
                  f"(NUOVO BEST)")
            pickle.dump({"name": name, "template": template_rel,
                         "slot2cell": best.slot2cell, "E": best.E,
                         "N": best.nslot}, open(best_path, "wb"))
    print(f"[{name}] provati {tried} seed. BEST N={best.nslot} "
          f"archi={len(best.E['FAFB'])} -> {best_path}")
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--seconds", type=int, default=3600)
    ap.add_argument("--restarts", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    random.seed(a.seed)
    run(a.template, a.seconds, a.restarts)
