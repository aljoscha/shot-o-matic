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

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.wsgi

from tornado.options import define, options


from shotomatic import app

define("port", default=5000, help="run on the given port", type=int)

def main():
    tornado.options.parse_command_line()
    container = tornado.wsgi.WSGIContainer(app)
    http_server = tornado.httpserver.HTTPServer(container)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
