# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org)
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Routines for testing WSGI applications.

Most interesting is app
"""

from libr.webtest.app import TestApp
from libr.webtest.app import TestRequest
from libr.webtest.app import TestResponse
from libr.webtest.app import Form
from libr.webtest.app import Field
from libr.webtest.app import AppError
from libr.webtest.app import Select
from libr.webtest.app import Radio
from libr.webtest.app import Checkbox
from libr.webtest.app import Text
from libr.webtest.app import Textarea
from libr.webtest.app import Hidden
from libr.webtest.app import Submit

from libr.webtest.sel import SeleniumApp
from libr.webtest.sel import selenium
