# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org)
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Routines for testing WSGI applications.

Most interesting is app
"""

from lib.webtest.app import TestApp
from lib.webtest.app import TestRequest
from lib.webtest.app import TestResponse
from lib.webtest.app import Form
from lib.webtest.app import Field
from lib.webtest.app import AppError
from lib.webtest.app import Select
from lib.webtest.app import Radio
from lib.webtest.app import Checkbox
from lib.webtest.app import Text
from lib.webtest.app import Textarea
from lib.webtest.app import Hidden
from lib.webtest.app import Submit

from lib.webtest.sel import SeleniumApp
from lib.webtest.sel import selenium
