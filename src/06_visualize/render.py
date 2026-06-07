"""
06_visualize / render.py
Rendering overview per zona anatomica.
"""
import math
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse

from zone_flows import draw_directed_zone_arrows, inter_zone_flow_legend_handles

_ZONE_COLORS = {
    "optic_lobe": "#4477AA",
    "central_brain": "#EE6677",
    "sensory": "#228833",
    "visual_projection": "#CCBB44",
    "descending": "#AA3377",
    "sensory_ascending": "#DDAA33",
    "other": "#999999",
    "unknown": "#999999",
}

# Zone rade → bucket "other" nel grafico overview
_ZONE_AS_OTHER = frozenset({"motor", "ascending", "visual_centrifugal"})
SHOW_OTHER = False  # temporaneo: nascondi cluster "other"


def _display_zone(zone):
    z = zone or "unknown"
    return "other" if z in _ZONE_AS_OTHER else z


def _display_zones(zones):
    return {n: _display_zone(z) for n, z in zones.items()}


def _visible_zone(zone):
    return SHOW_OTHER or zone != "other"


def _filter_visible_pos(pos, dzones):
    return {
        n: p for n, p in pos.items()
        if _visible_zone(dzones.get(n, "unknown"))
    }


def _node_sizes(G, zones, min_size=16.0, max_size=80.0):
    deg = dict(G.degree())
    log_deg = {n: math.log1p(deg[n]) for n in G.nodes}
    lo, hi = min(log_deg.values()), max(log_deg.values())
    sizes = {}
    for n in G.nodes:
        if hi == lo:
            s = (min_size + max_size) / 2
        else:
            s = min_size + (max_size - min_size) * (log_deg[n] - lo) / (hi - lo)
        if sum(1 for m in G.nodes if zones.get(m) == zones.get(n)) == 1:
            s = max(s, 130.0)
        sizes[n] = s
    return sizes


def _zone_centroids(pos, zones):
    by_zone = defaultdict(list)
    for n, p in pos.items():
        by_zone[zones.get(n, "unknown")].append(p)
    return {z: np.mean(pts, axis=0) for z, pts in by_zone.items()}


def _pca_ellipse(pts):
    arr = np.array(pts)
    cx, cy = arr.mean(axis=0)
    if len(arr) < 3:
        r = 0.45 if len(arr) == 1 else 0.32
        return cx, cy, r, r, 0.0
    centered = arr - [cx, cy]
    cov = np.cov(centered.T)
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    angle = math.degrees(math.atan2(vecs[1, 0], vecs[0, 0]))
    w = 2.8 * math.sqrt(max(vals[0], 1e-6))
    h = 2.8 * math.sqrt(max(vals[1], 1e-6))
    return cx, cy, max(w, 0.28), max(h, 0.28), angle


def _zone_ellipses(pos, zones, color_map):
    by_zone = defaultdict(list)
    for n, p in pos.items():
        by_zone[zones.get(n, "unknown")].append(p)
    patches = []
    for zone, pts in by_zone.items():
        cx, cy, w, h, angle = _pca_ellipse(pts)
        patches.append(
            Ellipse(
                (cx, cy), width=w * 2, height=h * 2, angle=angle,
                facecolor=color_map.get(zone, "#ccc"),
                edgecolor=color_map.get(zone, "#666"),
                alpha=0.07, linewidth=0.7, zorder=1.2,
            )
        )
    return patches


def _intra_zone_edges(G, pos, zones, zone_colors):
    by_zone = defaultdict(list)
    for u, v in G.edges():
        zu = zones.get(u)
        if zu and zu == zones.get(v) and u in pos and v in pos:
            by_zone[zu].append([pos[u], pos[v]])

    collections = []
    for zone, segments in by_zone.items():
        if not segments:
            continue
        collections.append(
            LineCollection(
                segments,
                colors=zone_colors.get(zone, "#999"),
                linewidths=0.25,
                alpha=0.32,
                zorder=1,
                capstyle="round",
            )
        )
    return collections


def _zone_label_body(n_nodes, n_l, n_r):
    return (
        "n=%d\n$n_{\\mathrm{L}}$=%d  $n_{\\mathrm{R}}$=%d"
        % (n_nodes, n_l, n_r)
    )


def _zone_side_counts(G, dzones, side_attr="side"):
    sides = nx.get_node_attributes(G, side_attr)
    counts = defaultdict(lambda: {"L": 0, "R": 0})
    for n in G.nodes:
        z = dzones.get(n, "unknown")
        s = sides.get(n, "?")
        if s in ("L", "R"):
            counts[z][s] += 1
    return counts


def _zone_label(ax, zone, pts, n_nodes, n_l=0, n_r=0, body_override=None):
    arr = np.array(pts)
    cx = arr[:, 0].mean()
    cy = arr[:, 1].min() - 0.18 * max(np.ptp(arr[:, 1]), 0.35)
    title = zone.replace("_", " ")
    body = body_override if body_override else _zone_label_body(n_nodes, n_l, n_r)
    ax.text(
        cx, cy, title + "\n" + body,
        ha="center", va="top", fontsize=7.5, fontweight="bold",
        color="#111111", zorder=4, linespacing=1.05,
        bbox=dict(
            boxstyle="round,pad=0.28", facecolor="white",
            edgecolor="#333333", linewidth=0.7, alpha=0.94,
        ),
    )


