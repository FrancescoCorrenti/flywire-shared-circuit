"""
06_visualize / zone_flows.py
Frecce inter-zona: centro sorgente → fuori cluster destinazione, lane parallele, spessore ∝ count.
"""
import math
from collections import Counter, defaultdict

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

_ARROW_ZORDER = 0.8
_FLOW_COLOR = "#2a2a2a"
_LANE_RAD = 0.26
_ASYM_RATIO = 3.0  # >> : flusso debole molto più trasparente


def _zone_label_bbox(pts):
    """BBox approssimativo del riquadro etichetta sotto al cluster."""
    arr = np.asarray(pts)
    cx = float(arr[:, 0].mean())
    y_top = float(arr[:, 1].min() - 0.18 * max(float(np.ptp(arr[:, 1])), 0.35))
    half_w, height = 0.62, 0.78
    return np.array([cx - half_w, cx + half_w, y_top - height, y_top + 0.06])


def _nudge_from_label(p_end, bbox, p_start):
    """Sposta la punta fuori dal riquadro etichetta se ci cade dentro."""
    p = np.asarray(p_end, dtype=float).copy()
    xmin, xmax, ymin, ymax = bbox

    def _inside(pt):
        return xmin <= pt[0] <= xmax and ymin <= pt[1] <= ymax

    if not _inside(p):
        return p
    d = p - np.asarray(p_start, dtype=float)
    norm = float(np.linalg.norm(d))
    if norm > 1e-9:
        d /= norm
        for _ in range(10):
            p -= d * 0.14
            if not _inside(p):
                return p
    p[1] = ymin - 0.16
    return p


def _zone_node_groups(pos, zones):
    by_zone = defaultdict(list)
    for n, p in pos.items():
        by_zone[zones.get(n, "unknown")].append(np.array(p, dtype=float))
    return by_zone


def _cluster_center(pts):
    return np.mean(pts, axis=0)


def _outside_toward(pts, from_point, pad=0.40):
    """Punto appena fuori dal cluster, lato rivolto verso from_point."""
    pts = np.asarray(pts)
    c = _cluster_center(pts)
    d = np.asarray(from_point, dtype=float) - c
    norm = float(np.linalg.norm(d))
    if norm < 1e-9:
        return c + np.array([0.0, pad])
    d /= norm
    proj = (pts - c) @ d
    return c + d * (float(proj.max()) + pad)


def _flow_endpoints(by_zone, z_from, z_to, pad=0.40):
    c_f = _cluster_center(by_zone[z_from])
    p_start = np.asarray(c_f, dtype=float)
    p_end = _outside_toward(by_zone[z_to], c_f, pad=pad)
    return p_start, p_end


def _lane_rad(z_from, z_to):
    """Lane parallele: flusso inverso = curvatura opposta."""
    return _LANE_RAD if (z_from, z_to) <= (z_to, z_from) else -_LANE_RAD


def _flow_alpha(cnt, rev_cnt, t):
    """Alpha pieno sul verso dominante; trasparenza sul verso debole se cnt >> rev."""
    base = 0.50 + 0.38 * t
    if rev_cnt <= 0:
        return base
    hi, lo = max(cnt, rev_cnt), min(cnt, rev_cnt)
    if lo <= 0 or hi / lo < _ASYM_RATIO:
        return base
    if cnt < rev_cnt:
        return max(0.12, base * 0.28)
    return min(0.92, base + 0.10)


def directed_zone_flows(G, dzones, show_other=True):
    flows = Counter()
    for u, v in G.edges():
        zu, zv = dzones.get(u), dzones.get(v)
        if zu and zv and zu != zv:
            if not show_other and ("other" in (zu, zv)):
                continue
            flows[(zu, zv)] += 1
    return flows


def directed_zone_arrows(by_zone, flows, pad=0.40):
    patches = []
    if not flows:
        return patches
    label_boxes = {z: _zone_label_bbox(pts) for z, pts in by_zone.items()}
    counts = np.array(list(flows.values()), dtype=float)
    log_c = np.log1p(counts)
    lo, hi = float(log_c.min()), float(log_c.max())

    for (z_from, z_to), cnt in flows.items():
        if z_from not in by_zone or z_to not in by_zone:
            continue
        p_start, p_end = _flow_endpoints(by_zone, z_from, z_to, pad=pad)
        if z_to in label_boxes:
            p_end = _nudge_from_label(p_end, label_boxes[z_to], p_start)
        rad = _lane_rad(z_from, z_to)
        t = (math.log1p(cnt) - lo) / (hi - lo) if hi > lo else 0.5
        rev_cnt = flows.get((z_to, z_from), 0)
        alpha = _flow_alpha(cnt, rev_cnt, t)
        patches.append(
            FancyArrowPatch(
                p_start, p_end, arrowstyle="-|>",
                mutation_scale=6 + 5 * t,
                connectionstyle="arc3,rad=%.3f" % rad,
                color=_FLOW_COLOR,
                linewidth=0.55 + 2.4 * t,
                alpha=alpha,
                zorder=_ARROW_ZORDER,
            )
        )
    return patches


def draw_directed_zone_arrows(ax, G, dzones, pos, pad=0.40, show_other=True):
    flows = directed_zone_flows(G, dzones, show_other=show_other)
    by_zone = _zone_node_groups(pos, dzones)
    if not show_other and "other" in by_zone:
        del by_zone["other"]
    for patch in directed_zone_arrows(by_zone, flows, pad=pad):
        ax.add_patch(patch)


def inter_zone_flow_legend_handles():
    return [
        Line2D(
            [0], [0], color=_FLOW_COLOR, linewidth=1.8,
            marker=">", markersize=6, label="synapse direction",
        ),
    ]
