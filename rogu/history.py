"""history provides the resource history functionality for Rogu.

"""
import os
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path

import config


# ------------------------------------------------------------------------------
# HISTORY FILE

class _HistoryManager:
    buf_size = 8192

    def __init__(self, path):
        self.path = path
        self._file = None

    def __iter__(self):
        """Iterate over the lines in the history file in reverse order,
        yielding latest entries first.
        """

        self._file.seek(0, os.SEEK_END)
        pos = self._file.tell()
        buffer = bytearray()

        while pos > 0:
            # Calculate how much to read in this iteration
            read_size = min(self.buf_size, pos)
            pos -= read_size

            # Read a chunk of the file
            self._file.seek(pos, os.SEEK_SET)
            chunk = self._file.read(read_size)

            # Prepend the chunk to the buffer
            buffer[:0] = chunk

            # Split the buffer into lines and yield them in reverse order
            while b'\n' in buffer:
                buffer, _, line = buffer.rpartition(b'\n')
                if line:
                    yield line.decode('utf-8')

        # Yield any remaining content in the buffer
        if buffer:
            yield buffer.decode('utf-8')

    @contextmanager
    def reader(self):
        """Context manager returning a CSV reader for the history file.

        The file is opened in read-only mode and closed when the context
        is exited.
        """
        import csv

        assert self._file is None, 'History file already open'

        if not self.path.exists():
            self.path.touch()

        try:
            self._file = open(self.path, 'rb')
            yield csv.reader(self, dialect='unix')
        finally:
            self._file.close()
            self._file = None

    @contextmanager
    def writer(self):
        """Context manager returning a CSV writer for the history file.

        The file is opened in append mode and closed when the context
        is exited.
        """
        import csv
        assert self._file is None, 'History file already open'
        with open(self.path, 'a') as f:
            yield csv.writer(f, dialect='unix')


# ------------------------------------------------------------------------------
# HISTORY INTERFACE

Entry = namedtuple('Entry', [
    'timestamp',
    'ok',
    'action',
    'name',
    'path',
    'uri',
    'key',
    'short_key',
    'local_hash',
    'message'
])

history_file = Path(config.app_dir) / 'rogu-history.csv'
_manager = _HistoryManager(history_file)


def record(action, resource, ok, message):
    """Record an action in the history file."""
    import arrow

    entry = Entry(
        timestamp=arrow.now(),
        ok=ok,
        action=action,
        name=str(resource),
        path=resource.short_path,
        uri=resource.uri,
        key=resource.key,
        short_key=resource.short_key,
        local_hash=resource.local_hash,
        message=message
    )

    with _manager.writer() as wr:
        wr.writerow(entry)


def _row_to_entry(row):
    import arrow
    timestamp, ok, *rest = row
    timestamp = arrow.get(timestamp)
    ok = ok == 'True'
    return Entry(timestamp, ok, *rest)


def entries(n=None):
    """Yield all history entries, the latest first.
    This includes both ok and failed entries.

    If n is given, only the last n entries are yielded.
    """
    with _manager.reader() as rd:
        for i, row in enumerate(rd):
            if n and i >= n:
                break
            yield _row_to_entry(row)


def resource_entries(resource, n=None):
    """Yield all ok history entries for the given resource.
    The latest first.

    If n is given, only the last n entries are yielded.
    """
    with _manager.reader() as rd:
        entries = (
            entry
            for entry in map(_row_to_entry, rd)
            if entry.ok and entry.key == resource.key
        )
        for i, entry in enumerate(entries):
            if n and i >= n:
                break
            yield entry
