#!/usr/bin/env python

# virtualenv stuff
# activate the virtual env in directory env if
# it exists
import os
activate_this = "env/bin/activate_this.py"
if os.path.exists(activate_this):
    execfile(activate_this, dict(__file__=activate_this))

from shotomatic import app
from gevent import wsgi

if __name__ == "__main__":
    server = wsgi.WSGIServer(('', 5000), app, spawn=None)
    server.serve_forever()
