"""Diagnostics and user-facing reporting."""

from __future__ import annotations

from .utils import get_name, query_path

REPORT_COLORS = {
    "Info": "\33[0m",
    "Warning": "\33[33m",
    "Error": "\33[31m",
}


class Diagnostics:
    """Collects and prints diagnostics."""

    def __init__(self):
        self._report_reentrance = True

    def report(self, kind, resource, path, msg, end):
        """Emit a diagnostic message."""
        if not self._report_reentrance:
            return
        self._report_reentrance = False
        report_message = (
            f"{REPORT_COLORS[kind]}[{kind}] "
            + query_path(resource, "kind", "NO-KIND")
            + ":"
            + get_name(resource, self)
        )
        if path is not None:
            report_message += f":{path}"
        report_message += f" - {msg}{end}\33[0m"
        print(report_message)
        self._report_reentrance = True

    def info(self, resource, path, msg):
        """Report an info message."""
        self.report("Info", resource, path, msg, ".")

    def warning(self, resource, path, msg):
        """Report a warning message."""
        self.report("Warning", resource, path, msg, "!")

    def error(self, resource, path, msg):
        """Report an error message."""
        self.report("Error", resource, path, msg, "!")
