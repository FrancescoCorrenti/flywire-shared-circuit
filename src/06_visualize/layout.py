"""
06_visualize / layout.py
Layout schematico: zone disposte anatomicamente, nodi posizionati con spring
locale dove possibile (rispetta connettività intra-cluster).
"""
import math
from collections import Counter, defaultdict

import networkx as nx
import numpy as np

# Zone rade raggruppate anche nello spazio (stesso bucket di render._ZONE_AS_OTHER).
_ZONE_AS_OTHER = frozenset({"motor", "ascending", "visual_centrifugal"})
_LAYOUT_OTHER = "_other"


def _layout_zone(zone):
    z = zone or "unknown"
    return _LAYOUT_OTHER if z in _ZONE_AS_OTHER else z


_ZONE_TEMPLATE = {
    "optic_lobe": np.array([-7.5, 0.3]),
    "central_brain": np.array([-0.8, -0.2]),
    "sensory": np.array([1.6, 5.0]),
    "visual_projection": np.array([3.8, -5.1]),
    "descending": np.array([5.4, 2.2]),
    _LAYOUT_OTHER: np.array([-7.0, 4.2]),
    "sensory_ascending": np.array([2.0, 5.5]),
    "unknown": np.array([0.0, 6.5]),
}

_ZONE_ASPECT = {
    "optic_lobe": (1.55, 0.82),
    "central_brain": (1.05, 1.05),
    "sensory": (1.25, 0.75),
    "visual_projection": (0.85, 1.15),
    "descending": (1.35, 0.65),
    _LAYOUT_OTHER: (1.0, 1.0),
    "sensory_ascending": (1.0, 1.0),
    "unknown": (1.0, 1.0),
}


def _zone_spread(n_nodes, base=0.32, scale=0.021):
    return base + scale * math.sqrt(max(n_nodes, 1))


def _zone_meta_graph(G, zone_attr="zone", zone_key=_layout_zone):
    zones = nx.get_node_attributes(G, zone_attr)
    ZG = nx.Graph()
    for u, v in G.edges():
        zu, zv = zone_key(zones.get(u)), zone_key(zones.get(v))
        if zu and zv and zu != zv:
            if ZG.has_edge(zu, zv):
                ZG[zu][zv]["weight"] += 1
            else:
                ZG.add_edge(zu, zv, weight=1)
    return ZG


def _refine_zone_centroids(ZG, zone_counts, seed=42):
    pos = {z: _ZONE_TEMPLATE.get(z, np.array([0.0, 0.0])).copy() for z in zone_counts}
    if ZG.number_of_edges() == 0:
        return pos

    for u, v, d in ZG.edges(data=True):
        d["weight"] = math.log1p(d.get("weight", 1))

    refined = nx.spring_layout(
        ZG, pos=pos, weight="weight", k=1.6, iterations=50, seed=seed
    )
    blend = 0.78
    return {
        z: blend * _ZONE_TEMPLATE.get(z, np.array([0.0, 0.0]))
        + (1.0 - blend) * np.array(refined.get(z, _ZONE_TEMPLATE.get(z, np.array([0.0, 0.0]))))
        for z in zone_counts
    }


def _resolve_zone_overlaps(centroids, zone_counts, gap=0.65, iterations=120):
    zones = list(centroids.keys())
    radii = {z: _zone_spread(zone_counts[z]) for z in zones}
    pos = {z: centroids[z].copy() for z in zones}

    for _ in range(iterations):
        moved = False
        for i, z1 in enumerate(zones):
            for z2 in zones[i + 1 :]:
                delta = pos[z2] - pos[z1]
                dist = np.linalg.norm(delta)
                min_dist = radii[z1] + radii[z2] + gap
                if dist < min_dist and dist > 1e-6:
                    push = (min_dist - dist) * 0.45 * delta / dist
                    pos[z1] -= push
                    pos[z2] += push
                    moved = True
        if not moved:
            break
    return pos


def _scale_to_ellipse(pos, spread, aspect=(1.0, 1.0)):
    if not pos:
        return pos
    arr = np.array(list(pos.values()))
    cx, cy = arr.mean(axis=0)
    centered = {n: np.array(p) - [cx, cy] for n, p in pos.items()}
    scaled = {
        n: np.array([p[0] / max(aspect[0], 1e-6), p[1] / max(aspect[1], 1e-6)])
        for n, p in centered.items()
    }
    max_r = max(np.linalg.norm(p) for p in scaled.values()) or 1.0
    s = spread / max_r
    return {
        n: np.array([p[0] * aspect[0] * s, p[1] * aspect[1] * s])
        for n, p in scaled.items()
    }


