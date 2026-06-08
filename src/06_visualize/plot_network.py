"""
06_visualize / plot_network.py — CLI for the deliverable network graphs.

Usage:
  python plot_network.py                         # neurons -> network_graph.pdf
  python plot_network.py --mode types            # types -> network_graph_types.pdf
  python plot_network.py --mode both             # both PDFs
"""
import argparse
import os
import sys
import time

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_BASE, "src", "06_visualize"))

from load_graph import BASE, build_circuit_graph, graph_summary  # noqa: E402
from layout import zone_force_layout, layout_types_toward_zones, pack_types_in_zones  # noqa: E402
from render import render_network_pdf  # noqa: E402
from render_types import render_type_network_pdf, _type_radii  # noqa: E402
from render import _display_zone, _visible_zone  # noqa: E402
from type_graph import build_type_graph, collapse_type_graph, type_graph_summary  # noqa: E402

DEFAULT_NEURONS = os.path.join(BASE, "report", "figures", "network_graph.pdf")
DEFAULT_TYPES = os.path.join(BASE, "report", "figures", "network_graph_types.pdf")
DEFAULT_DISPLAY_TYPES = os.path.join(BASE, "type_graphs", "display_types.csv")


def plot_network_neurons(
    csv_path,
    output_path,
    dataset="FAFB",
    seed=42,
    edge_mode="both",
):
    t0 = time.time()
    print("Loading circuit from %s (%s) ..." % (csv_path, dataset), flush=True)
    G = build_circuit_graph(csv_path, dataset=dataset)
    info = graph_summary(G)
    print(
        "  %d nodes, %d edges, %d types, %d zones"
        % (info["n_nodes"], info["n_edges"], info["n_types"], info["n_zones"]),
        flush=True,
    )

    print("Computing neuron layout (spring intra-cluster) ...", flush=True)
    pos = zone_force_layout(G, seed=seed)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    print("Rendering neurons -> %s" % output_path, flush=True)
    render_network_pdf(G, pos, output_path, edge_mode=edge_mode)
    print("Done in %.1fs" % (time.time() - t0), flush=True)
    return G, pos, output_path


def plot_network_types(
    csv_path,
    output_path,
    dataset="FAFB",
    seed=42,
    spread_scale=10.5,
    display_types_path=None,
    zone_gap=2.45,
    template_scale=1.82,
):
    t0 = time.time()
    display_types_path = display_types_path or DEFAULT_DISPLAY_TYPES
    print("Loading circuit from %s (%s) ..." % (csv_path, dataset), flush=True)
    G = build_circuit_graph(csv_path, dataset=dataset)
    info = graph_summary(G)
    print(
        "  %d nodes, %d edges, %d types, %d zones"
        % (info["n_nodes"], info["n_edges"], info["n_types"], info["n_zones"]),
        flush=True,
    )

    TG = build_type_graph(G)
    TG = collapse_type_graph(
        TG,
        display_types_path=display_types_path,
        zone_key=_display_zone,
        visible_zone=_visible_zone,
    )
    tinfo = type_graph_summary(TG)
    print(
        "  type graph: %d displayed types (+ other/zone), %d edges  [%s]"
        % (tinfo["n_types"], tinfo["n_edges"], display_types_path),
        flush=True,
    )

    print("Computing type layout ...", flush=True)
    pos = zone_force_layout(
        TG, zone_attr="zone", seed=seed,
        spread_scale=spread_scale, side_split=False,
        zone_gap=zone_gap, template_scale=template_scale, template_blend=0.88,
    )
    radii = _type_radii(TG)
    targets = layout_types_toward_zones(
        TG, pos, zone_key=_display_zone, radii=radii,
    )
    pos = pack_types_in_zones(
        TG, pos, targets, radii, zone_key=_display_zone,
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    print("Rendering types -> %s" % output_path, flush=True)
    render_type_network_pdf(G, TG, pos, output_path)
    print("Done in %.1fs" % (time.time() - t0), flush=True)
    return G, TG, pos, output_path


def plot_network(
    csv_path,
    output_path,
    dataset="FAFB",
    seed=42,
    edge_mode="both",
    mode="neurons",
    types_output_path=None,
    spread_scale=10.5,
    display_types_path=None,
    zone_gap=2.45,
    template_scale=1.82,
):
    """mode: neurons | types | both"""
    if mode == "neurons":
        return plot_network_neurons(
            csv_path, output_path, dataset=dataset, seed=seed, edge_mode=edge_mode,
        )
    if mode == "types":
        out = types_output_path or DEFAULT_TYPES
        return plot_network_types(
            csv_path, out, dataset=dataset, seed=seed,
            spread_scale=spread_scale,
            display_types_path=display_types_path,
            zone_gap=zone_gap,
            template_scale=template_scale,
        )
    if mode == "both":
        r1 = plot_network_neurons(
            csv_path, output_path, dataset=dataset, seed=seed, edge_mode=edge_mode,
        )
        out_types = types_output_path or DEFAULT_TYPES
        r2 = plot_network_types(
            csv_path, out_types, dataset=dataset, seed=seed,
            spread_scale=spread_scale,
            display_types_path=display_types_path,
            zone_gap=zone_gap,
            template_scale=template_scale,
        )
        return r1, r2
    raise ValueError("mode must be neurons, types, or both")


def main():
    default_csv = os.path.join(BASE, "submission_mega.csv")

    ap = argparse.ArgumentParser(description="Render circuit network graph(s) to PDF/EPS")
    ap.add_argument("--csv", default=default_csv, help="Deliverable CSV (default: submission_mega.csv)")
    ap.add_argument("--dataset", default="FAFB", choices=["FAFB", "BANC", "MCNS"])
    ap.add_argument(
        "--mode",
        default="neurons",
        choices=["neurons", "types", "both"],
        help="neurons = per-neuron graph; types = aggregated type graph; both = generate both PDFs",
    )
    ap.add_argument(
        "--output", "-o", default=DEFAULT_NEURONS,
        help="Output for neuron view (default: report/figures/network_graph.pdf)",
    )
    ap.add_argument(
        "--types-output",
        default=DEFAULT_TYPES,
        help="Output for type view (default: report/figures/network_graph_types.pdf)",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--edge-mode",
        default="both",
        choices=["both", "intra", "inter", "zone_summary", "none"],
        help="Edge drawing for neuron view only",
    )
    ap.add_argument(
        "--spread-scale", type=float, default=10.5,
        help="Cluster spread multiplier for type view (default: 10.5)",
    )
    ap.add_argument(
        "--zone-gap", type=float, default=2.45,
        help="Minimum gap between zone cluster anchors for type view (default: 2.45)",
    )
    ap.add_argument(
        "--template-scale", type=float, default=1.82,
        help="Scale anatomical zone template for type view (default: 1.82)",
    )
    ap.add_argument(
        "--display-types",
        default=DEFAULT_DISPLAY_TYPES,
        help="CSV with types to show (default: type_graphs/display_types.csv)",
    )
    args = ap.parse_args()

    plot_network(
        csv_path=args.csv,
        output_path=args.output,
        dataset=args.dataset,
        seed=args.seed,
        edge_mode=args.edge_mode,
        mode=args.mode,
        types_output_path=args.types_output,
        spread_scale=args.spread_scale,
        display_types_path=args.display_types,
        zone_gap=args.zone_gap,
        template_scale=args.template_scale,
    )


if __name__ == "__main__":
    main()
