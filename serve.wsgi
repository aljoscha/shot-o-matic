import os
import site
import sys
proj_root = os.path.dirname(__file__)
site_packages = os.path.join(proj_root, 'env/lib/python2.5/site-packages')
site.addsitedir(os.path.abspath(site_packages))
sys.path.insert(0, proj_root)

from shotomatic import app as application
