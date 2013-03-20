#!/usr/bin/env python
# encoding: utf-8
"""
parserWorkers.py

Created by Jason Elbourne on 2013-03-15.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import webapp2
from lib import parsers


class CreateProductTierPriceModel(webapp2.RequestHandler):
	def post(self):
		urlsafeProductKey = self.request.get('urlsafeProductKey')
		parsers.parseDigiKey(urlsafeProductKey)