"""
06_visualize / render_types.py
Condensed per-type view: circle area = cell count, class hue + saturation = degree.
"""
import colorsys
import math
from collections import Counter, defaultdict

import matplotlib.colors as mc
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch

from render import (
    _ZONE_COLORS,
    _display_zone,
    _display_zones,
    _filter_visible_pos,
    _tight_axis_limits,
    _visible_zone,
    _zone_ellipses,
    _zone_side_counts,
)
from type_graph import is_other_type


def _is_other_node(TG, t):
    return TG.nodes[t].get("is_other") or is_other_type(t)


def _type_zone(TG, t):
    return _display_zone(TG.nodes[t].get("zone"))


def relax_type_positions(pos, radii, gap=0.38, iterations=200):
    """Light repulsion between overlapping circles."""
    out = {k: np.array(v, dtype=float) for k, v in pos.items()}
    keys = [k for k in out if k in radii]
    for _ in range(iterations):
        moved = False
        for i, a in enumerate(keys):
            for b in keys[i + 1 :]:
                delta = out[b] - out[a]
                dist = float(np.linalg.norm(delta))
                need = radii[a] + radii[b] + gap
                if dist < need and dist > 1e-9:
                    push = (need - dist) * 0.48 * delta / dist
                    out[a] -= push
                    out[b] += push
                    moved = True
        if not moved:
            break
    return {k: (float(v[0]), float(v[1])) for k, v in out.items()}


def _type_radii(TG, min_r=0.68, max_r=1.30):
    log_n = {t: math.log1p(TG.nodes[t].get("n_neurons", 1)) for t in TG.nodes}
    lo, hi = min(log_n.values()), max(log_n.values())
    radii = {}
    for t in TG.nodes:
        if hi == lo:
            radii[t] = (min_r + max_r) / 2
        else:
            radii[t] = min_r + (max_r - min_r) * (log_n[t] - lo) / (hi - lo)
    return radii


def _type_color_palette(TG, zone_colors, sat_lo=0.20, sat_hi=0.95, light=0.47):
    """Class hue fixed; saturation ∝ log type degree (within each class)."""
    by_zone = defaultdict(list)
    for t in TG.nodes:
        if _is_other_node(TG, t):
            continue
        by_zone[_type_zone(TG, t)].append(t)

    colors = {}
    for zone, types in by_zone.items():
        h, _, _ = colorsys.rgb_to_hls(*mc.to_rgb(zone_colors.get(zone, "#888888")))
        log_deg = [math.log1p(TG.nodes[t].get("degree", 0)) for t in types]
        lo, hi = min(log_deg), max(log_deg)
        for t in types:
            ld = math.log1p(TG.nodes[t].get("degree", 0))
            frac = 0.5 if hi == lo else (ld - lo) / (hi - lo)
            sat = sat_lo + (sat_hi - sat_lo) * frac
            colors[t] = colorsys.hls_to_rgb(h, light, sat)

    for t in TG.nodes:
        if t in colors:
            continue
        z = _type_zone(TG, t)
        h, _, _ = colorsys.rgb_to_hls(*mc.to_rgb(zone_colors.get(z, "#888888")))
        colors[t] = colorsys.hls_to_rgb(h, 0.55, sat_lo)
    return colors


def _label_text(TG, t):
    info = TG.nodes[t]
    if info.get("is_other"):
        n = info.get("n_neurons", 0)
        k = info.get("n_types", 0)
        if k > 1:
            return "other\n(%d)" % k
        return "other\nn=%d" % n
    name = str(info.get("label", t)).replace("_", " ")
    if len(name) > 10 and " " not in name:
        mid = len(name) // 2
        return name[:mid] + "\n" + name[mid:]
    return name



def _clip_edge_endpoints(p0, p1, r0, r1, pad=0.06, tip_pad=0.11):
    """Shortens the arc: exits from the source border, tip stays outside the destination circle."""
    a = np.asarray(p0, dtype=float)
    b = np.asarray(p1, dtype=float)
    d = b - a
    dist = float(np.linalg.norm(d))
    if dist < 1e-9:
        return a, b
    u = d / dist
    start = a + u * (r0 + pad)
    end = b - u * (r1 + tip_pad)
    if float(np.linalg.norm(end - start)) < 0.04:
        end = b - u * (r1 + tip_pad * 0.5)
    return start, end


