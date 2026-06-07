"""
06_visualize / render_types.py
Vista aggregata per tipo: cerchio ∝ degree, archi intra-zona, flussi diretti inter-zona.
"""
import math
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse

from render import (
    SHOW_OTHER,
    _ZONE_COLORS,
    _display_zone,
    _display_zones,
    _pca_ellipse,
    _tight_axis_limits,
    _visible_zone,
    _zone_label,
    _zone_side_counts,
)
from zone_flows import draw_directed_zone_arrows, inter_zone_flow_legend_handles


def _type_sizes(TG, min_size=35.0, max_size=520.0):
    log_deg = {t: math.log1p(TG.nodes[t].get("degree", 0)) for t in TG.nodes}
    lo, hi = min(log_deg.values()), max(log_deg.values())
    sizes = {}
    for t in TG.nodes:
        if hi == lo:
            s = (min_size + max_size) / 2
        else:
            s = min_size + (max_size - min_size) * (log_deg[t] - lo) / (hi - lo)
        if TG.nodes[t].get("n_neurons", 1) == 1:
            s = max(s, min_size * 2.2)
        sizes[t] = s
    return sizes


def _zone_ellipses(pos, zones, color_map):
    by_zone = defaultdict(list)
    for n, p in pos.items():
        by_zone[zones.get(n, "unknown")].append(p)
    patches = []
    for zone, pts in by_zone.items():
        cx, cy, w, h, angle = _pca_ellipse(pts)
        patches.append(
            Ellipse(
                (cx, cy), width=w * 2.4, height=h * 2.4, angle=angle,
                facecolor=color_map.get(zone, "#ccc"),
                edgecolor=color_map.get(zone, "#666"),
                alpha=0.07, linewidth=0.7, zorder=1.2,
            )
        )
    return patches


def _intra_zone_type_edges(TG, pos, dzones, zone_colors, min_weight=1):
    by_zone = defaultdict(list)
    for u, v, d in TG.edges(data=True):
        zu = _display_zone(TG.nodes[u].get("zone"))
        zv = _display_zone(TG.nodes[v].get("zone"))
        if zu != zv or u not in pos or v not in pos:
            continue
        w = d.get("weight", 1)
        if w < min_weight:
            continue
        by_zone[zu].append(([pos[u], pos[v]], w))

    collections = []
    for zone, segments_w in by_zone.items():
        if not segments_w:
            continue
        weights = np.array([w for _, w in segments_w], dtype=float)
        log_w = np.log1p(weights)
        lo, hi = log_w.min(), log_w.max()
        segments = [s for s, _ in segments_w]
        widths = []
        for w in weights:
            t = (math.log1p(w) - lo) / (hi - lo) if hi > lo else 0.5
            widths.append(0.35 + 1.6 * t)
        collections.append(
            LineCollection(
                segments,
                colors=zone_colors.get(zone, "#999"),
                linewidths=widths,
                alpha=0.55,
                zorder=1,
                capstyle="round",
            )
        )
    return collections


def _zone_type_label_body(n_types, n_neurons, n_l, n_r):
    return (
        "n=%d types\n$n_{\\mathrm{neurons}}$=%d\n"
        "$n_{\\mathrm{L}}$=%d  $n_{\\mathrm{R}}$=%d"
        % (n_types, n_neurons, n_l, n_r)
    )


def render_type_network_pdf(
    G,
    TG,
    pos,
    output_path,
    figsize=(9.5, 6.8),
    dpi=300,
):
    zones = nx.get_node_attributes(G, "zone")
    dzones_g = _display_zones(zones)
    dzones_t = {t: _display_zone(TG.nodes[t]["zone"]) for t in TG.nodes}
    zone_list = sorted(z for z in set(dzones_t.values()) if _visible_zone(z))
    zone_colors = {z: _ZONE_COLORS.get(z, "#888888") for z in zone_list}
    sizes = _type_sizes(TG)
    vis_types = [t for t in TG.nodes if _visible_zone(dzones_t[t])]

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_facecolor("#FAFAFA")
    ax.axis("off")

    draw_directed_zone_arrows(ax, G, dzones_g, pos, pad=0.42, show_other=SHOW_OTHER)

    vis_pos = {t: pos[t] for t in vis_types if t in pos}
    vis_dzones = {t: dzones_t[t] for t in vis_types}

    for patch in _zone_ellipses(vis_pos, vis_dzones, zone_colors):
        ax.add_patch(patch)

    for lc in _intra_zone_type_edges(TG, pos, dzones_t, zone_colors):
        ax.add_collection(lc)

    xs, ys, cs, ss = [], [], [], []
    for t in vis_types:
        if t not in pos:
            continue
        xs.append(pos[t][0])
        ys.append(pos[t][1])
        cs.append(zone_colors.get(dzones_t[t], "#888"))
        ss.append(sizes[t])

    ax.scatter(
        xs, ys, c=cs, s=ss, marker="o",
        edgecolors="white", linewidths=0.35, alpha=0.92, zorder=3,
    )

    by_zone_pts = defaultdict(list)
    type_count = Counter()
    neuron_count = Counter()
    for t in vis_types:
        z = dzones_t[t]
        type_count[z] += 1
        neuron_count[z] += TG.nodes[t].get("n_neurons", 0)
        if t in pos:
            by_zone_pts[z].append(pos[t])

    side_counts = _zone_side_counts(G, dzones_g, side_attr="side")
    for zone, pts in by_zone_pts.items():
        if not _visible_zone(zone):
            continue
        sc = side_counts[zone]
        body = _zone_type_label_body(
            type_count[zone], neuron_count[zone], sc["L"], sc["R"]
        )
        _zone_label(
            ax, zone, pts, neuron_count[zone],
            n_l=sc["L"], n_r=sc["R"], body_override=body,
        )

    legend_handles = [
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=zone_colors[z], markeredgecolor="white",
               markeredgewidth=0.5, markersize=9, label=z.replace("_", " "))
        for z in zone_list
    ]
    zone_leg = ax.legend(
        handles=legend_handles, title="Brain zone",
        loc="lower left", bbox_to_anchor=(0.07, 0.17),
        fontsize=7, title_fontsize=7.5, frameon=True,
        borderaxespad=0, labelspacing=0.25, handletextpad=0.35,
        ncol=2, columnspacing=0.9,
    )
    zone_leg.get_frame().set_linewidth(0.6)
    ax.add_artist(zone_leg)

    flow_handles = inter_zone_flow_legend_handles() + [
        Line2D([0], [0], color=zone_colors.get("optic_lobe", "#4477AA"),
               linewidth=1.2, alpha=0.7, label="intra-zone"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#666666",
               markeredgecolor="white", markeredgewidth=0.5, markersize=8,
               label="type ($\\propto$ degree)"),
    ]
    ax.legend(
        handles=flow_handles, loc="upper left", bbox_to_anchor=(0.07, 0.16),
        fontsize=6.5, frameon=True, ncol=1,
        borderaxespad=0, handletextpad=0.35, labelspacing=0.2,
    ).get_frame().set_linewidth(0.6)

    x0, x1, y0, y1 = _tight_axis_limits(vis_pos, by_zone_pts)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ext = output_path.lower().rsplit(".", 1)[-1]
    fmt = {"pdf": "pdf", "eps": "eps", "png": "png", "svg": "svg"}.get(ext, "pdf")
    fig.savefig(output_path, format=fmt, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return output_path
