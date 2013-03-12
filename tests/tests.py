'''
Run the tests using testrunner.py script in the project root directory.

Usage: testrunner.py SDK_PATH TEST_PATH
Run unit tests for App Engine apps.

SDK_PATH	Path to the SDK installation
TEST_PATH	Path to package containing test modules

Options:
  -h, --help  show this help message and exit

'''
import logging
import unittest
import webapp2
import os

from google.appengine.ext import testbed
from google.appengine.ext import ndb

import config
import routes
import boilerplate
from boilerplate import routes as boilerplate_routes
from boilerplate import models as boilerplate_models

from libr import test_helpers
from libr import webtest
from libr import utils
from models import shoppingModels

# setting HTTP_HOST in extra_environ parameter for TestApp is not enough for taskqueue stub
os.environ['HTTP_HOST'] = 'localhost'

# globals
network = False

baseParams = {
	'cart': None,
	'cartItems': None,
	'belists': None,
	'marketMakerPos': None,
	'watchlistItems': None,
	'alerts': None,
	}

class AppTest(unittest.TestCase, test_helpers.HandlerHelpers):
	def setUp(self):

		# create a WSGI application.
		webapp2_config = config.config
		self.app = webapp2.WSGIApplication(config=webapp2_config)
		routes.add_routes(self.app)
		boilerplate_routes.add_routes(self.app)
		self.testapp = webtest.TestApp(self.app, extra_environ={'REMOTE_ADDR' : '127.0.0.1'})

		# # use absolute path for templates
		# self.app.config['webapp2_extras.jinja2']['template_path'] =	 ['/templates']

		# activate GAE stubs
		self.testbed = testbed.Testbed()
		self.testbed.activate()
		self.testbed.init_datastore_v3_stub()
		self.testbed.init_memcache_stub()
		self.testbed.init_urlfetch_stub()
		self.testbed.init_taskqueue_stub()
		self.testbed.init_mail_stub()
		self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)
		self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
		self.testbed.init_user_stub()

		self.headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) Version/6.0 Safari/536.25',
						'Accept-Language' : 'en_US'}

		# fix configuration if this is still a raw boilerplate code - required by test with mails
		if not utils.is_email_valid(self.app.config.get('contact_sender')):
			self.app.config['contact_sender'] = "noreply-testapp@example.com"
		if not utils.is_email_valid(self.app.config.get('contact_recipient')):
			self.app.config['contact_recipient'] = "support-testapp@example.com"
		
		##: Setup global variables
		self.deleteTestProduct()
		product, best_price, productPriceTiers = self.getTestProduct()
		urlsafeKey = product.key.urlsafe()
		
		self.testProduct = product
		self.testProduct_urlsafeKey = urlsafeKey
		self.testProduct_bestPrice = best_price
		self.testProduct_priceTiers = productPriceTiers
		
		logging.info('product = {}'.format(self.testProduct))
		logging.info('urlsafeKey = {}'.format(self.testProduct_urlsafeKey))
		logging.info('best_price = {}'.format(self.testProduct_bestPrice))


	def tearDown(self):
		self.testbed.deactivate()

	def test_config_environment(self):
		self.assertEquals(self.app.config.get('environment'), 'localhost')


	def test_HomeRequestHandler(self):

		response = self.get('/')
		
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')
	
	def test_FullPageCartHandler(self):
		order, cart = self.getTestOrder()
		urlsafeCartKey = cart.key.urlsafe()
		##: Test for Valid Cart UrlSafe Key, if not this is a Fail
		##: NOT Logged In so this is a redirect, Because this tests a Private Cart.
		response = self.testapp.get('/shoppingCart/{}'.format(urlsafeCartKey), status=302).follow(status=200, headers=self.headers)
		##: Not logged in so we will redirect
		self.assertEqual(response.status_int, 200, "This was Not Logged In, so we registered and Logged In")
		self.assertEqual(response.content_type, 'text/html')
		
		##: Next we Sign In
		userKey = self.getTestUserKey()
		
		##: Now we try logged in
		response = self.testapp.get('/shoppingCart/{}'.format(urlsafeCartKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')


	def test_FullPageWatchlistHandler(self):
		urlsafeWatchlistKey, urlsafeProductKey = self.getTestWatchlist()
		##: Test for Valid Cart UrlSafe Key, if not this is a Fail
		##: NOT Logged In so this is a redirect, if not this is a Fail
		response = self.testapp.get('/watchlist/{}'.format(urlsafeWatchlistKey), status=302).follow(status=200, headers=self.headers)
		##: Not logged in so we will redirect
		self.assertEqual(response.status_int, 200, "This was Not Logged In, so we registered and Logged In")
		self.assertEqual(response.content_type, 'text/html')
		
		##: Next we Sign In
		userKey = self.getTestUserKey()
		
		##: Now we try logged in
		response = self.testapp.get('/watchlist/{}'.format(urlsafeWatchlistKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')


	def test_FullPagePositionsHandler(self):
		##: Test for Valid Cart UrlSafe Key, if not this is a Fail
		##: NOT Logged In so this is a redirect, if not this is a Fail
		response = self.testapp.get('/positions', status=302).follow(status=200, headers=self.headers)
		##: Not logged in so we will redirect
		self.assertEqual(response.status_int, 200, "This was Not Logged In, so we registered and Logged In")
		self.assertEqual(response.content_type, 'text/html')
		
		##: Next we Sign In
		userKey = self.getTestUserKey()
		
		##: Now we try logged in
		response = self.testapp.get('/positions')
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')

	
	def test_HomeSearchProductForm(self):
		##: Now we will test the form submission
		form = self.get_form('/', 'productSearchForm')
		form['pn'] = 'AVE106M16B12T-F'
		form['q'] = '1'
		self.submit(form)
		
		##: Now we will test the form submission for a FAIL
		form['pn'] = '?1?1?1?1?1'
		form['q'] = 'q'
		self.submit(form, expect_error=True, error_message=None)
		form['pn'] = '?1?1?1?1?1'
		form['q'] = '1'
		self.submit(form) ##: This will complete the form without errors but will not find a product.


	def test_ProductRequestHandler(self):
		urlsafeProductKey = self.testProduct_urlsafeKey

		##: Test for Missing ProductNumber Redirect, if not this is a Fail
		response = self.testapp.get('/product', status=302).follow(status=200)
		self.assertEqual(response.content_type, 'text/html')
		self.assert_error_message_in_response(response.body, message=None)
		
		
		##: Test for Invalid ProductNumber Missing Quantity Redirect, if not this is a Fail
		response = self.testapp.get('/product/1111', status=302).follow(status=200)
		self.assertEqual(response.content_type, 'text/html')
		self.assert_error_message_in_response(response.body, message=None)
			

		##: Test for Invalid ProductNumber Missing Quantity Redirect, if not this is a Fail
		response = self.testapp.get('/product/1111+@#%$%<35}&q=d', status=302).follow(status=200)
		self.assertEqual(response.content_type, 'text/html')
		self.assert_error_message_in_response(response.body, message=None)

		##: Test for Valid ProductNumber Missing Quantity Redirect, if not this is a Fail
		response = self.get('/product/{}'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')
		self.assert_has_div_with_ID(response.body, 'productNameTitle_AVE106M16B12T-F')

		##: Test for Valid ProductNumber and Valid Quantity Redirect, if not this is a Fail
		response = self.get('/product/{}?q=1'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')
		self.assert_has_div_with_ID(response.body, 'productNameTitle_AVE106M16B12T-F')

	
	def test_AddToBeListFormHandler(self):
		
		urlsafeProductKey = self.testProduct_urlsafeKey
		logging.info('urlsafeKey = {}'.format(self.testProduct_urlsafeKey))
		
		##: Test for Valid Product Key, No Quantity, NOT Logged In so this is a redirect, if not this is a Fail
		response = self.testapp.get('/addToBeListForm/{}'.format(urlsafeProductKey), status=302).follow(status=200, headers=self.headers)
		
		##: Not logged in so we will redirect
		self.assertEqual(response.status_int, 200, "This was Not Logged In, so we registered and Logged In")
		self.assertEqual(response.content_type, 'text/html')
		
		##: Need to be logged in
		userKey = self.getTestUserKey()
		
		##: Test for Valid Product Key, No Quantity, IS Logged In so this is fine, if not this is a Fail
		response = self.testapp.get('/addToBeListForm/{}'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200) ##: This was Logged In
		self.assertEqual(response.content_type, 'text/html')
	
	def test_CreateLimitOrderFormHandler(self):
		
		urlsafeProductKey = self.testProduct_urlsafeKey
		logging.info('urlsafeKey = {}'.format(self.testProduct_urlsafeKey))
		
		##: Test for Valid Product Key, No Quantity, NOT Logged In so this is a redirect, if not this is a Fail
		response = self.testapp.get('/createLimitOrder/{}'.format(urlsafeProductKey), status=302).follow(status=200, headers=self.headers)
		
		##: Not logged in so we will redirect
		self.assertEqual(response.status_int, 200, "This was Not Logged In, so we registered and Logged In")
		self.assertEqual(response.content_type, 'text/html')
		
		##: Need to be logged in
		userKey = self.getTestUserKey()

		##: Test for Valid Product Key, No Quantity, IS Logged In so this is fine, if not this is a Fail
		response = self.testapp.get('/addToBeListForm/{}'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')
	
	def test_CreateAlertFormHandler(self):
		
		urlsafeProductKey = self.testProduct_urlsafeKey
		logging.info('urlsafeKey = {}'.format(self.testProduct_urlsafeKey))
		
		##: Test for Valid Product Key, No Quantity, NOT Logged In so this is a redirect, if not this is a Fail
		response = self.testapp.get('/createAlertForm/{}'.format(urlsafeProductKey), status=302).follow(status=200, headers=self.headers)
		
		##: Not logged in so we will redirect
		self.assertEqual(response.status_int, 200, "This was Not Logged In, so we registered and Logged In")
		self.assertEqual(response.content_type, 'text/html')
		
		##: Need to be logged in
		userKey = self.getTestUserKey()

		##: Test for Valid Product Key, No Quantity, IS Logged In so this is fine, if not this is a Fail
		response = self.testapp.get('/createAlertForm/{}'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')

	def test_ExchangeOrderHandler(self):
		urlsafeProductKey = self.testProduct_urlsafeKey
		logging.info('urlsafeKey = {}'.format(self.testProduct_urlsafeKey))
		
		logging.info('testProduct_priceTiers MPN = {}'.format(self.testProduct_priceTiers.pn))
		logging.info('testProduct_priceTiers PK = {}'.format(self.testProduct_priceTiers.pk))
		
		##: Test for Valid Product UrlSafe Key, if not this is a Fail
		response = self.testapp.get('/exchangeOrder/{}'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')
	
		##: Test for Valid Product UrlSafe Key and Quantity Argument which should be ignored, if not this is a Fail
		response = self.testapp.get('/exchangeOrder/{}?q=1'.format(urlsafeProductKey))
		self.assertEqual(response.status_int, 200)
		self.assertEqual(response.content_type, 'text/html')

	def test_CompleteExchangeOrderHandler(self):
		pass
	
	def test_AddToWatchlistHandler(self):
		##: This Handler only excepts POST requests, this will redirect
		response = self.testapp.get('/addToWatchlist', status=405)
		
		##: Need to be logged in to use form
		userKey = self.getTestUserKey()
			
		urlsafeProductKey = self.testProduct_urlsafeKey
		form = self.get_form('/product/{}&q=1'.format(urlsafeProductKey), 'addToWatchlistForm')
		form['pk'] = urlsafeProductKey
		form['wln'] = 'ALL'
		self.submit(form,success_message='')
		
		watchlist = shoppingModels.Watchlist.get_default_for_user(userKey)
		if watchlist:
			pk = ndb.Key(urlsafe=urlsafeProductKey)
			self.assertIn(pk, watchlist.pl)
		else:
			self.fail('Could not find Watchlist')

	
	def test_DeleteFromWatchlistHandler(self):
		##: This Handler only excepts POST requests, this will redirect
		response = self.get('/deleteFromWatchlist', status=405)

		##: Need to be logged in to use form
		userKey = self.getTestUserKey()
		
		urlsafeWatchlistKey, urlsafeProductKey = self.getTestWatchlist()
		
		form = self.get_form('/', 'deleteFromWatchlist')
		form['pk'] = urlsafeProductKey
		form['wlk'] = urlsafeWatchlistKey
		self.submit(form, success_message='Product has been removed from your Watchlist')
		
		watchlist = shoppingModels.Watchlist.get_default_for_user(userKey)
		if watchlist:
			pk = ndb.Key(urlsafe=urlsafeProductKey)
			self.assertNotIn(pk, watchlist.pl)
		else:
			self.fail('Could not find Watchlist')

	def test_AddToCartHandler(self):
		##: This Handler only excepts POST requests, this will redirect
		response = self.get('/addToCart', status=405)
		
		##: Need to be logged in to use form
		userKey = self.getTestUserKey()
			
		urlsafeProductKey = self.testProduct_urlsafeKey
		form = self.get_form('/product/{}&q=1'.format(urlsafeProductKey), 'addToCartForm')
		form['pk'] = urlsafeProductKey
		form['cn'] = 'SHOPPING'
		form['q'] = '23'
		self.submit(form, success_message='')
		
		productKey = ndb.Key(urlsafe=urlsafeProductKey)
		orders = shoppingModels.Order.get_for_product(productKey, paid=False, shipped=False, quantity=2)
		if orders:
			self.assertEqual(1, len(orders))
		else:
			self.fail('Could not find Order')


	def test_DeleteOrderFromCartHandler(self):
		##: This Handler only excepts POST requests, this will redirect
		response = self.get('/removeFromCart', status=405)
		
		##: Need to be logged in to use form
		userKey = self.getTestUserKey()

		order, cart = self.getTestOrder()
		if order and cart:
			form = self.get_form('/', 'deleteFromCartForm_{}'.format(order.pn))
			form['ok'] = order.key.urlsafe()
			form['ck'] = cart.key.urlsafe()
			form['ost'] = order.st
			form['lo'] = 'False'
			self.submit(form, success_message='')
		else:
			self.fail('Could not get the Order and Cart')
		
		cart = cart.key.get() ##: Re-Get the Cart model
		if cart:
			self.assertNotIn(order.key, cart.okl)
		else:
			self.fail('Could not find Order')
				
		order = order.key.get() ##: Re-Get the order model
		if order:
			self.fail('Order should have been deleted')


	

	def test_ChangeQuantityOfOrderHandler(self):
		##: This Handler only excepts POST requests, this will redirect
		response = self.get('/changeQntOfOrder', status=405)
		
		##: Need to be logged in to use form
		userKey = self.getTestUserKey()
		
		order, cart = self.getTestOrder()
		if order and cart:
			logging.info('We have Test Order = {}'.format(order))
			pre_qnt = order.q
			cartItems = None
			if len(cart.okl) > 0:
				logging.info('There are items in the cart')
				L = []
				for i in cart.okl:
					L.append(i)
				cartItems = ndb.get_multi(L)
			
			form = self.get_form('/', 'chgQntFromCartForm')
			form['ok'] = order.key.urlsafe()
			form['ck'] = cart.key.urlsafe()
			form['ost'] = order.st
			form['lo'] = 'False'
			form['q'] = '100'
			self.submit(form, success_message='')
		else:
			self.fail('Could not get the Order and Cart')
		
		order = order.key.get()
		if order:
			self.assertEqual(100, order.q)
		else:
			self.fail('Could not find order after updating')

	
	def test_CreateAlertHandler(self):
		response = self.get('/createAlert', status=405)
		
		##: Need to be logged in to use form
		userKey = self.getTestUserKey()
		
		pn = self.testProduct.pn
		urlsafeProductKey = self.testProduct_urlsafeKey
		form = self.get_form('/createAlertForm/{}'.format(urlsafeProductKey), 'createAlertForm')
		form['pk'] = urlsafeProductKey
		form['ap'] = '0.3'
		form['aq'] = '23'
		self.submit(form)
		
		alerts = shoppingModels.Alert.get_for_UserKey(userKey, mpn, quantity=2)
		if alerts:
			self.assertIn(30, alerts.ap)
			self.assertIn(23, alerts.aq)
		else:
			self.fail('Could not find alerts')


class ModelTest(unittest.TestCase):
	def setUp(self):

		# activate GAE stubs
		self.testbed = testbed.Testbed()
		self.testbed.activate()
		self.testbed.init_datastore_v3_stub()
		self.testbed.init_memcache_stub()

	def tearDown(self):
		self.testbed.deactivate()

	def test_user_token(self):
		user = boilerplate_models.User(name="tester", email="tester@example.com")
		user.put()
		user2 = boilerplate_models.User(name="tester2", email="tester2@example.com")
		user2.put()

		token = boilerplate_models.User.create_signup_token(user.get_id())
		self.assertTrue(boilerplate_models.User.validate_signup_token(user.get_id(), token))
		self.assertFalse(boilerplate_models.User.validate_resend_token(user.get_id(), token))
		self.assertFalse(boilerplate_models.User.validate_signup_token(user2.get_id(), token))


if __name__ == "__main__":
	unittest.main()
