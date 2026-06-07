"""Output post-processing helpers."""

from __future__ import annotations

import base64
import os
import re
import subprocess
from pathlib import Path

import diagrams


def normalize_output_paths(options):
    """Normalize output name and format the same way as the legacy script."""
    output = options.output
    output_format = options.format
    if output is None:
        output = options.filenames[0][: options.filenames[0].rfind(".")]
    else:
        dot_idx = output.rfind(".")
        if dot_idx != -1:
            output_format = output[dot_idx + 1 :]
            output = output[:dot_idx]
    return output, output_format


def convert_drawio(temp_output, temp_format, drawio_filename):
    """Convert dot output into drawio."""
    command = [
        "graphviz2drawio",
        f"{temp_output}.{temp_format}",
        "-o",
        f"{drawio_filename}.drawio",
    ]
    print(f"Executing {' '.join(command)}...")
    subprocess.run(command, check=False)
    os.remove(f"{temp_output}.{temp_format}")
    print(f"{drawio_filename}.drawio generated.")


def postprocess_icon_paths(output, output_format, embed_all_icons, script_dirname):
    """Rewrite image paths in svg/dot_json outputs."""
    if output_format not in ("svg", "dot_json"):
        return
    filename = f"{output}.{output_format}"
    print("Post-process paths of icons...")
    with open(filename, "rt", encoding="utf-8") as file_stream:
        lines = file_stream.readlines()
    diagrams_path = str(Path(os.path.abspath(os.path.dirname(diagrams.__file__))).parent)
    diagrams_url = "https://raw.githubusercontent.com/mingrammer/diagrams/refs/heads/master"
    kubediagrams_path = str(Path(os.path.abspath(script_dirname)).parent)
    kubediagrams_url = "https://raw.githubusercontent.com/philippemerle/KubeDiagrams/refs/heads/main"
    if output_format == "svg":
        what_to_search = [r'image xlink:href="([^"]+)"']
    else:
        diagrams_path = diagrams_path.replace("/", "\\/")
        kubediagrams_path = kubediagrams_path.replace("/", "\\/")
        what_to_search = [r'"image": "([^"]+)"', r'img src=\\"([^"]+)\\"']
    with open(filename, "wt", encoding="utf-8") as file_stream:
        for line in lines:
            for pattern in what_to_search:
                img_paths = re.findall(pattern, line)
                for img_path in img_paths:
                    if not embed_all_icons:
                        if diagrams_path in line:
                            line = line.replace(diagrams_path, diagrams_url)
                            continue
                        if kubediagrams_path in line:
                            line = line.replace(kubediagrams_path, kubediagrams_url)
                            continue
                    full_img_path = Path(img_path.replace("\\/", "/"))
                    if full_img_path.exists():
                        with open(full_img_path, "rb") as img_file:
                            img_data = img_file.read()
                        mime_type = "image/png"
                        b64_data = base64.b64encode(img_data).decode("ascii")
                        data_uri = f"data:{mime_type};base64,{b64_data}"
                        line = line.replace(img_path, data_uri)
                    else:
                        print(f"Warning: Image not found: {full_img_path}")
            file_stream.write(line)
    print(f"{filename} saved.")
