#!/usr/bin/env python
# encoding: utf-8
"""
tabWorkers.py

Created by Jason Elbourne on 2013-04-15.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

import webapp2

from models import shoppingModels


class CheckTabSubtotalsWorker(webapp2.RequestHandler):
    def post(self):
        urlsafeTabKey = self.request.get('urlsafeTabKey')
        shoppingModels.verify_tab_subtotals(urlsafeTabKey)
