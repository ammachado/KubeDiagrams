"""Application orchestration."""

from __future__ import annotations

from .config import load_config
from .diagnostics import Diagnostics
from .edges import build_edges
from .loaders import load_resources
from .nodes import expand_generated_nodes
from .postprocess import convert_drawio, postprocess_icon_paths
from .renderer import render_diagram


def run(options):
    """Run KubeDiagrams end-to-end."""
    diagnostics = Diagnostics()
    config = load_config(options, diagnostics)
    processor = load_resources(options, config, diagnostics)
    expand_generated_nodes(
        processor.registry,
        processor.process_resource,
        config,
        diagnostics,
    )
    edge_map = build_edges(processor.registry, config, diagnostics)
    output, output_format, drawio_filename = render_diagram(
        processor,
        edge_map,
        config,
        diagnostics,
        options,
    )
    print(f"{output}.{output_format} generated.")
    if drawio_filename is not None:
        convert_drawio(output, output_format, drawio_filename)
    postprocess_icon_paths(output, output_format, options.embed_all_icons, config.dirname)
