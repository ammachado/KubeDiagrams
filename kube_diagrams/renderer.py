"""Diagram rendering."""

from __future__ import annotations

import importlib
import os

import diagrams
from diagrams import Cluster, Edge
from diagrams.aws.enablement import ManagedServices
from diagrams.custom import Custom

from .constants import SUPPORTED_OUTPUT_FORMATS
from .nodes import create_diagram_node, icon
from .utils import query_path, split_node_label


class Diagram(diagrams.Diagram):
    """Enhancement of the Diagram class to add new output formats."""

    __outformats = SUPPORTED_OUTPUT_FORMATS


def create_nodes(cluster, diagram_nodes, config):
    """Create diagram nodes and clusters recursively."""
    for resource_id, resource in cluster.resources.items():
        if config.get_node_config(resource).get("show", True):
            diagram_nodes[resource_id] = create_diagram_node(resource, config)
    for cluster_id, sub_cluster in cluster.clusters.items():
        with Cluster(cluster_id, graph_attr=sub_cluster.graph_attr):
            create_nodes(sub_cluster, diagram_nodes, config)


def create_custom_node(node_id, node_def, diagram_nodes, config):
    """Create a custom node."""
    node_icon = node_def.get("icon")
    node_label = split_node_label(node_def.get("name", ""))
    if node_icon is not None:
        diagram_nodes[node_id] = Custom(
            node_label,
            os.path.abspath(node_icon.replace("$KD", config.dirname)),
            tooltip=node_label,
        )
    else:
        diagram_node_class = ManagedServices
        diagram_node_classname = node_def.get("type")
        if diagram_node_classname is not None:
            idx = diagram_node_classname.rfind(".")
            if idx != -1:
                module = importlib.import_module(diagram_node_classname[:idx])
                diagram_node_class = getattr(module, diagram_node_classname[idx + 1 :])
        diagram_nodes[node_id] = diagram_node_class(node_label, tooltip=node_label)


def create_custom_cluster(cluster_id, cluster_def, diagram_nodes, config, resource_cluster, generate_diagram_in_cluster):
    """Create a custom cluster."""
    cluster_name = query_path(cluster_def, "name")
    cluster_type = query_path(cluster_def, "type")
    graph_attr = {"tooltip": cluster_name, **cluster_def.get("graph_attr", {})}
    if cluster_type:
        idx = cluster_type.rfind(".")
        if idx != -1:
            module = importlib.import_module(cluster_type[:idx])
            diagram_class = getattr(module, cluster_type[idx + 1 :])
            graph_attr["label"] = icon(diagram_class, cluster_name)
    with Cluster(cluster_name, graph_attr=graph_attr):
        create_custom_clusters_nodes(
            cluster_id,
            cluster_def,
            diagram_nodes,
            config,
            resource_cluster,
            generate_diagram_in_cluster,
        )


def create_custom_clusters_nodes(container_id, container_def, diagram_nodes, config, resource_cluster, generate_diagram_in_cluster):
    """Create custom clusters and nodes."""
    prefix_id = container_id + "." if container_id else ""
    for cluster_id, cluster_def in query_path(container_def, "clusters", {}).items():
        create_custom_cluster(
            prefix_id + cluster_id,
            cluster_def,
            diagram_nodes,
            config,
            resource_cluster,
            generate_diagram_in_cluster,
        )
    for node_id, node_def in query_path(container_def, "nodes", {}).items():
        create_custom_node(prefix_id + node_id, node_def, diagram_nodes, config)
    if container_id == generate_diagram_in_cluster:
        create_nodes(resource_cluster, diagram_nodes, config)


def apply_edges(edge_map, diagram_nodes, config, diagnostics):
    """Create diagram edges from the computed edge map."""
    for resource_id, edges in edge_map.items():
        for edge in edges:
            edge_from, edge_to, edge_name = edge
            try:
                if isinstance(edge_name, dict):
                    edge_configuration = edge_name
                else:
                    edge_configuration = config.get_edge_config(edge_name)
                if edge_configuration.get("direction") == "up":
                    _ = diagram_nodes[edge_to] << Edge(**edge_configuration) << diagram_nodes[edge_from]
                else:
                    _ = diagram_nodes[edge_from] >> Edge(**edge_configuration) >> diagram_nodes[edge_to]
            except KeyError as key_error:
                if edge_to in config.cluster_resources():
                    diagnostics.info(
                        {}, None, f"Referenced {edge_to} resource is provided by K8s clusters."
                    )
                    continue
                raise KeyError(f"{key_error} resource not found") from key_error


def render_diagram(processor, edge_map, config, diagnostics, options):
    """Render the final diagram."""
    is_drawio_format = options.format == "drawio"
    output = options.output
    output_format = options.format
    drawio_filename = None
    if is_drawio_format:
        drawio_filename = output
        output = "/tmp/drawio"
        output_format = "dot"
    generate_diagram_in_cluster = query_path(config.diagram_config(), "generate_diagram_in_cluster")
    with Diagram("", filename=output, show=False, direction="TB", outformat=output_format):
        diagram_nodes = {}
        create_custom_clusters_nodes(
            None,
            config.diagram_config(),
            diagram_nodes,
            config,
            processor.resource_cluster,
            generate_diagram_in_cluster,
        )
        apply_edges(edge_map, diagram_nodes, config, diagnostics)
        for edge_idx, custom_edge in enumerate(query_path(config.diagram_config(), "edges", [])):
            custom_edge_from = custom_edge.get("from")
            from_node = diagram_nodes.get(custom_edge_from)
            if from_node is None:
                print(
                    f"Warning: diagram.edges[{edge_idx}].from: Node '{custom_edge_from}' undefined!"
                )
            custom_edge_to = custom_edge.get("to")
            to_node = diagram_nodes.get(custom_edge_to)
            if to_node is None:
                print(
                    f"Warning: diagram.edges[{edge_idx}].to: Node '{custom_edge_to}' undefined!"
                )
            if from_node is not None and to_node is not None:
                edge_tooltip = f"from: {custom_edge_from}\nto: {custom_edge_to}"
                _ = from_node >> Edge(**custom_edge, tooltip=edge_tooltip) >> to_node
    return output, output_format, drawio_filename
