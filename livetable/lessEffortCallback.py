"""
Best Effort Callback.
For instructions on how to test in a simulated environment please see:
    tests/interactive/best_effort_cb.py
"""

import logging
import sys
import time
from datetime import datetime
from io import StringIO
from warnings import warn


from bluesky.callbacks.core import LiveTable, make_class_safe, CallbackBase

logger = logging.getLogger(__name__)


def hinted_fields(descriptor):
    # Figure out which columns to put in the table.
    obj_names = list(descriptor["object_keys"])
    # We will see if these objects hint at whether
    # a subset of their data keys ('fields') are interesting. If they
    # did, we'll use those. If these didn't, we know that the RunEngine
    # *always* records their complete list of fields, so we can use
    # them all unselectively.
    columns = []
    for obj_name in obj_names:
        try:
            fields = descriptor.get("hints", {}).get(obj_name, {})["fields"]
        except KeyError:
            fields = descriptor["object_keys"][obj_name]
        columns.extend(fields)
    return columns


@make_class_safe(logger=logger)
class LessEffortCallback(CallbackBase):
    def __init__(
        self,
        *,
        fig_factory=None,
        table_enabled=True,
        out=print,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # internal state
        self._start_doc = None
        self._descriptors = {}
        self._table = None
        self._heading_enabled = True
        self._table_enabled = table_enabled
        self._baseline_enabled = True
        self._out = out
        self._cleanup_motor_heuristic = False
        self._stream_names_seen = set()
        self._started = False

        # hack to handle the bottom border of the table
        self._buffer = StringIO()
        self._baseline_toggle = True

    @property
    def baseline_enabled(self):
        """Whether baseline readings are printed."""
        return self._baseline_enabled

    @baseline_enabled.setter
    def baseline_enabled(self, enabled):
        """Enable or disable baseline readings."""
        self._baseline_enabled = bool(enabled)

    def enable_heading(self):
        "Print timestamp and IDs at the top of a run."
        self._heading_enabled = True

    def disable_heading(self):
        "Opposite of enable_heading()"
        self._heading_enabled = False

    def enable_table(self):
        "Print hinted readings from the 'primary' stream in a LiveTable."
        self._table_enabled = True

    def disable_table(self):
        "Opposite of enable_table()"
        self._table_enabled = False

    def __call__(self, name, doc, *args, **kwargs):
        if not (self._table_enabled or self._baseline_enabled):
            return
        super().__call__(name, doc, *args, **kwargs)

    def start(self, doc):
        self.clear()
        print("Start Doc Received")
        self._start_doc = doc
        self.plan_hints = doc.get("hints", {})

        # Prepare a guess about the dimensions (independent variables) in case
        # we need it.
        motors = self._start_doc.get("motors")
        if motors is not None:
            GUESS = [([motor], "primary") for motor in motors]
        else:
            GUESS = [(["time"], "primary")]

        # Ues the guess if there is not hint about dimensions.
        dimensions = self.plan_hints.get("dimensions")
        if dimensions is None:
            self._cleanup_motor_heuristic = True
            dimensions = GUESS

        # We can only cope with all the dimensions belonging to the same
        # stream unless we resample. We are not doing to handle that yet.
        if len(set(d[1] for d in dimensions)) != 1:  # noqa: C401
            self._cleanup_motor_heuristic = True
            dimensions = GUESS  # Fall back on our GUESS.
            warn(
                "We are ignoring the dimensions hinted because we cannot "
                "combine streams."
            )  # noqa: B028

        # for each dimension, choose one field only
        # the plan can supply a list of fields. It's assumed the first
        # of the list is always the one plotted against
        self.dim_fields = [fields[0] for fields, stream_name in dimensions]

        # make distinction between flattened fields and plotted fields
        # motivation for this is that when plotting, we find dependent variable
        # by finding elements that are not independent variables
        self.all_dim_fields = [
            field for fields, stream_name in dimensions for field in fields
        ]

        _, self.dim_stream = dimensions[0]

        # Print heading.
        tt = datetime.fromtimestamp(self._start_doc["time"]).utctimetuple()
        if self._heading_enabled:
            self._out(
                "\n\nTransient Scan ID: {0}     Time: {1}".format(  # noqa: UP030
                    self._start_doc.get("scan_id", ""),
                    time.strftime("%Y-%m-%d %H:%M:%S", tt),
                )
            )
            self._out(
                "Persistent Unique Scan ID: '{0}'".format(self._start_doc["uid"])
            )  # noqa: UP030
        self._started = True

    def descriptor(self, doc):
        if not self._started:
            return
        self._descriptors[doc["uid"]] = doc
        stream_name = doc.get("name", "primary")  # fall back for old docs

        if stream_name not in self._stream_names_seen:
            self._stream_names_seen.add(stream_name)
            if self._table_enabled:
                self._out(f"New stream: {stream_name!r}")

        columns = hinted_fields(doc)

        # ## This deals with old documents. ## #
        if stream_name == "primary" and self._cleanup_motor_heuristic:
            # We stashed object names in self.dim_fields, which we now need to
            # look up the actual fields for.
            self._cleanup_motor_heuristic = False
            fixed_dim_fields = []
            for obj_name in self.dim_fields:
                # Special case: 'time' can be a dim_field, but it's not an
                # object name. Just add it directly to the list of fields.
                if obj_name == "time":
                    fixed_dim_fields.append("time")
                    continue
                try:
                    fields = doc.get("hints", {}).get(obj_name, {})["fields"]
                except KeyError:
                    fields = doc["object_keys"][obj_name]
                fixed_dim_fields.extend(fields)
            self.dim_fields = fixed_dim_fields

        # Ensure that no independent variables ('dimensions') are
        # duplicated here.
        columns = [c for c in columns if c not in self.all_dim_fields]

        # ## TABLE ## #
        if stream_name == self.dim_stream:
            if self._table_enabled:
                # plot everything, independent or dependent variables
                self._table = LiveTable(
                    list(self.all_dim_fields) + columns,
                    separator_lines=False,
                    out=self._out,
                )
                self._table("start", self._start_doc)
                self._table("descriptor", doc)

    def event(self, doc):
        if not self._started:
            return
        descriptor = self._descriptors[doc["descriptor"]]
        if descriptor.get("name") == "primary":
            if self._table is not None:
                self._table("event", doc)

        # Show the baseline readings.
        if descriptor.get("name") == "baseline":
            columns = hinted_fields(descriptor)
            self._baseline_toggle = not self._baseline_toggle
            if self._baseline_enabled:
                border = "+" + "-" * 32 + "+" + "-" * 32 + "+"
                if self._baseline_toggle:
                    print("End-of-run baseline readings:", file=self._buffer)
                    print(border, file=self._buffer)
                else:
                    self._out("Start-of-run baseline readings:")
                    self._out(border)
                for k, v in doc["data"].items():
                    if k not in columns:
                        continue
                    if self._baseline_toggle:
                        print(f"| {k:>30} | {v:<30} |", file=self._buffer)
                    else:
                        self._out(f"| {k:>30} | {v:<30} |")
                if self._baseline_toggle:
                    print(border, file=self._buffer)
                else:
                    self._out(border)

    def stop(self, doc):
        if not self._started:
            return
        if self._table is not None:
            self._table("stop", doc)

        if self._baseline_enabled:
            # Print baseline below bottom border of table.
            self._buffer.seek(0)
            self._out(self._buffer.read())
            self._out("\n")
        self._started = False

    def clear(self):
        self._start_doc = None
        self._descriptors.clear()
        self._stream_names_seen.clear()
        self._table = None
        self._buffer = StringIO()
        self._baseline_toggle = True
