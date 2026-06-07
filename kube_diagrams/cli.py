"""CLI implementation."""

from __future__ import annotations

import argparse
import sys

from .app import run
from .constants import SUPPORTED_OUTPUT_FORMATS
from .options import RunOptions
from .postprocess import normalize_output_paths


def build_parser():
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="kube-diagrams",
        description=(
            "Generate Kubernetes architecture diagrams from Kubernetes manifest files"
        ),
    )
    parser.add_argument(
        "filename", nargs="+", help="the Kubernetes manifest filename to process"
    )
    parser.add_argument("-o", "--output", type=str, help="output diagram filename")
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        help=(
            "output format, allowed formats are "
            + ", ".join(SUPPORTED_OUTPUT_FORMATS)
            + ", set to png by default"
        ),
        default="png",
    )
    parser.add_argument(
        "--embed-all-icons",
        help="embed all icons into svg or dot_json output diagrams",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-c", "--config", type=str, action="append", help="custom kube-diagrams configuration file"
    )
    parser.add_argument(
        "-n", "--namespace", type=str, help="visualize only the resources inside a given namespace"
    )
    parser.add_argument(
        "-v", "--verbose", help="verbosity, set to false by default", action="store_true", default=False
    )
    parser.add_argument(
        "--without-namespace",
        help="disable namespace cluster generation",
        action="store_true",
        default=False,
    )
    return parser


def main(argv=None):
    """CLI main function."""
    parser = build_parser()
    args = parser.parse_args(argv)
    options = RunOptions(
        filenames=args.filename,
        output=args.output,
        format=args.format,
        embed_all_icons=args.embed_all_icons,
        config_files=args.config or [],
        namespace=args.namespace,
        verbose=args.verbose,
        without_namespace=args.without_namespace,
    )
    options.output, options.format = normalize_output_paths(options)
    if options.format not in SUPPORTED_OUTPUT_FORMATS:
        supported_output_formats = "' or '".join(SUPPORTED_OUTPUT_FORMATS)
        print(
            f"Error: '{options.format}' output format unsupported, use '{supported_output_formats}' instead!",
            file=sys.stderr,
        )
        return 1
    if options.embed_all_icons and options.format not in ("svg", "dot_json"):
        print("Warning: --embed-all-icons only works with svg or dot_json output format!")
    run(options)
    return 0
