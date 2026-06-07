"""Utility helpers."""

from __future__ import annotations

from .constants import MAX_NODE_LABEL_LENGTH, NODE_LABEL_SEPARATORS


def query_path(data, path, default=None):
    """Query nested dictionary values using dot notation."""
    paths = path.split(".")
    for part in paths[:-1]:
        data = data.get(part)
        if data is None:
            return default
    data = data.get(paths[-1])
    if data is None:
        return default
    return data


def get_type(resource):
    """Get the type of a Kubernetes resource, i.e. kind/apiVersion."""
    return query_path(resource, "kind", "kind-NOT-SET") + "/" + query_path(
        resource, "apiVersion", "apiVersion-NOT-SET"
    )


def get_name(resource, diagnostics=None):
    """Get the name of a Kubernetes resource."""
    name = query_path(resource, "metadata.name") or query_path(
        resource, "metadata.generateName"
    )
    if name is None:
        if diagnostics is not None:
            diagnostics.warning(resource, "metadata.name", "Not set or set to null")
        name = "NO-NAME"
        if "metadata" in resource:
            resource["metadata"]["name"] = name
        else:
            resource["metadata"] = {"name": name}
    return name


def get_namespace(resource, default_namespace="default"):
    """Get the namespace of a Kubernetes resource."""
    return query_path(resource, "metadata.namespace", default_namespace)


def split_node_label(node_label):
    """Split node labels into multi-lines."""
    result = ""
    last_pos = 0
    max_pos = len(node_label) - MAX_NODE_LABEL_LENGTH
    while last_pos < max_pos:
        part = node_label[last_pos : last_pos + MAX_NODE_LABEL_LENGTH]
        idx = MAX_NODE_LABEL_LENGTH - 1
        while idx > 0:
            if part[idx] in NODE_LABEL_SEPARATORS:
                part = part[:idx]
                break
            idx -= 1
        result += part
        result += "\n"
        last_pos += len(part)
    result += node_label[last_pos:]
    return result
