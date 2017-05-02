#!/usr/bin/env python3
"""Starter flag files
"""

#--- standard library imports
#
import os

#--- third party imports
#
#/ should be none, to be callable from any shell script with python3 without problem

#--- project specific imports
#
# should be as simple as possible
from utils import generate_timestamp
from utils import timestamp_from_string


class StarterFlag(object):
    """Flag files indicating analysis start
    """

    pattern = "STARTER_FLAG.{timestamp}"


    def __init__(self, filename=None):
        """
        """

        if filename:
            self.read(filename)
        else:
            self.filename = None
            self.timestamp = None
            self.dbid = None


    def _timestamp_from_filename(self, filename):
        """Get timestamp from filename
        """

        tstr = os.path.basename(filename).replace(
            self.pattern.format(timestamp=""), "")
        return timestamp_from_string(tstr)


    def read(self, filename):
        """Read flag file (timestamp and dbid)
        """
        self.filename = filename
        self.timestamp = self._timestamp_from_filename(self.filename)
        with open(self.filename, 'r') as fh:
            self.dbid = fh.read().encode().decode()


    def write(self, dirname, dbid, timestamp=None):
        """Write starter flag file
        """

        if not timestamp:
            timestamp = generate_timestamp()
        self.timestamp = timestamp
        self.dbid = dbid
        self.filename = os.path.join(dirname, self.pattern.format(timestamp=self.timestamp))

        assert not os.path.exists(self.filename), (
            "StartFlag {} already exists".format(self.filename))
        with open(self.filename, 'w') as fh:
            fh.write(dbid)

