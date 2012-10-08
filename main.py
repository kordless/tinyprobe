#!/usr/bin/env python
##
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'Kord Campbell'
__website__ = 'http://www.tinyprobe.com'

import os,sys

# install third party libraries
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib/externals'))

import webapp2
import config
import routes

"""
import ssl
import logging
import sys
logging.info(sys.version)
logging.info(os.environ)
logging.info("cert_none is %s" % CERT_NONE)
"""

from lib.basehandler import handle_error

app = webapp2.WSGIApplication(debug = os.environ['SERVER_SOFTWARE'].startswith('Dev'), config=config.webapp2_config)

app.error_handlers[403] = handle_error
app.error_handlers[404] = handle_error
if not app.debug:
    app.error_handlers[500] = handle_error
routes.add_routes(app)

