#!/usr/bin/env python
# encoding: utf-8
"""
paypalHandlers.py

Created by Jason Elbourne on 2013-03-12.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:	 Python Imports
import re
import logging
import httpagentparser

##:	 Webapp2 Imports
import webapp2
from webapp2_extras.i18n import gettext as _

##:	 Google Imports
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.api import memcache
from google.appengine.datastore.datastore_query import Cursor

##:	 BournEE Imports
import forms as forms
from models import shoppingModels, userModels
from lib import bestPrice
from lib import utils
from lib.utils import dollar_float
from lib.bourneehandler import RegisterBaseHandler, BournEEHandler
from lib.exceptions import FunctionException
from lib import paypal_settings as settings

##:	 Boilerplate Imports
from boilerplate import models
from boilerplate.lib.basehandler import user_required
from boilerplate.lib.basehandler import BaseHandler

class PayPalPaymentHandler(BournEEHandler):
	
	@user_required
	def post(self, urlsafeCartKey):
		try:
			if not self.paypalPayment_form.validate():
				raise Exception('paypalPayment_form did not Validate, in function POST of PayPalPaymentHandler')
			
			cart = ndb.Key(urlsafe=urlsafeCartKey).get()
			if cart:
				logging.info('Here')
				(ok, pay) = self.paypal_purchase(cart)
				logging.info('Here')
				if ok:
					logging.info(pay.next_url().encode('ascii'))
					self.redirect( pay.next_url().encode('ascii') ) # go to paypal
				else:
					raise Exception('paypal purchase setup NOT ok, in function POST of PayPalPaymentHandler')
			else:
				raise Exception('Error finding cart using urlsafeCartKey, in function POST of PayPalPaymentHandler')

		except Exception as e:
			logging.error('Error in handler - PayPalPaymentHandler : -- {}'.format(e))
			message = _('An error occurred during the purchase process. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
	
	@webapp2.cached_property
	def paypalPayment_form(self):
		return forms.PaypalPaymentForm(self)


class PaypalReturnHandler(BournEEHandler):

	def get(self, urlsafeCartKey, urlsafePurchaseKey, secret):
		'''user arrives here after purchase'''
		purchase = ndb.Key(urlsafe=urlsafePurchaseKey).get()

		# validation
		if purchase == None: # no key
			self.error(404)

		elif purchase.st != 'CREATED' and purchase.st != 'COMPLETED':
			purchase.std = 'Expected status to be CREATED or COMPLETED, not %s - duplicate transaction?' % purchase.s
			purchase.st = 'ERROR'
			purchase.put()
			self.error(501)

		elif secret != purchase.s:
			purchase.st = 'ERROR'
			purchase.std = 'BuyReturn secret "%s" did not match' % secret
			purchase.put()
			self.error(501)

		else:
			if purchase.st != 'COMPLETED':
				purchase.st = 'RETURNED'
				purchase.put()

			if settings.SHIPPING:
				purchase.sh = paypal.ShippingAddress( purchase.pk, self.request.remote_addr ).raw_response # TODO parse
				purchase.put()

			self.redirect_to('fullPageCart', urlsafeCartKey=urlsafeCartKey)


class PaypalCancelHandler(BournEEHandler):
	def get(self, urlsafeCartKey, urlsafePurchaseKey):
		purchase = ndb.Key(urlsafe=urlsafePurchaseKey).get()
		if purchase.st != 'COMPLETED' or purchase.st != 'RETURNED':
			purchase.st = 'CANCELLED'
			purchase.put()

		self.redirect_to('fullPageCart', urlsafeCartKey=urlsafeCartKey)


class PaypalIPNHandler(BournEEHandler):

	def post(self, urlsafePurchaseKey, secret):
		'''incoming post from paypal'''
		logging.info( "IPN received for %s" % urlsafePurchaseKey )
		ipn = paypal.IPN( self.request )
		if ipn.success():
			# request is paypal's
			purchase = ndb.Key(urlsafe=urlsafePurchaseKey).get()
			cart = purchase.ck.get()
			if secret != purchase.s:
				purchase.st = 'ERROR'
				purchase.std = 'IPN secret "%s" did not match' % secret
				purchase.put()
			# confirm amount
			elif cart.d_st != ipn.amount:
				purchase.st = 'ERROR'
				purchase.std = "IPN amounts didn't match. Item price %f. Payment made %f" % ( cart.d_gt, ipn.amount )
				purchase.put()
			else:
				purchase.st = 'COMPLETED'
				purchase.put()
		else:
			logging.error( "PayPal IPN verify failed: %s" % ipn.error )
			logging.error( "Request was: %s" % self.request.body )