#!/usr/bin/env python
# encoding: utf-8
"""
test_helpers.py

Created by Jason Elbourne on 2013-01-25.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import logging
import webapp2
import re

from webapp2_extras import auth
from google.appengine.ext import ndb

from models import shoppingModels, userModels
from libr import bestPrice
from libr.parsers import createProductPriceTier
from libr.BeautifulSoup import BeautifulSoup
from boilerplate import models as boilerplate_models



class HandlerHelpers():
	
	def getProductPriceTiers_withoutURLOPEN(self, product):
		productModel = product
		productNumber = str('AVE106M16B12T-F')
		priceTiers = {'1':15,'10':15,'100':12,'250':11,'500':9,'1000':9,'2500':9,'5000':9,'10000':9}
		parsedData = parsedData = {	'ppp':5,'pp':0,'m':product.m,'pn':product.pn,'d':product.d, \
						'ot':product.ot,'mt':product.mt,'pc':product.pc,'sdp':product.sdp,'p':product.p,'qa':product.qa, \
						'mq':product.mq, 'up':15,'meq':100,'mep':12,'rep':12,'highest_qnt':500, \
						'lp':9, 'dkl':'http://www.digikey.ca/product-detail/en/AVE106M16B12T-F/338-1794-1-ND/2096324', \
						'img':'http://media.digikey.com/Photos/Cornell%20Dubilier%20Photos/AVE4-SERIES.jpg', \
						'ds':'http://www.cde.com/catalogs/AVE.pdf', 'priceTiers':priceTiers,\
						}
		productPriceTiers = createProductPriceTier(productModel, productNumber, parsedData)
		if productPriceTiers:
			return productPriceTiers
		else:
			self.fail("createProductPriceTier failed during function getProductPriceTiers_withoutURLOPEN")
			
		
	def getTestProduct(self):
		self.testapp.reset()
		product, best_price = bestPrice.getBestPrice(None, str('AVE106M16B12T-F'), int(1))
		if product:
			productPriceTiers = self.getProductPriceTiers_withoutURLOPEN(product)
			return product, best_price, productPriceTiers
		else:
			self.fail("getBestPrice failed during function getTestProduct")

	def deleteTestProduct(self):
		sellerKey = ndb.Key(userModels.Seller, 1)
		product = shoppingModels.Product.get_by_pn('AVE106M16B12T-F', sellerKey)
		if product:
			productKey = product.key
			productKey.delete()
			product = shoppingModels.Product.get_by_pn('AVE106M16B12T-F', sellerKey)
			if product:
				self.fail("deleteTestProduct failed, Did not delete Product")
		else:
			self.fail("deleteTestProduct failed, Did not find Product before deleting it.")

	def getTestWatchlist(self):
		try:
			userKey = ndb.Key(userModels.User, 1)
			sellerKey = ndb.Key(userModels.Seller, 1)
			##: Check for existing WatchListItem Model
			watchlist = shoppingModels.Watchlist.get_default_for_user(userKey)
			productKey = ndb.Key(shoppingModels.Product, "AVE106M16B12T-F", sellerKey)
			if watchlist:
				L = watchlist.pl
				if productKey not in L:
					L.append(productKey) ##: append the productKey (NOT urlsafe)
					watchlist.pl = L
				wl_key = watchlist.put()
			else:
				##: Create the Watchlist Item
				watchlist = shoppingModels.Watchlist(
							uk = userKey, ##: User Model Key
							n = str('ALL'), ##: Watchlist Name
							pl = [productKey], ##: Product List (NOT urlsafe)
							)
				wl_key = watchlist.put()
			return wl_key.urlsafe(), productKey.urlsafe()
		except Exception as e:
			logging.error("Could not get Test Watchlist: {}".format(e))
			self.fail("Could not get Test Watchlist: {}".format(e))

	def getTestOrder(self, cartName="SHOPPING"):
		try:
			userKey = ndb.Key(userModels.User, 1)
			sellerKey = ndb.Key(userModels.Seller, 1)
			
			cart = shoppingModels.Cart.get_for_UserKey(userKey, name=str(cartName), public=False)
			order = None
			
			if cart:
				order = ndb.Key(shoppingModels.Order, 'AVE106M16B12T-F', parent=cart.key).get()
				if not order:
					logging.info('Creating a New Order')
					try:
						order = shoppingModels.Order(
									pk = ndb.Key(shoppingModels.Product, "AVE106M16B12T-F", parent=sellerKey), ##: Product Model Key
									ck = cart.key, ##: Cart Model Key
									pn = str('AVE106M16B12T-F'), ##: Manufacturer Product Number
									q = int(1), ##: Quantity for Order
									)
						order_key = order.put()
					except Exception as e:
						logging.error("Failed while creating Order: {}".format(e))
						self.fail("Failed while creating Order: {}".format(e))
				#
				if order.key not in cart.okl:
					logging.info("order_key not in cart.okl, so we now add it in")
					cart.okl.append(order_key) ##: If Order Key is not in the Cart's List append to the Cart List
				
				if order.pn:
					if order.pn not in cart.pnl:
						logging.info("order Product Number not in cart.pnl, so we now add it in")
						cart.pnl.append(order.pn) ##: If Order Product Number is not in the Cart's List append to the Cart List

				logging.info("Begin updating the cart pricing info with new order details")
				tax_perc = float(cart.txrp)/100
				old_order_subtotal = 0
				cart.st += (int(order.st)-int(old_order_subtotal)) ##: Sub-Total Cost (Cents)
				cart.tx = int(((float(cart.st)/100) * float(tax_perc))*100)
				cart.sh = 0 ##: Not known at this time
				cart.mu = int((( ( (float(cart.st)/100) + (float(cart.tx)/100) )*0.05)+0.3)*100)
				if cart.mu == 30:
					cart.mu = 0
				cart.gt = int(cart.st)+int(cart.tx)+int(cart.mu)+int(cart.sh)
				cart_key = cart.put()

			return order, cart
			
		except Exception as e:
			logging.error("Could not get Cart or Order: {}".format(e))
			self.fail("Could not get Cart or Order: {}".format(e))
			
			

	def get(self, *args, **kwargs):
		"""Wrap webtest get with nicer defaults"""
		if 'headers' not in kwargs:
			kwargs['headers'] = self.headers
		if 'status' not in kwargs:
			kwargs['status'] = 200
		return self.testapp.get(*args, **kwargs)

	def post(self, *args, **kwargs):
		"""Wrap webtest post with nicer defaults"""
		if 'headers' not in kwargs:
			kwargs['headers'] = self.headers
		return self.testapp.post(*args, **kwargs)

	def get_form(self, url, form_id, params={}, expect_fields=None):
		"""Load the page and retrieve the form by id"""
		response = self.get(url, params)
		#logging.error('Body = {}'.format(response.body))
		if response.forms:
			forms_msg = "Found forms: " + ", ".join([f for f in response.forms.keys() if isinstance(f, unicode)])
		else:
			forms_msg = 'No forms found.'
		self.assertIn(form_id, response.forms, "form {} not found on the page {}. {}"
						.format(form_id, url, forms_msg))
		form = response.forms[form_id]
		if expect_fields:
			form_fields = form.fields.keys()
			for special_field in ('_csrf_token', None):
				try:
					form_fields.remove(special_field)
				except ValueError:
					pass
			self.assertListEqual(form_fields, expect_fields)
		return form

	def submit(self, form, expect_error=False, error_message='', error_field='', success_message='', warning_message=''):
		"""Submit the form"""
		response = form.submit(headers=self.headers)
		logging.info('Test response form submission status = %s' % str(response.status_int))
		if response.status_int == 200:
			if expect_error: # form validation errors result in response 200
				self.assert_error_message_in_response(response.body, message=error_message)
				
				# error_label = soup.find("label", "error")
				# error_label_for = error_label.attr('for')
				# if expect_error:
				#	if error_message:
				#		self.assertIn(error_message, error_label.contents)
				#	if error_field:
				#		self.assertEqual(error_field, error_label_for)
				#	return response
				# else:
				#	self.fail("form failed due to field '{}' with error: {}".format(error_label_for, error_label.text()))
			else: # some forms do not redirect
				pass
		elif response.status_int == 302:
			response = response.follow(headers=self.headers)
		else:
			self.fail("unexpected form response: {}".format(response.status))

		if expect_error:
			self.assert_error_message_in_response(response.body, message=error_message)
		else:
			self.assert_no_error_message_in_response(response.body)
			if success_message:
				self.assert_success_message_in_response(response.body, message=success_message)
			if warning_message:
				self.assert_warning_message_in_response(response.body, message=warning_message)
		return response
		
	def getTestUserKey(self):
		user = self.register_activate_login_testuser()
		i = 0
		while i<3:
			i = i+1
			user = self.get_user_data_from_session()
			if not user:
				self.login_user('testuser', '456456')
			else:
				break
		if not user:
			self.fail('Could not find a User')
	
		user_info = boilerplate_models.User.get_by_id(long(user['user_id']))
		if user_info:
			return user_info.key
		else:
			self.fail('Could not find a User')
	
	def login_user(self, username, password):
		"""Login user by username and password."""
		form = self.get_form('/login/', 'form_login_user')
		form['username'] = username
		form['password'] = password
		self.submit(form)
		self.assert_user_logged_in()

	def activate_user(self, user, use_activation_email=True):
		"""Activate user account."""
		self.assertFalse(user.activated, 'user has been already activated')
		if use_activation_email:
			# get mail from the appengine stub
			message = self.get_sent_messages(to=user.email)[0]
			# click activation link
			url = self.get_url_from_message(message, 'activation')
			self.get(url, status=302)
		else:
			user.activated = True
			user.put()
		# activated user should be auto-logged in
		self.assertTrue(user.activated)
		self.assert_user_logged_in()

	def register_activate_login_testuser(self):
		user = self.register_testuser()
		self.activate_user(user)
		return user

	def register_testuser(self, **kwargs):
		return self.register_user('testuser', '123456', 'testuser@example.com', **kwargs)

	def register_user(self, username, password, email):
		"""Register new user account.

		Optionally activate account and login with username and password."""
		form = self.get_form('/register/', 'form_register')
		form['username'] = username
		form['email'] = email
		form['password'] = password
		form['c_password'] = password
		self.submit(form)

		users = boilerplate_models.User.query(boilerplate_models.User.username == username).fetch(2)
		self.assertEqual(1, len(users), "{} could not register".format(username))
		user = users[0]

		return user

	def get_user_data_from_session(self):
		"""Retrieve user info from session."""
		cookies = "; ".join(["{}={}".format(k, v) for k, v in self.testapp.cookies.items()])
		request = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
		request.app = self.app
		a = auth.Auth(request=request)
		return a.get_user_by_session()

	def assert_user_logged_in(self, user_id=None):
		"""Check if user is logged in."""
		cookie_name = self.app.config.get('webapp2_extras.auth').get('cookie_name')
		self.assertIn(cookie_name, self.testapp.cookies,
					  'user is not logged in: session cookie not found')
		user = self.get_user_data_from_session()
		if user is None:
			self.fail('user is not logged in')
		if user_id:
			self.assertEqual(user['user_id'], user_id, 'unexpected user is logged in')

	def assert_user_not_logged_in(self):
		"""Check if user is not logged in."""
		self.assertIsNone(self.get_user_data_from_session(), 'user is logged in unexpectedly')


	def assert_error_message_in_response(self, response, message=''):
		"""Check if response contains one or more error messages.

		Assume error messages rendered as <p class="alert-error"> elements.
		"""
		soup = BeautifulSoup(response)
		#logging.info(soup)
		alert = soup.findAll("p", "alert-error")
		logging.info(alert)
		if len(alert) > 0 :
			pass
		else:
			self.fail('no error message found in response')
		if message:
			found = str(alert[0]).find(message)
			self.assertGreater(found, 0)

	def assert_success_message_in_response(self, response, message=''):
		"""Check if response contains one or more success messages.

		Assume success messages rendered as <p class="alert-success"> elements.
		"""
		soup = BeautifulSoup(response)
		alert = soup.findAll("p", "alert-success")
		self.assertGreater(len(alert), 0, 'no success message found in response')
		if message:
			found = str(alert[0]).find(message)
			self.assertGreater(found, 0)

	def assert_warning_message_in_response(self, response, message=''):
		"""Check if response contains one or more warning messages.

		Assume warning messages rendered as <p class="alert-warning"> elements.
		"""
		soup = BeautifulSoup(response)
		alert = soup.findAll("p", "alert-warning")
		self.assertGreater(len(alert), 0, 'no warning message found in response')
		if message:
			found = str(alert[0]).find(message)
			self.assertGreater(found, 0)

	def assert_no_error_message_in_response(self, response):
		"""Check that response has no error messages."""
		soup = BeautifulSoup(response)
		el = soup.find("p", "alert-error")
		if el:
			self.fail('error message found in response unexpectedly: {}'.format(el.contents))
		el = soup.findAll("label", "alert-error")
		if el:
			self.fail('error message found in response unexpectedly: {}'.format(el.contents))
	
	def assert_has_div_with_ID(self, response, id_attr):
		"""Check if response contains a Div with a particular ID attribute.

		<div id="<some-id>"> elements.
		""" 
		soup = BeautifulSoup(response)
		alert = soup.findAll("div", id=id_attr)
		if alert:
			self.assertGreater(len(alert), 0, 'No Div tag with, id=%s, in response' % str(id_attr))
		else:
			self.fail('No Div tag with, id=%s, in response' % str(id_attr))

	def execute_tasks(self, url=None, queue_name='default', expect_tasks=1):
		"""Filter and execute tasks accumulated in the task queue stub."""
		tasks = self.taskqueue_stub.get_filtered_tasks(url=url, queue_names=[queue_name])
		if expect_tasks:
			self.assertEqual(expect_tasks, len(tasks),
					'expect {} task(s) in queue, found {}: {}'.
					format(expect_tasks, len(tasks), ", ".join([t.name for t in tasks])))
		for task in tasks:
			self.post(task.url, params=task.payload)
			self.taskqueue_stub.DeleteTask(queue_name, task.name)


	def get_sent_messages(self, to=None, expect_messages=1, reset_mail_stub=True):
		"""Fetch sent emails accumulated in the mail stub."""
		# in the single threaded test we have to process the tasks before getting mails
		self.execute_tasks(url='/taskqueue-send-email/', expect_tasks=None)
		messages = self.mail_stub.get_sent_messages(to=to)
		# remove ALL messages from mail stub
		# TODO: remove only fetched messages and get rid of reset_mail_stub parameter
		if reset_mail_stub:
			self.mail_stub._cached_messages=[]
		if expect_messages:
			self.assertEqual(expect_messages, len(messages))
		for message in messages:
			self.assertEqual(to, message.to)
		return messages

	def get_url_from_message(self, message, pattern):
		m = re.search("http://\S+?(/{}/\S+)".format(pattern), message.html.payload, re.MULTILINE)
		self.assertIsNotNone(m, "{} link not found in mail body".format(pattern))
		return m.group(1)