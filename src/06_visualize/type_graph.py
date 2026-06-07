"""
06_visualize / type_graph.py
Grafo aggregato per tipo di cellula (nodo = tipo, peso arco = sinapsi).
"""
from collections import Counter

import networkx as nx


def build_type_graph(G, zone_attr="zone", type_attr="type"):
    """
    DiGraph sui tipi presenti nel circuito.
    Attributi nodo: zone, n_neurons, degree (sinapsi incidenti aggregate).
    Attributi arco: weight (= conteggio sinapsi cella→cella).
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


def type_graph_summary(TG):
    zones = {TG.nodes[t]["zone"] for t in TG.nodes}
    return {
        "n_types": TG.number_of_nodes(),
        "n_edges": TG.number_of_edges(),
        "n_zones": len(zones),
    }
