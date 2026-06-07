"""
06_visualize / load_graph.py
Carica un CSV deliverable e costruisce il sottografo indotto con annotazioni.
"""
import csv
import os
import sys

import networkx as nx
import pandas as pd

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_BASE, "src", "03_grow"))
from cell_graph import BASE, DATA, EDGE, TG  # noqa: E402

DATASETS = ("FAFB", "BANC", "MCNS")


def load_submission_ids(csv_path, dataset="FAFB"):
    """Legge la colonna del dataset dal CSV deliverable (3 colonne × N righe)."""
    if dataset not in DATASETS:
        raise ValueError("dataset must be one of %s" % (DATASETS,))

    df = pd.read_csv(csv_path, dtype=str)
    if dataset not in df.columns:
        raise ValueError("column %r not in %s" % (dataset, csv_path))

    ids = df[dataset].dropna().astype(str).str.strip()
    ids = ids[ids != ""]
    return list(ids.unique())


def load_node_annotations(dataset):
    """Neurone → zona, tipo, side da nodes_{dataset}.csv."""
    path = os.path.join(TG, "nodes_%s.csv" % dataset)
    nodes = pd.read_csv(path, dtype={"id": str})
    nodes["id"] = nodes["id"].str.strip()
    zone = dict(zip(nodes["id"], nodes["zone"].fillna("unknown")))
    typ = dict(zip(nodes["id"], nodes["type"].fillna("unknown")))
    side = dict(zip(nodes["id"], nodes["side"].fillna("?")))
    return zone, typ, side


def load_induced_edges(dataset, neuron_ids):
    """Archi reali tra neuroni selezionati (sottografo indotto)."""
    neurons = set(str(n) for n in neuron_ids)
    path = os.path.join(DATA, EDGE[dataset])

    edges = []
    with open(path, newline="") as fh:
        rd = csv.reader(fh)
        next(rd)  # header
        for row in rd:
            if len(row) < 2:
                continue
            src, tgt = row[0].strip(), row[1].strip()
            if src in neurons and tgt in neurons:
                edges.append((src, tgt))
    return edges


def build_circuit_graph(csv_path, dataset="FAFB"):
    """
    Grafo diretto del circuito nel dataset scelto.
    Attributi nodo: zone, type, side. Archi senza peso (peso=1).
    """
    neuron_ids = load_submission_ids(csv_path, dataset)
    zone_map, type_map, side_map = load_node_annotations(dataset)
    edges = load_induced_edges(dataset, neuron_ids)

    G = nx.DiGraph()
    for nid in neuron_ids:
        G.add_node(
            nid,
            zone=zone_map.get(nid, "unknown"),
            type=type_map.get(nid, "unknown"),
            side=side_map.get(nid, "?"),
        )
    G.add_edges_from(edges)
    return G


def graph_summary(G):
    zones = [G.nodes[n]["zone"] for n in G.nodes]
    types = [G.nodes[n]["type"] for n in G.nodes]
    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "n_zones": len(set(zones)),
        "n_types": len(set(types)),
    }
