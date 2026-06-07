"""Shared resource models."""


class Resource(dict):
    """Kubernetes resource wrapper carrying source filename metadata."""

    def __init__(self, data, filename):
        super().__init__(data)
        self.filename = filename
