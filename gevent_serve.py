#!/usr/bin/env python
#
# Adapted from the tornade0.2 example directory

# virtual env stuff
import os
import site
import sys
proj_root = os.path.dirname(__file__)
site_packages = os.path.join(proj_root, 'env/lib/python2.6/site-packages')
site.addsitedir(os.path.abspath(site_packages))
sys.path.insert(0, proj_root)

from shotomatic import app
from gevent import wsgi

if __name__ == "__main__":
    server = wsgi.WSGIServer(('', 5000), app, spawn=None)
    server.serve_forever()
