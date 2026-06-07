"""Edge building logic."""

from __future__ import annotations

import json
from pprint import pprint
import traceback

import yaml

from .utils import get_namespace, query_path


class EdgesContext(list):
    """Context provided to edges configuration scripts."""

    def __init__(self, resource_id, resource, registry, config, diagnostics):
        super().__init__()
        self.rid = resource_id
        self.resource = resource
        self.registry = registry
        self.config = config
        self.diagnostics = diagnostics
        self.namespace = get_namespace(resource, config.default_namespace)

    def info(self, path, msg):
        self.diagnostics.info(self.resource, path, msg)

    def warning(self, path, msg):
        self.diagnostics.warning(self.resource, path, msg)

    def error(self, path, msg):
        self.diagnostics.error(self.resource, path, msg)

    def add_edge(self, path, edge, data=None):
        edge_kind = edge[-1]
        if isinstance(edge_kind, str):
            edge_kind = dict(self.config.get_edge_config(edge_kind))
        if "tooltip" not in edge_kind:
            if data is None and path is not None:
                data = query_path(self.resource, path)
            if data is None:
                tooltip = path
            else:
                tooltip = yaml.dump({path: data}, default_flow_style=False)[:-1]
                if len(tooltip) > 16384:
                    tooltip = tooltip[:16380] + "\n..."
            edge_kind["tooltip"] = tooltip
        edge[-1] = edge_kind
        self.append(edge)

    def add_edge_to_rid(self, path, resource_id, edge_kind, data=None):
        if resource_id in self.registry:
            self.add_edge(path, [resource_id, edge_kind], data)
        elif resource_id in self.config.cluster_resources():
            self.info(path, f"'{resource_id}' provided by Kubernetes cluster")
        else:
            self.warning(path, f"'{resource_id}' undefined")

    def add_edge_to(self, path, name, namespace, kind, api_version, edge_kind, data=None):
        if name == ".":
            name = query_path(self.resource, path)
        if name is None:
            return
        if name == "":
            self.warning(path, 'Set to ""')
            return
        if namespace is not None:
            resource_id = f"{name}/{namespace}/{kind}/{api_version}"
        else:
            resource_id = f"{name}/{kind}/{api_version}"
        if not (self.config.get_node_config_of_resource_type(f"{kind}/{api_version}") or {}).get(
            "show", True
        ):
            self.info(path, f"{kind} '{name}' hidden")
        elif resource_id in self.registry:
            self.add_edge(path, [resource_id, edge_kind], data)
        elif resource_id in self.config.cluster_resources():
            self.info(path, f"{kind} '{name}' provided by Kubernetes cluster")
        else:
            self.warning(path, f"{kind} '{name}' undefined")


def build_edges(registry, config, diagnostics):
    """Execute configured edge scripts and return edge map by resource id."""
    edge_map = {}
    for resource_id, resource in registry.items():
        if not config.get_node_config(resource).get("show", True):
            continue
        edges = EdgesContext(resource_id, resource, registry, config, diagnostics)
        code_to_exec = config.get_node_config(resource).get("edges")
        if code_to_exec:
            try:
                exec(  # pylint: disable=exec-used
                    code_to_exec,
                    {},
                    {
                        "resource": resource,
                        "resources": registry,
                        "edges": edges,
                        "query_path": query_path,
                        "get_namespace": lambda res: get_namespace(res, config.default_namespace),
                    },
                )
            except Exception as exc:  # pylint: disable=broad-except
                print("Error:", type(exc), ":", exc.args)
                traceback.print_exc()
                print("Edges script:\n", code_to_exec)
                print("Resource:")
                pprint(resource)
                raise
        for index, edge in enumerate(edges):
            if len(edge) == 2:
                edges[index] = [resource_id, edge[0], edge[1]]
        edge_map[resource_id] = list(edges)
    return edge_map
