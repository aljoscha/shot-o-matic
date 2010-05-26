#!/usr/bin/env python
"""
Upload a screenshot to the specified shot-O-matic website
Example usage:
    ./upload_screenshot.py http://shots.foo/upload /path/to/file admin default

"""
import sys

import pycurl

if __name__ == "__main__":
    url = sys.argv[1]
    filename = sys.argv[2]
    username = sys.argv[3]
    password = sys.argv[4]
    print "Uploading {0} to {1}".format(filename, url)
    c = pycurl.Curl()
    c.setopt(c.POST, 1)
    c.setopt(c.URL, url)
    c.setopt(c.HTTPPOST, [("screenshot", (c.FORM_FILE, filename)),
                          ("username", (c.FORM_CONTENTS, username)),
                          ("password", (c.FORM_CONTENTS, password)),
                          ])
    c.setopt(c.VERBOSE, 0)
    c.perform()
    c.close()
    print "\nDone."
