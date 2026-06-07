"""Configuration loading helpers."""

from __future__ import annotations

import copy
import os

import yaml

from .utils import get_type


yaml.SafeLoader.yaml_implicit_resolvers.pop("=")


class Config:
    """Wrapper around raw configuration data."""

    def __init__(self, data, dirname, diagnostics):
        self.data = data
        self.dirname = dirname
        self.diagnostics = diagnostics
        self.already_warned_node_configs = set()
        self.plural_to_kinds = self._build_plural_to_kinds()

    @property
    def default_namespace(self):
        """Return the configured default namespace."""
        return self.data.get("default_namespace", "default")

    def get_edge_config(self, edge_kind):
        """Get diagram edge config."""
        edge_config = self.data.get("edges", {}).get(edge_kind)
        if edge_config is None:
            print(f"Error: {edge_kind} edge configuration not found!")
        return edge_config if edge_config else {}

    def get_node_config_of_resource_type(self, resource_type):
        """Resolve node config for a resource type, including aliases."""
        node_config = self.data.get("nodes", {}).get(resource_type)
        while isinstance(node_config, str):
            node_config = self.data.get("nodes", {}).get(node_config)
        return node_config

    def get_node_config(self, resource):
        """Resolve node config for a resource."""
        resource_type = get_type(resource)
        node_config = self.data.get("nodes", {}).get(resource_type)
        while isinstance(node_config, str):
            if node_config not in self.already_warned_node_configs:
                self.diagnostics.warning(
                    resource, None, f"{resource_type} used instead of {node_config}"
                )
                self.already_warned_node_configs.add(node_config)
            node_config = self.data.get("nodes", {}).get(node_config)
        if node_config is None and resource_type not in self.already_warned_node_configs:
            self.diagnostics.warning(
                resource, None, f"{resource_type} node configuration undefined"
            )
            self.already_warned_node_configs.add(resource_type)
        return node_config if node_config else {}

    def cluster_resources(self):
        """Return configured cluster-provided resources."""
        return self.data["cluster-resources"]

    def clusters(self):
        """Return cluster grouping rules."""
        return self.data.get("clusters", [])

    def diagram_config(self):
        """Return diagram config."""
        return self.data.get("diagram", {})

    def merge_custom_file(self, config_file):
        """Merge a custom config file into the loaded config."""
        with open(config_file, encoding="utf-8") as file_handle:
            custom_config = yaml.safe_load(file_handle)
            if not custom_config:
                return
            if "default_namespace" in custom_config:
                self.data["default_namespace"] = custom_config["default_namespace"]
            if custom_config.get("edges"):
                self.data["edges"].update(custom_config["edges"])
            if custom_config.get("clusters"):
                for cluster_custom_config in custom_config["clusters"]:
                    if "label" in cluster_custom_config:
                        cluster_label = cluster_custom_config["label"]
                        for config_cluster in self.data["clusters"]:
                            if config_cluster.get("label") == cluster_label:
                                config_cluster.update(cluster_custom_config)
                                cluster_label = None
                                break
                        if cluster_label is not None:
                            self.data["clusters"].append(cluster_custom_config)
                    elif "annotation" in cluster_custom_config:
                        cluster_annotation = cluster_custom_config["annotation"]
                        for config_cluster in self.data["clusters"]:
                            if config_cluster.get("annotation") == cluster_annotation:
                                config_cluster.update(cluster_custom_config)
                                cluster_annotation = None
                                break
                        if cluster_annotation is not None:
                            self.data["clusters"].append(cluster_custom_config)
                    else:
                        print("ISSUE on", cluster_custom_config)
            if custom_config.get("nodes"):
                for key, value in custom_config["nodes"].items():
                    previous = self.data["nodes"].get(key)
                    if previous is None:
                        self.data["nodes"][key] = value
                    else:
                        previous.update(value)
            if "diagram" in custom_config:
                self.data["diagram"] = custom_config["diagram"]
            self.plural_to_kinds = self._build_plural_to_kinds()

    def _build_plural_to_kinds(self):
        mapping = {}
        for key, value in self.data["nodes"].items():
            if not isinstance(value, dict):
                continue
            node_kind = key.split("/")[0]
            plural = value.get("plural")
            if plural is None:
                plural = node_kind.lower() + "s"
            mapping[plural] = node_kind
        return mapping


def load_config(options, diagnostics):
    """Load default and custom configuration files."""
    dirname = os.path.dirname(os.path.abspath(__file__))
    base_config_path = os.path.join(os.path.dirname(dirname), "bin", "kube-diagrams.yaml")
    with open(base_config_path, encoding="utf-8") as file_handle:
        config = Config(yaml.safe_load(file_handle), os.path.join(os.path.dirname(dirname), "bin"), diagnostics)
    for config_file in options.config_files:
        config.merge_custom_file(config_file)
    return config
