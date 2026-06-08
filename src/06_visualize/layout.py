"""
06_visualize / layout.py
Schematic layout: zones arranged anatomically, nodes positioned with local spring
where possible (respects intra-cluster connectivity).
"""
import math
from collections import Counter, defaultdict

import networkx as nx
import numpy as np

# Sparse zones grouped together in space (same bucket as render._ZONE_AS_OTHER).
_ZONE_AS_OTHER = frozenset({"motor", "ascending", "visual_centrifugal"})
_LAYOUT_OTHER = "_other"


def _layout_zone(zone):
    z = zone or "unknown"
    return _LAYOUT_OTHER if z in _ZONE_AS_OTHER else z


_ZONE_TEMPLATE = {
    "optic_lobe": np.array([-7.5, -1.2]),
    "central_brain": np.array([-0.8, -0.2]),
    "sensory": np.array([-4.4, 6.4]),
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


def _refine_zone_centroids(ZG, zone_counts, seed=42, template_scale=1.0, template_blend=0.78):
    base = {z: _ZONE_TEMPLATE.get(z, np.array([0.0, 0.0])).copy() for z in zone_counts}
    if template_scale != 1.0 and base:
        arr = np.array(list(base.values()))
        center = arr.mean(axis=0)
        base = {z: center + template_scale * (p - center) for z, p in base.items()}

    if ZG.number_of_edges() == 0:
        return base

    for u, v, d in ZG.edges(data=True):
        d["weight"] = math.log1p(d.get("weight", 1))

    refined = nx.spring_layout(
        ZG, pos=base, weight="weight", k=1.6, iterations=50, seed=seed
    )
    return {
        z: template_blend * base.get(z, np.array([0.0, 0.0]))
        + (1.0 - template_blend) * np.array(refined.get(z, base.get(z, np.array([0.0, 0.0]))))
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
    """Spring layout if intra-zone edges exist; otherwise spiral/grid."""
    nodes = list(sub.nodes)
    n = len(nodes)
    if n == 1:
        return {nodes[0]: np.array([0.0, 0.0])}

    m_edges = sub.number_of_edges()

    # Local spring: respects intra-cluster topology.
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
    G,
    zone_attr="zone",
    seed=42,
    spread_scale=1.0,
    side_split=True,
    side_attr="side",
    zone_gap=0.65,
    template_scale=1.0,
    template_blend=0.78,
):
    rng = np.random.default_rng(seed)
    zones = nx.get_node_attributes(G, zone_attr)
    layout_zones = {n: _layout_zone(zones.get(n)) for n in G.nodes}
    zone_counts = Counter(layout_zones.values())

    ZG = _zone_meta_graph(G, zone_attr, zone_key=_layout_zone)
    centroids = _refine_zone_centroids(
        ZG, zone_counts, seed=seed,
        template_scale=template_scale, template_blend=template_blend,
    )
    centroids = _resolve_zone_overlaps(centroids, zone_counts, gap=zone_gap)

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
    """Within each layout cluster, shift L to the left and R to the right."""
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


def _primary_inter_zone(TG, t, zt, zone_key, zone_attr, anatomy):
    scores = defaultdict(float)
    template_t = anatomy.get(zt, np.zeros(2))
    for u, v, d in TG.edges(data=True):
        if t not in (u, v) or u == v:
            continue
        other = v if u == t else u
        zo = zone_key(TG.nodes[other].get(zone_attr))
        if zo != zt:
            scores[zo] += float(d.get("weight", 1))
    if not scores:
        return None
    return max(scores, key=scores.get)


def layout_types_toward_zones(
    TG,
    pos,
    zone_attr="zone",
    zone_key=None,
    radii=None,
    inter_blend=0.58,
    edge_min_frac=0.22,
    edge_max_frac=0.62,
    angle_step=0.42,
):
    """
    Position each type on the cluster side facing interconnected zones.
    Direction from anatomical template; intensity proportional to inter vs intra weight.
    """
    if zone_key is None:
        zone_key = lambda z: z  # noqa: E731

    initial = {n: np.array(p, dtype=float) for n, p in pos.items()}

    def _node_zone(t):
        return zone_key(TG.nodes[t].get(zone_attr))

    anatomy = {
        "optic_lobe": np.array([-7.5, -1.2]),
        "central_brain": np.array([-0.8, -0.2]),
        "sensory": np.array([-4.4, 6.4]),
        "visual_projection": np.array([3.8, -5.1]),
        "descending": np.array([5.4, 2.2]),
    }

    by_zone = defaultdict(list)
    for t in initial:
        by_zone[_node_zone(t)].append(t)

    zone_anchors = {}
    zone_radius = {}
    for z, nodes in by_zone.items():
        pts = np.array([initial[t] for t in nodes])
        zone_anchors[z] = pts.mean(axis=0)
        zone_radius[z] = max(
            max(float(np.ptp(pts[:, 0])), float(np.ptp(pts[:, 1])), 0.5) * 0.62,
            0.55,
        )

    out = {}
    inter_fracs = {}
    for t, p0 in initial.items():
        zt = _node_zone(t)
        anchor = zone_anchors[zt]
        template_t = anatomy.get(zt, anchor)

        inter_pull = np.zeros(2)
        intra_w = inter_w = 0.0
        for u, v, d in TG.edges(data=True):
            if t not in (u, v) or u == v:
                continue
            w = float(d.get("weight", 1))
            other = v if u == t else u
            zo = _node_zone(other)
            if zo == zt:
                intra_w += w
            else:
                template_o = anatomy.get(zo, zone_anchors.get(zo, anchor))
                inter_pull += w * (template_o - template_t)
                inter_w += w

        if inter_w > 0:
            direction = inter_pull / inter_w
            norm = float(np.linalg.norm(direction))
            if norm > 1e-9:
                direction /= norm
            inter_frac = inter_w / (inter_w + intra_w)
            inter_fracs[t] = inter_frac
            edge_dist = zone_radius[zt] * (
                edge_min_frac + (edge_max_frac - edge_min_frac) * inter_frac
            )
            target = anchor + direction * edge_dist
            blend = inter_blend * (0.40 + 0.60 * inter_frac)
            p_new = (1.0 - blend) * p0 + blend * target
        else:
            inter_fracs[t] = 0.0
            p_new = p0.copy()

        delta = p_new - anchor
        max_r = zone_radius[zt] * 0.98
        dn = float(np.linalg.norm(delta))
        if dn > max_r and dn > 1e-9:
            p_new = anchor + delta * (max_r / dn)
        out[t] = p_new

    if radii:
        by_primary = defaultdict(lambda: defaultdict(list))
        for t in out:
            zt = _node_zone(t)
            primary = _primary_inter_zone(TG, t, zt, zone_key, zone_attr, anatomy)
            if primary is None:
                continue
            by_primary[zt][primary].append(t)

        for zt, groups in by_primary.items():
            anchor = zone_anchors[zt]
            template_t = anatomy.get(zt, anchor)
            for primary, group in groups.items():
                group = [
                    t for t in group
                    if inter_fracs.get(t, 0.0) >= 0.42
                ]
                if len(group) <= 1:
                    continue
                template_o = anatomy.get(primary, anchor)
                direction = template_o - template_t
                norm = float(np.linalg.norm(direction))
                if norm < 1e-9:
                    continue
                direction /= norm
                base_angle = math.atan2(direction[1], direction[0])
                group = sorted(group, key=lambda t: (-radii.get(t, 0.5), t))
                n = len(group)
                step = min(angle_step, 0.85 / max(n - 1, 1))
                for i, t in enumerate(group):
                    angle = base_angle + (i - (n - 1) / 2.0) * step
                    dist = float(np.linalg.norm(out[t] - anchor))
                    dist = max(dist, zone_radius[zt] * edge_min_frac)
                    out[t] = anchor + dist * np.array([
                        math.cos(angle), math.sin(angle),
                    ])
                    max_r = zone_radius[zt] * 0.98
                    delta = out[t] - anchor
                    dn = float(np.linalg.norm(delta))
                    if dn > max_r and dn > 1e-9:
                        out[t] = anchor + delta * (max_r / dn)

    return {n: (float(p[0]), float(p[1])) for n, p in out.items()}


def pack_types_in_zones(
    TG,
    pos,
    targets,
    radii,
    zone_attr="zone",
    zone_key=None,
    iterations=560,
    gap=0.46,
    target_pull=0.10,
    max_radius_frac=1.28,
):
    """
    Per-zone: remove circle overlaps while keeping each type toward its
    directional target (layout_types_toward_zones).
    """
    if zone_key is None:
        zone_key = lambda z: z  # noqa: E731

    def _node_zone(t):
        return zone_key(TG.nodes[t].get(zone_attr))

    by_zone = defaultdict(list)
    for t in pos:
        by_zone[_node_zone(t)].append(t)

    anchors = {}
    max_r_zone = {}
    for z, nodes in by_zone.items():
        pts = np.array([np.array(pos[t], dtype=float) for t in nodes])
        anchors[z] = pts.mean(axis=0)
        max_r_zone[z] = max(
            max(float(np.ptp(pts[:, 0])), float(np.ptp(pts[:, 1])), 0.5) * 0.82,
            0.85,
        )

    out = {t: np.array(targets.get(t, pos[t]), dtype=float) for t in pos}

    for _ in range(iterations):
        moved = False
        for z, nodes in by_zone.items():
            anchor = anchors[z]
            max_r = max_r_zone[z] * max_radius_frac

            for t in nodes:
                tgt = np.array(targets.get(t, out[t]), dtype=float)
                out[t] += target_pull * (tgt - out[t])
                delta = out[t] - anchor
                dn = float(np.linalg.norm(delta))
                if dn > max_r and dn > 1e-9:
                    out[t] = anchor + delta * (max_r / dn)

            for i, a in enumerate(nodes):
                for b in nodes[i + 1:]:
                    delta = out[b] - out[a]
                    dist = float(np.linalg.norm(delta))
                    need = radii[a] + radii[b] + gap
                    if dist < need:
                        if dist > 1e-9:
                            push = (need - dist) * 0.58 * delta / dist
                        else:
                            push = np.array([need * 0.52, 0.0])
                        out[a] -= push
                        out[b] += push
                        moved = True

            for t in nodes:
                delta = out[t] - anchor
                dn = float(np.linalg.norm(delta))
                if dn > max_r and dn > 1e-9:
                    out[t] = anchor + delta * (max_r / dn)

        if not moved:
            break

    return {n: (float(v[0]), float(v[1])) for n, v in out.items()}
