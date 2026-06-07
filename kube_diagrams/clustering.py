"""Cluster tree helpers."""


class ResourceCluster:
    """Hierarchical clustering of Kubernetes resources."""

    def __init__(self, name):
        self.name = name
        self.resources = {}
        self.clusters = {}
        self.graph_attr = {"tooltip": name}

    def get_or_create_cluster(self, name):
        cluster = self.clusters.get(name)
        if cluster is None:
            cluster = ResourceCluster(name)
            self.clusters[name] = cluster
        return cluster

    def display(self, ident=0):
        for resource_id in self.resources:
            print("  " * ident, f"- Resource {resource_id}")
        for cluster_id, sub_cluster in self.clusters.items():
            print("  " * ident, f"- {cluster_id}")
            sub_cluster.display(ident + 1)
