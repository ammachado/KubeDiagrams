"""Options used to run KubeDiagrams."""

from dataclasses import dataclass, field


@dataclass
class RunOptions:
    """Runtime options for diagram generation."""

    filenames: list[str]
    output: str | None = None
    format: str = "png"
    embed_all_icons: bool = False
    config_files: list[str] = field(default_factory=list)
    namespace: str | None = None
    verbose: bool = False
    without_namespace: bool = False