def _golden_spiral(n, spread, aspect=(1.0, 1.0)):
    golden = math.pi * (3.0 - math.sqrt(5.0))
    out = {}
    for i in range(n):
        t = (i + 0.5) / n
        r = spread * math.sqrt(t)
        theta = i * golden
        out[i] = np.array(
            [aspect[0] * r * math.cos(theta), aspect[1] * r * math.sin(theta)]
        )
    return out


def _place_zone_nodes(sub, spread, aspect, rng, seed_offset=0):
    """Spring se ci sono archi intra-zona; altrimenti spirale/griglia."""
    nodes = list(sub.nodes)
    n = len(nodes)
    if n == 1:
        return {nodes[0]: np.array([0.0, 0.0])}

    m_edges = sub.number_of_edges()

    # Spring locale: rispetta topologia intra-cluster.
    if m_edges > 0:
        k = spread / max(math.sqrt(n), 1.0)
        iters = int(min(60, max(20, 4000 / n)))
        local = nx.spring_layout(
            sub,
            k=k,
            iterations=iters,
            seed=seed_offset,
        )
        return _scale_to_ellipse(local, spread, aspect)

    if n <= 12:
        local = {}
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / n
            local[node] = np.array(
                [aspect[0] * spread * 0.55 * math.cos(angle),
                 aspect[1] * spread * 0.55 * math.sin(angle)]
            )
        return local

    spiral = _golden_spiral(n, spread, aspect)
    return {nodes[i]: spiral[i] for i in range(n)}


def zone_force_layout(
    G, zone_attr="zone", seed=42, spread_scale=1.0, side_split=True, side_attr="side"
):
    rng = np.random.default_rng(seed)
    zones = nx.get_node_attributes(G, zone_attr)
    layout_zones = {n: _layout_zone(zones.get(n)) for n in G.nodes}
    zone_counts = Counter(layout_zones.values())

    ZG = _zone_meta_graph(G, zone_attr, zone_key=_layout_zone)
    centroids = _refine_zone_centroids(ZG, zone_counts, seed=seed)
    centroids = _resolve_zone_overlaps(centroids, zone_counts)

    pos = {}
    for zi, (zone, count) in enumerate(zone_counts.items()):
        anchor = centroids[zone]
        spread = _zone_spread(count) * spread_scale
        aspect = _ZONE_ASPECT.get(zone, (1.0, 1.0))
        nodes_z = [n for n in G.nodes if layout_zones[n] == zone]
        sub = G.subgraph(nodes_z)

        local = _place_zone_nodes(
            sub, spread, aspect, rng, seed_offset=int(seed) + zi * 17
        )
        if zone not in ("optic_lobe", "central_brain") and len(nodes_z) > 3:
            angle = rng.uniform(-0.25, 0.25)
            c, s = math.cos(angle), math.sin(angle)
            rot = np.array([[c, -s], [s, c]])
            local = {n: rot @ p for n, p in local.items()}

        for n, p in local.items():
            pos[n] = anchor + p

    if side_split:
        pos = apply_side_split(pos, G, zone_attr=zone_attr, side_attr=side_attr)
    return {n: (float(p[0]), float(p[1])) for n, p in pos.items()}


def apply_side_split(pos, G, zone_attr="zone", side_attr="side", scale=0.34):
    """Within ogni cluster di layout, sposta L a sinistra e R a destra."""
    zones = nx.get_node_attributes(G, zone_attr)
    sides = nx.get_node_attributes(G, side_attr)
    by_zone = defaultdict(list)
    for n in pos:
        by_zone[_layout_zone(zones.get(n))].append(n)

    out = dict(pos)
    for nodes in by_zone.values():
        if len(nodes) <= 1:
            continue
        pts = np.array([out[n] for n in nodes])
        span = max(float(np.ptp(pts[:, 0])), float(np.ptp(pts[:, 1])), 0.25)
        shift = scale * span * 0.45
        for n in nodes:
            side = sides.get(n, "?")
            if side == "L":
                x, y = out[n]
                out[n] = (x - shift, y)
            elif side == "R":
                x, y = out[n]
                out[n] = (x + shift, y)
    return out


def zone_centroids(pos, zones_map=None):
    by_zone = defaultdict(list)
    if zones_map is None:
        zones_map = {}
    for n, p in pos.items():
        by_zone[zones_map.get(n, "unknown")].append(np.array(p))
    return {z: np.mean(pts, axis=0) for z, pts in by_zone.items()}
