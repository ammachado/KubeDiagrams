"""Manifest loading and resource indexing."""

from __future__ import annotations

import copy

import yaml

from .clustering import ResourceCluster
from .models import Resource
from .nodes import apply_namespace_cluster_style
from .registry import ResourceRegistry
from .utils import get_name, get_namespace, get_type, query_path


class ResourceProcessor:
    """Process and index resources into registry and cluster tree."""

    def __init__(self, options, config, diagnostics):
        self.options = options
        self.config = config
        self.diagnostics = diagnostics
        self.registry = ResourceRegistry()
        self.resource_cluster = ResourceCluster("ROOT")
        self.is_drawio_format = options.format == "drawio"

    def process_resource(self, resource):
        cluster = self.resource_cluster
        name = get_name(resource, self.diagnostics)
        resource_scope = self.config.get_node_config(resource).get("scope")
        if self.options.namespace is not None and (
            resource_scope != "Namespaced"
            or get_namespace(resource, self.config.default_namespace) != self.options.namespace
        ):
            return

        if resource_scope in ("Outside", "Cluster"):
            resource_id = name + "/" + get_type(resource)
        else:
            namespace = get_namespace(resource, self.config.default_namespace)
            resource_id = name + "/" + namespace + "/" + get_type(resource)
            if not self.options.without_namespace:
                cluster = self.resource_cluster.get_or_create_cluster(
                    f"Namespace: {namespace}"
                )
                apply_namespace_cluster_style(cluster, namespace, self.is_drawio_format)

        if resource_id not in self.registry:
            self.registry[resource_id] = resource
        else:
            self.diagnostics.error(
                resource, None, f"Already declared in {self.registry[resource_id].filename}"
            )

        cluster = self._process_clusters(
            cluster, resource, copy.deepcopy(self.config.clusters())
        )
        cluster.resources[resource_id] = resource

    def _process_clusters(self, cluster, resource, cluster_configs):
        for cluster_config in cluster_configs:
            if cluster_config.get("show", True) is False:
                continue
            if "annotation" in cluster_config:
                annotation = cluster_config["annotation"]
                annotations = query_path(resource, "metadata.annotations")
                if isinstance(annotations, dict) and annotation in annotations:
                    cluster_name = cluster_config["title"].format(annotations[annotation])
                    cluster = cluster.get_or_create_cluster(cluster_name)
                    cluster.graph_attr.update(cluster_config.get("graph_attr", {}))
                    cluster_configs.remove(cluster_config)
                    return self._process_clusters(cluster, resource, cluster_configs)
            elif "label" in cluster_config:
                label = cluster_config["label"]
                labels = query_path(resource, "metadata.labels")
                if isinstance(labels, dict) and label in labels:
                    cluster_name = cluster_config["title"].format(labels[label])
                    cluster = cluster.get_or_create_cluster(cluster_name)
                    cluster.graph_attr.update(cluster_config.get("graph_attr", {}))
                    cluster_configs.remove(cluster_config)
                    return self._process_clusters(cluster, resource, cluster_configs)
        return cluster


def load_resources(options, config, diagnostics):
    """Load manifest files and build the resource registry and cluster tree."""
    processor = ResourceProcessor(options, config, diagnostics)
    for filename in options.filenames:
        try:
            with open(0 if filename == "-" else filename, encoding="utf-8") as file_handle:
                print(f"Load {'from stdin' if filename == '-' else filename}...")
                for yaml_data in yaml.safe_load_all(file_handle):
                    if yaml_data is None:
                        continue
                    if yaml_data.get("kind", "NO-KIND").endswith("List") and "items" in yaml_data:
                        for resource in yaml_data["items"]:
                            processor.process_resource(Resource(resource, filename))
                    else:
                        processor.process_resource(Resource(yaml_data, filename))
        except FileNotFoundError:
            print(f"Error: file '{filename}' not found!")
            if len(options.filenames) == 1:
                raise SystemExit(1) from None
        except yaml.scanner.ScannerError as error:
            print("Error: " + str(error).replace("\n", " ") + "!")
        except yaml.constructor.ConstructorError as error:
            print("Error: " + str(error).replace("\n", " ") + "!")

    if options.verbose:
        print("Loaded Kubernetes resources:")
        processor.resource_cluster.display()

    return processor
