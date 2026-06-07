"""Resource registry and lookup helpers."""

from __future__ import annotations

from .utils import query_path


class ResourceRegistry(dict):
    """Central store for resources."""

    def owned_by(self, owner_resource):
        """Return resources owned by the supplied resource."""
        result = []
        uid = query_path(owner_resource, "metadata.uid")
        for resource in self.values():
            for owner_reference in query_path(resource, "metadata.ownerReferences", []):
                if owner_reference.get("uid") == uid:
                    result.append(resource)
        return result
