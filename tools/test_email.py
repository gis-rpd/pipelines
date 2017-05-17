#!/usr/bin/env python3
"""
FIXME:add-doc
"""

#--- standard library imports
#
import sys
import os

#--- third-party imports
#
#/

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import send_mail
from pipelines import get_site
from pipelines import get_pipeline_version


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"
               

def main(toaddr):
    subject = "Test email from {} version {}".format(
        get_site(), get_pipeline_version())
    body = "Email wursts.\n\nSincerely,\nRPD"
    send_mail(subject, body, toaddr=toaddr, ccaddr=None, pass_exception=False)
    
    
if __name__ == "__main__":
    assert len(sys.argv)==2, ("Need email address as only argument")
    toaddr = sys.argv[1]
    main(toaddr)
            