def _edge_style(weight, lo, hi):
    t = (math.log1p(weight) - lo) / (hi - lo) if hi > lo else 0.5
    return 0.75 + 2.2 * t, 0.38 + 0.48 * t


def _draw_type_edges(ax, TG, pos, type_colors, radii):
    edges = [
        (u, v, d) for u, v, d in TG.edges(data=True)
        if u in pos and v in pos
        and not _is_other_node(TG, u) and not _is_other_node(TG, v)
    ]
    if not edges:
        return
    weights = [d.get("weight", 1) for _, _, d in edges]
    log_w = [math.log1p(w) for w in weights]
    lo, hi = min(log_w), max(log_w)

    for u, v, d in edges:
        w = d.get("weight", 1)
        lw, alpha = _edge_style(w, lo, hi)
        cu = type_colors.get(u, (0.5, 0.5, 0.5))
        cv = type_colors.get(v, (0.5, 0.5, 0.5))
        color = tuple(0.5 * a + 0.5 * b for a, b in zip(cu, cv))
        zu, zv = _type_zone(TG, u), _type_zone(TG, v)
        intra = zu == zv
        rad = 0.04 if intra else 0.08
        p0, p1 = _clip_edge_endpoints(
            pos[u], pos[v], radii[u], radii[v],
        )
        ax.add_patch(
            FancyArrowPatch(
                p0, p1,
                arrowstyle="->" if intra else "-|>",
                mutation_scale=7 + 3 * lw if intra else 8 + 3 * lw,
                connectionstyle="arc3,rad=%.3f" % rad,
                color=color,
                linewidth=lw,
                linestyle="--" if intra else "solid",
                alpha=alpha,
                zorder=1.6,
            )
        )


def _draw_type_nodes(ax, TG, pos, type_colors, radii):
    for t in TG.nodes:
        if t not in pos:
            continue
        x, y = pos[t]
        r = radii[t]
        fill = type_colors[t]
        circle = Circle(
            (x, y), radius=r,
            facecolor=fill,
            edgecolor="white",
            linewidth=1.1,
            alpha=0.94,
            zorder=3,
        )
        ax.add_patch(circle)
        label = _label_text(TG, t)
        n_lines = label.count("\n") + 1
        fontsize = max(9.0, min(14.5, r * 11.8 / max(n_lines, 1)))
        ax.text(
            x, y, label,
            ha="center", va="center",
            fontsize=fontsize,
            fontweight="bold",
            color="#111111",
            zorder=4,
            linespacing=0.9,
        )


def _zone_type_label(ax, zone, pts, body):
    arr = np.array(pts)
    span = max(float(np.ptp(arr[:, 0])), float(np.ptp(arr[:, 1])), 0.35)
    title = zone.replace("_", " ")
    text = title + "\n" + body

    if zone == "sensory":
        lx = float(arr[:, 0].min()) - 0.16 * span - 0.72
        ly = float(arr[:, 1].mean())
        ha, va = "right", "center"
    elif zone == "visual_projection":
        lx = float(arr[:, 0].max()) + 0.05 * span + 0.12
        ly = float(arr[:, 1].min()) - 0.08 * span - 0.28
        ha, va = "left", "top"
    elif zone == "central_brain":
        lx = float(arr[:, 0].mean()) + 0.14 * span
        ly = float(arr[:, 1].max()) + 0.14 * span + 0.38
        ha, va = "center", "bottom"
    else:
        lx = float(arr[:, 0].mean())
        ly = float(arr[:, 1].min()) - 0.18 * span - 0.52
        ha, va = "center", "top"

    ax.text(
        lx, ly, text,
        ha=ha, va=va, fontsize=10.5, fontweight="bold",
        color="#111111", zorder=4, linespacing=1.05,
        bbox=dict(
            boxstyle="round,pad=0.28", facecolor="white",
            edgecolor="#333333", linewidth=0.7, alpha=0.94,
        ),
    )
    return lx, ly, ha, va


def _zone_type_label_body(n_types, n_neurons, n_l, n_r):
    return (
        "$n_{\\mathrm{types}}$=%d\n$n_{\\mathrm{neurons}}$=%d\n"
        "$n_{\\mathrm{L}}$=%d  $n_{\\mathrm{R}}$=%d"
        % (n_types, n_neurons, n_l, n_r)
    )


def _total_types_per_zone(G):
    """Count of distinct types per zone in the full circuit."""
    by_zone = defaultdict(set)
    for n in G.nodes:
        z = _display_zone(G.nodes[n].get("zone"))
        if not _visible_zone(z):
            continue
        by_zone[z].add(G.nodes[n].get("type"))
    return {z: len(types) for z, types in by_zone.items()}


