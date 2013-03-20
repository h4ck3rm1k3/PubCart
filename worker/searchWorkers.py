#!/usr/bin/env python
# encoding: utf-8
"""
searchWorkers.py

Created by Jason Elbourne on 2013-03-15.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import webapp2
import logging

from google.appengine.ext import ndb

from lib import searchDocument

class ProductSearchUpdateHandler(webapp2.RequestHandler):
	def post(self):
		urlsafeProductKey = self.request.get('urlsafeProductKey')
		product = ndb.Key(urlsafe=urlsafeProductKey).get()
		if product:
			params = product.to_dict()
			if params:
				if params.get('sk'):
					del params['sk']
				params['upk'] = urlsafeProductKey
				
				searchDocument.Product.buildProduct(**params)
