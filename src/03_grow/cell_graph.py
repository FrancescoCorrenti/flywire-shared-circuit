"""
Build the cell-level graph for each dataset from the type template.
"""
import pandas as pd, networkx as nx, pickle, os
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(BASE, "data")
TG   = os.path.join(BASE, "type_graphs")

EDGE = {"FAFB": "fafb_783_edge_list.csv",
        "BANC": "banc_626_edge_list.csv",
        "MCNS": "mcns_0.9_edge_list.csv"}

def load_template_type_edges(template_csv="template_best.csv"):
    """Directed type->type edges from the template (subset of type_graph_inter)."""
    tpl = pd.read_csv(template_csv if os.path.isabs(template_csv)
                      else os.path.join(TG, template_csv))
    tset = set(tpl.type)
    inter = pd.read_csv(os.path.join(TG, "type_graph_inter.csv"))
    e = inter[inter.source_type.isin(tset) & inter.target_type.isin(tset)]
    type_edges = set(zip(e.source_type, e.target_type))
    return tpl, tset, type_edges

def build_cell_graph(ds, tset, type_edges, intra_ok):
    nodes = pd.read_csv(os.path.join(TG, f"nodes_{ds}.csv"))
    nodes = nodes[nodes.type.isin(tset)]
    cell2type = dict(zip(nodes.id.astype("int64"), nodes.type))
    cell2zone = dict(zip(nodes.id.astype("int64"), nodes.zone))
    valid = set(cell2type)

    el = pd.read_csv(os.path.join(DATA, EDGE[ds]))
    el.columns = ["src", "tgt"]
    el = el[el.src.isin(valid) & el.tgt.isin(valid)]

    G = nx.DiGraph()
    for c in valid:
        G.add_node(c, type=cell2type[c], zone=cell2zone[c])
    for s, t in zip(el.src.values, el.tgt.values):
        G.add_edge(int(s), int(t))
    return G