def _tight_limits_circles(pos, by_zone, radii, margin=0.28):
    x0, x1, y0, y1 = _tight_axis_limits(pos, by_zone)
    for t, (x, y) in pos.items():
        r = radii.get(t, 0.15)
        x0 = min(x0, x - r - 0.10)
        x1 = max(x1, x + r + 0.10)
        y0 = min(y0, y - r - 0.10)
        y1 = max(y1, y + r + 0.10)
    if "sensory" in by_zone and by_zone["sensory"]:
        arr = np.array(by_zone["sensory"])
        span = max(float(np.ptp(arr[:, 0])), float(np.ptp(arr[:, 1])), 0.35)
        x0 = min(x0, float(arr[:, 0].min()) - 0.16 * span - 0.95)
    if "visual_projection" in by_zone and by_zone["visual_projection"]:
        arr = np.array(by_zone["visual_projection"])
        span = max(float(np.ptp(arr[:, 0])), float(np.ptp(arr[:, 1])), 0.35)
        x1 = max(x1, float(arr[:, 0].max()) + 0.08 * span + 0.42)
    if "central_brain" in by_zone and by_zone["central_brain"]:
        arr = np.array(by_zone["central_brain"])
        span = max(float(np.ptp(arr[:, 0])), float(np.ptp(arr[:, 1])), 0.35)
        y1 = max(y1, float(arr[:, 1].max()) + 0.14 * span + 0.75)
    x_span = max(x1 - x0, 1.0)
    y_span = max(y1 - y0, 1.0)
    pad_x = margin + 0.025 * x_span
    pad_y = margin + 0.025 * y_span
    return x0 - pad_x, x1 + pad_x, y0 - pad_y, y1 + pad_y


def render_type_network_pdf(
    G,
    TG,
    pos,
    output_path,
    figsize=(14.5, 10.2),
    dpi=300,
):
    zones = nx.get_node_attributes(G, "zone")
    dzones_g = _display_zones(zones)
    dzones_t = {t: _type_zone(TG, t) for t in TG.nodes}
    vis_types = [t for t in TG.nodes if _visible_zone(dzones_t[t])]
    zone_list = sorted(z for z in set(dzones_t.values()) if _visible_zone(z))
    zone_colors = {z: _ZONE_COLORS.get(z, "#888888") for z in zone_list}
    type_colors = _type_color_palette(TG, zone_colors)
    radii = _type_radii(TG)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_facecolor("#FAFAFA")
    ax.axis("off")

    by_zone_pts = defaultdict(list)
    for t in vis_types:
        z = dzones_t[t]
        if t in pos:
            by_zone_pts[z].append(pos[t])

    vis_pos = _filter_visible_pos(
        {t: pos[t] for t in vis_types if t in pos},
        dzones_t,
    )
    vis_dzones = {t: dzones_t[t] for t in vis_pos}

    for patch in _zone_ellipses(vis_pos, vis_dzones, zone_colors):
        ax.add_patch(patch)

    _draw_type_edges(ax, TG, pos, type_colors, radii)
    _draw_type_nodes(ax, TG, pos, type_colors, radii)

    total_types = _total_types_per_zone(G)
    neuron_count = Counter()
    for n in G.nodes:
        z = _display_zone(G.nodes[n].get("zone"))
        if _visible_zone(z):
            neuron_count[z] += 1
    side_counts = _zone_side_counts(G, dzones_g, side_attr="side")
    for zone, pts in by_zone_pts.items():
        if not _visible_zone(zone):
            continue
        sc = side_counts[zone]
        body = _zone_type_label_body(
            total_types.get(zone, 0), neuron_count[zone], sc["L"], sc["R"],
        )
        _zone_type_label(ax, zone, pts, body)

    x0, x1, y0, y1 = _tight_limits_circles(vis_pos, by_zone_pts, radii)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")

    data_w = max(x1 - x0, 1e-6)
    data_h = max(y1 - y0, 1e-6)
    fig_w, _ = figsize
    fig.set_size_inches(fig_w, fig_w * data_h / data_w)

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ext = output_path.lower().rsplit(".", 1)[-1]
    fmt = {"pdf": "pdf", "eps": "eps", "png": "png", "svg": "svg"}.get(ext, "pdf")
    fig.savefig(output_path, format=fmt, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return output_path
