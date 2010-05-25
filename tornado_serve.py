#!/usr/bin/env python

# virtualenv stuff
# activate the virtual env in directory env if
# it exists
import os
activate_this = "env/bin/activate_this.py"
if os.path.exists(activate_this):
    execfile(activate_this, dict(__file__=activate_this))

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.wsgi
from tornado.options import define, options

from shotomatic import app

if __name__ == "__main__":
    define("port", default=5000, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    container = tornado.wsgi.WSGIContainer(app)
    http_server = tornado.httpserver.HTTPServer(container)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
