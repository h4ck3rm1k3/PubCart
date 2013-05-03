#!/usr/bin/env python
# encoding: utf-8
"""
cartWorkers.py

Created by Jason Elbourne on 2013-03-16.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

import webapp2
import logging

from google.appengine.ext import ndb

from models import userModels


class CreateProductHistoryWorker(webapp2.RequestHandler):
    def post(self):
        try:
            urlsafeProductKey = self.request.get('pk')
            urlsafeUserKey = self.request.get('uk')
            remote_addr = self.request.get('ra')
            user_agent = self.request.get('ua')
            productModel = ndb.Key(urlsafe=urlsafeProductKey).get()
            user_key = ndb.Key(urlsafe=urlsafeUserKey)
            userModels.History.create_event(user_key, productModel.key,
                                            remote_addr,
                                            user_agent)
        except Exception as e:
            logging.error('Error setting user History for product in class ProductRequestHandler : %s' % e)
