"""
06_visualize / type_graph.py
Aggregated cell-type graph (node = type, edge weight = synapses).
"""
import csv
import os
from collections import Counter, defaultdict

import networkx as nx

OTHER_PREFIX = "__other__|"

_DEFAULT_DISPLAY_TYPES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "type_graphs",
    "display_types.csv",
)


def build_type_graph(G, zone_attr="zone", type_attr="type"):
    """
    DiGraph over types present in the circuit.
    Node attributes: zone, n_neurons, degree (aggregated incident synapses).
    Edge attributes: weight (= cell->cell synapse count).
    """
    meta = {}
    for n in G.nodes:
        t = G.nodes[n][type_attr]
        z = G.nodes[n][zone_attr]
        if t not in meta:
            meta[t] = {"zone": z, "n_neurons": 0}
        meta[t]["n_neurons"] += 1

    TG = nx.DiGraph()
    for t, info in meta.items():
        TG.add_node(t, zone=info["zone"], n_neurons=info["n_neurons"])

    edge_w = Counter()
    for u, v in G.edges():
        edge_w[(G.nodes[u][type_attr], G.nodes[v][type_attr])] += 1
    for (tu, tv), w in edge_w.items():
        TG.add_edge(tu, tv, weight=w)

    for t in TG.nodes:
        deg = sum(d.get("weight", 1) for _, _, d in TG.in_edges(t, data=True))
        deg += sum(d.get("weight", 1) for _, _, d in TG.out_edges(t, data=True))
        TG.nodes[t]["degree"] = deg

    return TG


def is_other_type(node_id):
    return str(node_id).startswith(OTHER_PREFIX)


def other_type_id(zone):
    return OTHER_PREFIX + zone


def load_display_types(csv_path=None):
    """Types to display in the network graph (columns: type, zone)."""
    path = csv_path or _DEFAULT_DISPLAY_TYPES
    keep = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("type") or "").strip()
            if name:
                keep.add(name)
    if not keep:
        raise ValueError("No types found in %s" % path)
    return keep


def collapse_type_graph(
    TG,
    display_types=None,
    display_types_path=None,
    zone_attr="zone",
    zone_key=None,
    visible_zone=None,
):
    """
    Keeps the types listed in ``display_types.csv``; the rest goes into ``other``.
    """
    if zone_key is None:
        zone_key = lambda z: z  # noqa: E731
    if visible_zone is None:
        visible_zone = lambda z: True  # noqa: E731
    if display_types is None:
        display_types = load_display_types(display_types_path)

    by_zone = defaultdict(list)
    for t in TG.nodes:
        z = zone_key(TG.nodes[t].get(zone_attr))
        if not visible_zone(z):
            continue
        by_zone[z].append(t)

    merge_map = {}
    for zone, types in by_zone.items():
        keep = {t for t in types if t in display_types}
        for t in keep:
            merge_map[t] = t
        tail = [t for t in types if t not in keep]
        if tail:
            oid = other_type_id(zone)
            for t in tail:
                merge_map[t] = oid

    CTG = nx.DiGraph()
    reps = set(merge_map.values())
    for rep in reps:
        members = [t for t, r in merge_map.items() if r == rep]
        if is_other_type(rep):
            zone = rep.split("|", 1)[1]
            CTG.add_node(
                rep,
                zone=zone,
                n_neurons=sum(TG.nodes[t].get("n_neurons", 0) for t in members),
                n_types=len(members),
                is_other=True,
                label="other",
                member_types=members,
            )
        else:
            CTG.add_node(
                rep,
                zone=zone_key(TG.nodes[rep].get(zone_attr)),
                n_neurons=TG.nodes[rep].get("n_neurons", 0),
                n_types=1,
                is_other=False,
                label=rep,
                member_types=[rep],
            )

    edge_w = Counter()
    for u, v, d in TG.edges(data=True):
        if u not in merge_map or v not in merge_map:
            continue
        ru, rv = merge_map[u], merge_map[v]
        if ru == rv:
            continue
        edge_w[(ru, rv)] += d.get("weight", 1)
    for (u, v), w in edge_w.items():
        CTG.add_edge(u, v, weight=w)

    for t in CTG.nodes:
        deg = sum(d.get("weight", 1) for _, _, d in CTG.in_edges(t, data=True))
        deg += sum(d.get("weight", 1) for _, _, d in CTG.out_edges(t, data=True))
        CTG.nodes[t]["degree"] = deg

    return CTG


def type_graph_summary(TG):
    zones = {TG.nodes[t]["zone"] for t in TG.nodes}
    return {
        "n_types": TG.number_of_nodes(),
        "n_edges": TG.number_of_edges(),
        "n_zones": len(zones),
    }
