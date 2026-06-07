"""Shared constants for KubeDiagrams."""

# All dot output formats are listed in https://graphviz.org/docs/outputs/
# If you need a format not listed below, just add it below.
SUPPORTED_OUTPUT_FORMATS = (
    "dot",
    "dot_json",
    "drawio",
    "gif",
    "jp2",
    "jpe",
    "jpeg",
    "jpg",
    "pdf",
    "png",
    "svg",
    "tif",
    "tiff",
)

MAX_NODE_LABEL_LENGTH = 16
NODE_LABEL_SEPARATORS = [" ", ":", "-", "."]
