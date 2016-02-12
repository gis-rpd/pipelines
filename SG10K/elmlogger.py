"""ELM Logging functions
"""

import os
import socket
from datetime import datetime
import subprocess
import json
from collections import OrderedDict
from collections import namedtuple

UnitId = namedtuple('UnitId', ['run_id', 'library_in', 'lane_id'])


def timestamp():
    """returns iso timestamp down to ms"""
    return datetime.now().isoformat()



class ElmLogging(object):
    """
    NOTE:
    - all log lines need all fields
    - one line per runid and lane
    """


    @staticmethod
    def get_hostname():
        return socket.gethostname()


    @staticmethod
    def disk_usage(path):
        """disk usage via du"""
        return int(subprocess.check_output(['du', '-s', path]).split()[0])


    def __init__(self,
                 script_name,# used as logging prefix. can be dummy
                 pipeline_name,
                 pipeline_version,
                 submitter,
                 site,
                 instance_id,
                 log_path,# main logging file                 
                 result_outdir,# where results are stored
                 unit_ids):# list of namedtuples
        """FIXME:add-doc"""

        assert isinstance(unit_ids, list)
        
        elmlogdir = os.getenv('RPD_ELMLOGDIR')
        assert elmlogdir, ("RPD_ELMLOGDIR undefined")

        pipelogdir = os.path.join(elmlogdir, pipeline_name)
        assert os.path.exists(pipelogdir), (
            "pipeline log dir {} doesn't exist".format(pipelogdir))

        # timestamp just a way to make it unique
        logfile = os.path.join(pipelogdir, timestamp() + ".log")
        assert not os.path.exists(logfile)
        self.logfile = logfile

        # only used as logging prefix (not even parsed by ELM)
        self.script_name = script_name
        # required for computing library_file_size
        self.result_outdir = result_outdir

        # json-like values
        self.fields = OrderedDict()
        # caller provided
        self.fields['pipeline_name'] = pipeline_name
        self.fields['pipeline_version'] = pipeline_version
        self.fields['site'] = site
        self.fields['instance_id'] = instance_id
        self.fields['submitter'] = submitter
        self.fields['log_path'] = log_path
        # internally computed
        self.fields['library_file_size'] = None
        self.fields['status_id'] = None

        self.unit_ids = unit_ids

        
    def write_event(self):
        """write logging events to file per unit (yes, that's not intuitive)
        """
        
        with open(self.logfile, 'a') as fh:                
            timestr = datetime.now().strftime('%c')
            for unit_id in self.unit_ids:
                # convert None to 'NA' and all to str
                dump = unit_id._asdict()
                for (k, v) in self.fields.items():
                    assert k not in dump
                    dump[k] = str(v) if v else "NA" 
                jsonstr = json.dumps(dump)
                fh.write('[{}] [{}] [{}] [EVENTLOG] "{}"\n'.format(
                    timestr, self.get_hostname(), self.script_name, jsonstr))


    def start(self):
        """Start ELM logging using config values
        """
        # startup
        self.fields['status_id'] = 5
        self.write_event()


    def stop(self, success):
        """Finalize ELM logging
        """
        if success:
            # done
            self.fields['status_id'] = 6
        else:
            # troubleshooting
            self.fields['status_id'] = 7
        self.fields['library_file_size'] = self.disk_usage(
            self.result_outdir)
        self.write_event()
