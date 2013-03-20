#!/usr/bin/env python
# encoding: utf-8
"""
cartWorkers.py

Created by Jason Elbourne on 2013-03-16.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

import webapp2
import logging

from models import shoppingModels

class CheckCartSubtotalsWorker(webapp2.RequestHandler):
	def post(self):
		urlsafeCartKey = self.request.get('urlsafeCartKey')
		shoppingModels.verify_cart_subtotals(urlsafeCartKey)