def _tight_axis_limits(pos, by_zone):
    arr = np.array(list(pos.values()))
    xmin, xmax = arr[:, 0].min(), arr[:, 0].max()
    ymin, ymax = arr[:, 1].min(), arr[:, 1].max()
    x_span = max(xmax - xmin, 1.0)
    y_span = max(ymax - ymin, 1.0)

    for pts in by_zone.values():
        parr = np.array(pts)
        label_drop = 0.18 * max(np.ptp(parr[:, 1]), 0.35) + 0.52
        ymin = min(ymin, parr[:, 1].min() - label_drop)
        xmin = min(xmin, parr[:, 0].min() - 0.55)
        xmax = max(xmax, parr[:, 0].max() + 0.55)
        ymax = max(ymax, parr[:, 1].max() + 0.18)

    pad_x = x_span * 0.025 + 0.12
    pad_y_bottom = y_span * 0.025 + 0.10
    pad_y_top = y_span * 0.012 + 0.05
    return xmin - pad_x, xmax + pad_x, ymin - pad_y_bottom, ymax + pad_y_top


_SIDE_MARKERS = {"L": "o", "R": "s", "?": "o"}


def _scatter_nodes(ax, G, pos, dzones, zone_colors, sizes, side_attr="side"):
    sides = nx.get_node_attributes(G, side_attr)
    buckets = {s: {"x": [], "y": [], "c": [], "s": []} for s in ("L", "R", "?")}

    for n in G.nodes:
        if n not in pos or not _visible_zone(dzones.get(n, "unknown")):
            continue
        side = sides.get(n, "?")
        if side not in buckets:
            side = "?"
        b = buckets[side]
        b["x"].append(pos[n][0])
        b["y"].append(pos[n][1])
        b["c"].append(zone_colors.get(dzones.get(n, "unknown"), "#888"))
        b["s"].append(sizes[n])

    for side, marker in _SIDE_MARKERS.items():
        b = buckets[side]
        if not b["x"]:
            continue
        node_sizes = b["s"]
        if marker == "s":
            node_sizes = [0.82 * s for s in node_sizes]
        ax.scatter(
            b["x"], b["y"], c=b["c"], s=node_sizes, marker=marker,
            edgecolors="white", linewidths=0.25,
            alpha=0.90 if side != "?" else 0.75, zorder=3,
        )


def render_network_pdf(
    G,
    pos,
    output_path,
    zone_attr="zone",
    side_attr="side",
    edge_mode="both",
    figsize=(9.5, 6.8),
    dpi=300,
):
    zones = nx.get_node_attributes(G, zone_attr)
    dzones = _display_zones(zones)
    vis_pos = _filter_visible_pos(pos, dzones)
    zone_list = sorted(z for z in set(dzones.values()) if _visible_zone(z))
    zone_colors = {z: _ZONE_COLORS.get(z, "#888888") for z in zone_list}
    sizes = _node_sizes(G, dzones)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_facecolor("#FAFAFA")
    ax.axis("off")

    if edge_mode in ("both", "inter", "zone_summary"):
        draw_directed_zone_arrows(ax, G, dzones, pos, pad=0.42, show_other=SHOW_OTHER)

    for patch in _zone_ellipses(vis_pos, dzones, zone_colors):
        ax.add_patch(patch)

    n_intra = 0
    if edge_mode in ("both", "intra"):
        for lc in _intra_zone_edges(G, pos, dzones, zone_colors):
            ax.add_collection(lc)
            n_intra += len(lc.get_segments())

    _scatter_nodes(ax, G, pos, dzones, zone_colors, sizes, side_attr=side_attr)

    by_zone = defaultdict(list)
    for n, p in vis_pos.items():
        by_zone[dzones.get(n, "unknown")].append(p)
    side_counts = _zone_side_counts(G, dzones, side_attr=side_attr)
    for zone, pts in by_zone.items():
        if not _visible_zone(zone):
            continue
        sc = side_counts[zone]
        _zone_label(ax, zone, pts, len(pts), n_l=sc["L"], n_r=sc["R"])

    legend_handles = [
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=zone_colors[z], markeredgecolor="white",
               markeredgewidth=0.5, markersize=9, label=z.replace("_", " "))
        for z in zone_list
    ]
    zone_leg = ax.legend(
        handles=legend_handles, title="Brain zone",
        loc="lower left", bbox_to_anchor=(0.07, 0.13),
        fontsize=7, title_fontsize=7.5, frameon=True,
        borderaxespad=0, labelspacing=0.25, handletextpad=0.35,
        ncol=2, columnspacing=0.9,
    )
    zone_leg.get_frame().set_linewidth(0.6)
    ax.add_artist(zone_leg)

    side_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#666666",
               markeredgecolor="white", markeredgewidth=0.5, markersize=7, label="L"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#666666",
               markeredgecolor="white", markeredgewidth=0.5, markersize=6.5, label="R"),
    ]
    side_leg = ax.legend(
        handles=side_handles, loc="lower left", bbox_to_anchor=(0.07, 0.025),
        fontsize=7, frameon=True, ncol=1,
        borderaxespad=0, handletextpad=0.35, labelspacing=0.15,
    )
    side_leg.get_frame().set_linewidth(0.6)
    ax.add_artist(side_leg)

    if edge_mode in ("both", "inter", "zone_summary"):
        ax.legend(
            handles=inter_zone_flow_legend_handles(),
            loc="lower left", bbox_to_anchor=(0.115, 0.025),
            fontsize=6.5, frameon=True, ncol=1,
            borderaxespad=0, handletextpad=0.35, labelspacing=0.15,
        ).get_frame().set_linewidth(0.6)

    x0, x1, y0, y1 = _tight_axis_limits(vis_pos, by_zone)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ext = output_path.lower().rsplit(".", 1)[-1]
    fmt = {"pdf": "pdf", "eps": "eps", "png": "png", "svg": "svg"}.get(ext, "pdf")
    fig.savefig(output_path, format=fmt, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return output_path
