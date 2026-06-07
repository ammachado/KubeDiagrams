"""Node creation helpers."""

from __future__ import annotations

import importlib
import os
from pprint import pprint
import traceback

from diagrams.aws.enablement import ManagedServices
from diagrams.custom import Custom
from diagrams.k8s.group import Namespace

from .models import Resource
from .utils import get_name, get_namespace, query_path, split_node_label


def icon(node, label, size=64):
    """Return an HTML-like label embedding a diagrams icon."""

    class Node(node):
        def __init__(self):
            pass

    icon_path = Node()._load_icon()  # pylint: disable=protected-access
    return (
        '<<table border="0" width="100%"><tr><td fixedsize="true" width="'
        + str(size)
        + '" height="'
        + str(size)
        + '"><img src="'
        + icon_path
        + '" /></td></tr><tr><td>'
        + label
        + "</td></tr></table>>"
    )


def create_diagram_node(resource, config):
    """Create a diagram node from a Kubernetes resource."""
    node_label = split_node_label(get_name(resource))
    tooltip = (
        f"kind: {resource.get('kind')}\n"
        + f"apiVersion: {resource.get('apiVersion')}\n"
        + "metadata:\n"
        + f"  name: {get_name(resource)}\n"
        + "..."
    )
    diagram_node_class = ManagedServices
    node_config = config.get_node_config(resource)
    if node_config is not None:
        custom_icon = node_config.get("custom_icon")
        if custom_icon is not None:
            return Custom(
                node_label,
                os.path.abspath(custom_icon.replace("$KD", config.dirname)),
                tooltip=tooltip,
            )
        diagram_node_classname = node_config.get("diagram_node_classname")
        if diagram_node_classname is not None:
            idx = diagram_node_classname.rfind(".")
            if idx != -1:
                module = importlib.import_module(diagram_node_classname[:idx])
                diagram_node_class = getattr(module, diagram_node_classname[idx + 1 :])
    return diagram_node_class(node_label, tooltip=tooltip)


def create_node_for_role_rules_resource_names(role, nodes, registry, config, diagnostics):
    """Create synthetic resource nodes for role resourceNames rules."""
    for ridx, rule in enumerate(query_path(role, "rules", [])):
        if not isinstance(rule, dict):
            continue
        resource_names = query_path(rule, "resourceNames")
        if resource_names is None:
            continue
        api_groups = query_path(rule, "apiGroups")
        if len(api_groups) != 1:
            diagnostics.error(
                role,
                f"rules[{ridx}]",
                f"Field apiGroups ({api_groups}) should contain only one value",
            )
            continue
        api_group = api_groups[0]
        api_version = "v1" if api_group == "" else f"{api_group}/v1"
        for resource in query_path(rule, "resources", []):
            if "/" in resource:
                continue
            resource_kind = config.plural_to_kinds.get(resource)
            if resource_kind is None:
                continue
            for rnidx, resource_name in enumerate(resource_names):
                if not isinstance(resource_name, str) or "*" in resource_name:
                    continue
                resource_id = (
                    f"{resource_name}/{get_namespace(role, config.default_namespace)}/"
                    f"{resource_kind}/{api_version}"
                )
                if resource_id in registry:
                    continue
                for rule1 in query_path(role, "rules", []):
                    if (
                        api_group in rule1.get("apiGroups", [])
                        and resource in rule1.get("resources", [])
                        and "create" in rule1.get("verbs", [])
                    ):
                        new_node = {
                            "kind": resource_kind,
                            "apiVersion": api_version,
                            "metadata": {
                                "name": resource_name,
                                "namespace": get_namespace(role, config.default_namespace),
                                "labels": query_path(role, "metadata.labels"),
                            },
                        }
                        diagnostics.warning(
                            role,
                            f"rules[{ridx}].resourceNames[{rnidx}]",
                            f"Create {new_node}",
                        )
                        nodes.append(new_node)
                        break


def expand_generated_nodes(registry, process_resource, config, diagnostics):
    """Create additional resources from config node scripts."""

    def internal_create_new_nodes(resource):
        nodes_script = config.get_node_config(resource).get("nodes")
        if nodes_script is None:
            return
        nodes = []
        try:
            exec(  # pylint: disable=exec-used
                nodes_script,
                {},
                {
                    "resource": resource,
                    "nodes": nodes,
                    "query_path": query_path,
                    "create_node_for_role_rules_resource_names": lambda res, target: create_node_for_role_rules_resource_names(
                        res, target, registry, config, diagnostics
                    ),
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            print("Error:", type(exc), ":", exc.args)
            traceback.print_exc()
            print("Nodes script:\n", nodes_script)
            print("Resource:")
            pprint(resource)
            raise
        for node in nodes:
            new_resource = Resource(node, resource.filename)
            process_resource(new_resource)
            internal_create_new_nodes(new_resource)

    for resource in dict(registry).values():
        internal_create_new_nodes(resource)


def apply_namespace_cluster_style(cluster, namespace, is_drawio_format):
    """Apply the standard namespace cluster styling."""
    cluster.graph_attr.update(
        {
            "style": "rounded,dashed",
            "bgcolor": "white",
            "pencolor": "black",
            "label": icon(Namespace, namespace)
            if not is_drawio_format
            else f"Namespace: {namespace}",
        }
    )
