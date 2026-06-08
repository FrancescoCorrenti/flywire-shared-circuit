"""
Select representative types for the network graph in the report.
Method (all graph-derived, no ad-hoc scores):
  1. Inter-zone gateway ranking: per zone, top k types by total inter-zone
     synapse weight (budget: OL 6, CB 6, VP 8, SE 5, DN 6).
  2. Shortest-path relay (CB only): types on directed shortest paths
     between CB sources (connected to sensory gateways) and CB sinks
     (connected to descending gateways).
  3. Intra-zone feeders (OL only): top 5 types by synapse weight toward
     OL gateway types already selected.
Output: type_graphs/display_types.csv (type, zone)
"""
import pandas as pd
import networkx as nx
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- Load data ---
sub = pd.read_csv(ROOT / "submission_mega.csv")
nodes_fafb = pd.read_csv(ROOT / "type_graphs" / "nodes_FAFB.csv").set_index("id")
fafb_ids = set(sub["FAFB"].values)
id2type = nodes_fafb["type"].to_dict()
id2zone = nodes_fafb["zone"].to_dict()
type2zone = {id2type[i]: id2zone[i] for i in fafb_ids if i in id2type}
type_cells = pd.Series([id2type[i] for i in fafb_ids if i in id2type]).value_counts().to_dict()

edges_raw = pd.read_csv(ROOT / "data" / "fafb_783_edge_list.csv")
mask = edges_raw["source neuron id"].isin(fafb_ids) & edges_raw["target neuron id"].isin(fafb_ids)
induced = edges_raw[mask][["source neuron id", "target neuron id"]].values
type_edges = defaultdict(int)
for s, t in induced:
    ts, tt = id2type.get(s), id2type.get(t)
    if ts and tt and ts != tt:
        type_edges[(ts, tt)] += 1

# ===== STEP 1: inter-zone gateways =====
inter_w = defaultdict(int)
for (ts, tt), w in type_edges.items():
    zs, zt = type2zone.get(ts), type2zone.get(tt)
    if zs and zt and zs != zt:
        inter_w[ts] += w
        inter_w[tt] += w

BUDGETS = {"optic_lobe": 6, "central_brain": 6, "visual_projection": 8,
           "sensory": 5, "descending": 6}
selected = set()
for zone, b in BUDGETS.items():
    zt = [(t, inter_w[t]) for t in inter_w if type2zone.get(t) == zone]
    zt.sort(key=lambda x: -x[1])
    for t, _ in zt[:b]:
        selected.add(t)
print("Step 1 (inter-zone gateways): %d types" % len(selected))

# ===== STEP 2: CB shortest-path relay =====
cb_types = {t for t, z in type2zone.items() if z == "central_brain"}
G_cb = nx.DiGraph()
for (ts, tt), w in type_edges.items():
    if ts in cb_types and tt in cb_types:
        G_cb.add_edge(ts, tt, weight=w)

sensory_gw = {t for t in selected if type2zone.get(t) == "sensory"}
descending_gw = {t for t in selected if type2zone.get(t) == "descending"}

cb_sources = set()
for (ts, tt), w in type_edges.items():
    if ts in sensory_gw and tt in cb_types:
        cb_sources.add(tt)
    if tt in sensory_gw and ts in cb_types:
        cb_sources.add(ts)

cb_sinks = set()
for (ts, tt), w in type_edges.items():
    if ts in cb_types and tt in descending_gw:
        cb_sinks.add(ts)
    if tt in cb_types and ts in descending_gw:
        cb_sinks.add(ts)

relay = set()
for src in cb_sources & set(G_cb.nodes):
    for snk in cb_sinks & set(G_cb.nodes):
        try:
            path = nx.shortest_path(G_cb, src, snk)
            relay.update(path)
        except nx.NetworkXNoPath:
            pass
selected |= relay
print("Step 2 (CB relay): +%d types (%d total)" % (len(relay - selected), len(selected)))

# ===== STEP 3: OL intra-zone feeders =====
ol_types = {t for t, z in type2zone.items() if z == "optic_lobe"}
ol_gateways = selected & ol_types
ol_feeder_w = {}
for t in ol_types - selected:
    w = sum(type_edges.get((t, gw), 0) for gw in ol_gateways)
    if w > 0:
        ol_feeder_w[t] = w
top_feeders = sorted(ol_feeder_w.items(), key=lambda x: -x[1])[:5]
for t, _ in top_feeders:
    selected.add(t)
print("Step 3 (OL feeders): +%d types (%d total)" % (len(top_feeders), len(selected)))

# ===== Output =====
rows = []
for t in sorted(selected, key=lambda t: (type2zone.get(t, "zzz"), t)):
    rows.append({"type": t, "zone": type2zone[t]})
df = pd.DataFrame(rows)
out_path = ROOT / "type_graphs" / "display_types.csv"
df.to_csv(out_path, index=False)

tc = sum(type_cells.get(t, 0) for t in selected)
n = len(sub)
print("\nSelected %d types" % len(df))
print("Covering %d/%d neurons (%.1f%%)" % (tc, n, tc / n * 100))
print("Saved to %s" % out_path)
for zone in ["sensory", "optic_lobe", "visual_projection", "central_brain", "descending"]:
    tz = [r["type"] for r in rows if r["zone"] == zone]
    if tz:
        print("  %s: %s" % (zone, ", ".join(tz)))
