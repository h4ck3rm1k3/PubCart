# -*- coding: utf-8 -*-

"""
	A real simple app for using webapp2 with auth and session.

	It just covers the basics. Creating a user, login, logout
	and a decorator for protecting certain handlers.

	Routes are setup in routes.py and added in main.py
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


class HomeRequestHandler(RegisterBaseHandler):
	"""
	Handler to show the home page
	"""

	def get(self):
		""" Returns a simple HTML form for home """
		try:
			params =	{}
		except:
			params =	{}
			entries = None
			logging.error('Error during Request')
		finally:
			
			self.bournee_template('home.html', **params)


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





class FullPageWatchlistHandler(BournEEHandler):
	"""
	Handler to view full page of Watchlist items.
	These are private so a User is required
	"""
	@user_required
	def get(self, urlsafeWatchlistKey):
		try:
			##: Make Sure if the cart is Private the owner (userKey) is viewing it.
			watchlistKey = ndb.Key(urlsafe=urlsafeWatchlistKey)
			watchlist = watchlistKey.get()
			logging.info('Here')
			
			if not watchlist:
				raise Exception('No Watchlist Found')
			##: The user_key must match the watchlist's user_key
			if watchlist.uk != self.user_key:
				raise Exception('User doing request does not match the owner of the Watchlist.')
			logging.info('Here')

			watchlistName = "ALL"
			if watchlist.n:
				if watchlist.n != "ALL":
					logging.info('Here')
					
					watchlistName = str(watchlist.n).upper()
	
			modelObjects = []
			if watchlist.kl:
				logging.info('Here')
				if len(watchlist.kl)>1:
					logging.info('Here')
					
					modelObjects = ndb.get_multi(watchlist.kl)
				elif len(watchlist.kl)==1:
					logging.info('Here')
					
					modelObjects.append(watchlist.kl[0].get())
			
			watchedCarts = []
			watchedProducts = []
			for modelObject in modelObjects:
				if 'Product' in str(modelObject.key.kind()):
					watchedProducts.append(modelObject)
				elif 'Cart' in str(modelObject.key.kind()):
					watchedCarts.append(modelObject)
			logging.info('Here')
			
			params = {
				"modelObjects" : modelObjects,
				"watchedCarts": watchedCarts,
				"watchedProducts": watchedProducts,
				"urlsafeWatchlistKey": urlsafeWatchlistKey,
				"watchlistName": watchlistName,
			}
			logging.info('Here')
			
			self.bournee_template('fullWatchlist.html', **params)

		except Exception as e:
			logging.error('Error in handler - FullPageWishlistHandler : -- {}'.format(e))
			message = _('We are having difficulties displaying the Full Watchlist Page. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


class FullPagePositionsHandler(BournEEHandler):
	"""
	Handler to view full page of Position items (MarketMakers).
	These are private so a User is required
	"""
	@user_required
	def get(self):
		try:
			p = self.request.get('p')
			q = self.request.get('q') ##: This is for the search which should be added to the query.
			c = self.request.get('c')
			forward = True if p not in ['prev'] else False
			cursor = Cursor(urlsafe=c)
			
			if q:
				qry = shoppingModels.MarketMaker.query(ancestor=self.user_key) ##: TODO add the q(for search query) to this query
			else:
				qry = shoppingModels.MarketMaker.query(ancestor=self.user_key)

			PAGE_SIZE = 5
			if forward:
				positions, next_cursor, more = qry.order(shoppingModels.MarketMaker.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
				if next_cursor and more:
					self.view.next_cursor = next_cursor
				if c:
					self.view.prev_cursor = cursor.reversed()
			else:
				positions, next_cursor, more = qry.order(-shoppingModels.MarketMaker.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
				positions = list(reversed(positions))
				if next_cursor and more:
					self.view.prev_cursor = next_cursor
				self.view.next_cursor = cursor.reversed()
 
			def pager_url(p, cursor):
				params = OrderedDict()
				if q:
					params['q'] = q
				if p in ['prev']:
					params['p'] = p
				if cursor:
					params['c'] = cursor.urlsafe()
				return self.uri_for('fullPagePositions', **params)

			self.view.pager_url = pager_url
			self.view.q = q

			params = {
				"list_columns": [
								('pn', 'Product Number'), 
								('d', 'Description'),
								('bup', 'Purchase Price'),
								('sup', 'Selling Price'),
								('rq', 'Quantity'),
								('qoh', 'Qnt. on Hold'),
								('roi', 'Est. R.O.I.'),
								('p', 'Markup %'),
								('f', 'Fee Paid'),
								],
				"positions" : positions,
				"count" : qry.count()
			}
			self.bournee_template('fullPositions.html', **params)

		except Exception as e:
			logging.error('Error in handler - FullPagePositionsHandler : -- {}'.format(e))
			message = _('We are having difficulties displaying the Full Positions Page. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


class CreateLimitOrderFormHandler(RegisterBaseHandler):
	"""
	Handler for the Products Exchange order form and info page.
	"""
	@user_required
	def get(self, pk):
		""" Returns page containing part info and exchange order form """
		##: pk = product Key
		qnt = self.request.GET.get('q', 1)
		self.doWork(pk,qnt)

	def doWork(self, partKey, quantity):
		""" 
		This is a common function for both Methods GET and POST
		"""
		productModel = None
		best_price = None
		try:
			##: Make Sure quantity from URL is an integer
			qnt = int(quantity)
			logging.info('Quantity suplied in CreateLimitOrderFormHandler = %s' % str(qnt))
			##: Get the Product Model and Best Price
			##: partKey is a urlSafe key from the request URL
			productModel, best_price = bestPrice.getBestPrice( partKey , None, int(qnt))
			if best_price == None:
				logging.error('Error, Best Price not determined. ')
				raise Exception('Best Price not determined.')
			if not productModel or not best_price:
				logging.error('Error, No Product Model Found ')
				raise Exception('No Product Model Found using urlsafe key and the function getBestPrice')

			params =	{'product': productModel,
						'requested_quantity': int(qnt),
						'best_price': dollar_float(float(best_price)),
						}
		
			self.bournee_template('limitOrder.html', **params)

		except Exception as e:
			logging.error('Error, Updating Quantity for CreateLimitOrderFormHandler: -- %s' % str(e))
			message = _('We are having difficulties with the request for the Limit Order Form. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def addToCart_form(self):
		return forms.AddToCartForm(self)


class CreateAlertFormHandler(RegisterBaseHandler):
	"""
	Handler for the Products Exchange order form and info page.
	"""
	@user_required
	def get(self, pk):
		""" Returns page containing part info and exchange order form """
		##: pk = product Key
		self.doWork(pk)

	def doWork(self, partKey):
		""" 
		This is a common function for both Methods GET and POST
		"""
		productModel = None
		best_Price = None ##: Remeber the there is a Module called bestPrice...
		try:

			##: Get the Product Model and Best Price
			##: partKey is a urlSafe key from the request URL
			productModel, best_Price = bestPrice.getBestPrice( partKey , None, int(1))
			if best_Price == None:
				logging.error('Error, Best Price not determined. ')
				raise Exception('Best Price not determined.')
			if not productModel or not best_Price:
				logging.error('Error, No Product Model Found ')
				raise Exception('No Product Model Found using urlsafe key and the function getBestPrice')

			params =	{'product': productModel,
						'best_price': dollar_float(float(best_Price)),
						}
		
			self.bournee_template('createAlertForm.html', **params)

		except Exception as e:
			logging.error('Error, in CreateAlertFormHandler: -- %s' % str(e))
			message = _('We are having difficulties with the request for the Alert Form. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def createAlert_form(self):
		return forms.CreateAlertForm(self)

class ExchangeOrderHandler(RegisterBaseHandler):
	"""
	Handler for the Products Exchange order form and info page.
	"""
	def get(self, pk):
		""" Returns page containing part info and exchange order form """
		##: pn = partNumber
		try:
			##: Try to find the part in the Datastore.
			productKey = ndb.Key(urlsafe=pk)
			productModel = productKey.get()
			if productModel:
				logging.info('Product MPN = {}'.format(productModel.pn))
				##: Get the minimum Exchange Order qnt and unit price for this part.
				productTierPrice = shoppingModels.ProductTierPrice.get_for_product(productModel.pn, productKey)
				if productTierPrice:
					meq = int(productTierPrice.meq)
					mep = float(productTierPrice.mep)/100
					rep = float(productTierPrice.rep)/100
					pProfit = float(productTierPrice.pp)/100
					percentage = int(productTierPrice.ppp)
			
					fee = float(pProfit) * float(0.05) ##: 5% of profit

					#: Calculate the cost with the minimums
					cost = (float(meq)*float(mep)) + fee

					##:	 This Loop will determine the Maximum Markup Percentage (mmp) a Market Maker can charge on this product.
					maxPercentage = percentage
					oneHPrice = float(productTierPrice.oH)/100
					per=1.50
					while per >= 1.01:
						sellPrice = float(mep) * float(per)
						if float(sellPrice) > float(oneHPrice):
							##: If the determined sell price is higher than the 100 unit Price then this is a fail. It must be lower.
							per -= 0.01
							continue
						else:
							maxPercentage = int(per*100)-100
							maxSellPrice = sellPrice
							break

					if maxPercentage < percentage:
						percentage = maxPercentage

					params = {'product': productModel,
								'meq': int(meq), # Needed in template during a Get request
								'mep': dollar_float(mep), # Needed in template during a Get request
								'rep': dollar_float(rep),
								'pProfit': dollar_float(pProfit),
								'percentage': int(percentage),
								'maxPercentage': int(maxPercentage),
								'maxSellPrice': dollar_float(mep),
								'qnt': int(meq), # Needed in template during a POST request
								'up': dollar_float(mep), # Needed in template during a POST request
								'cost': dollar_float(cost),
								'fee': dollar_float(fee),
								}
					self.bournee_template('exchangeOrder.html', **params)
				else:
					logging.error('No productTierPrice Found.')
					raise Exception('No productTierPrice Found.')
			else:
				logging.error('No productModel Found.')
				raise Exception('No productModel Found.')
		except Exception as e:
			logging.error('Error finding Product and/or Price in function get of ExchangeOrderHandler : %s' % e)
			message = _('We are having difficulties with the requested Product. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')



	def post(self, pn):
		if not self.exchangeQnt_form.validate():
			raise Exception('ExchangeQNTForm Form Not Validated, in function post of ExchangeOrderHandler')

		try:
			partNumber = str(pn).upper()
			
			qnt = int(self.exchangeQnt_form.qnt.data)
			meq = int(self.exchangeQnt_form.meq.data)
			mep = float(self.exchangeQnt_form.mep.data)
			percentage = int(self.exchangeQnt_form.percentage.data)
			urlsafeProductKey = str(self.exchangeQnt_form.partNumber.data.strip()).upper()
			price = None
			
			##: Try to find the part in the Datastore.
			productKey = ndb.Key(urlsafe=urlsafeProductKey)
			productModel = productKey.get()

			if not productModel:
				raise Exception('Error fetching the Product with the productNumber from the URI, in function post of ExchangeOrderHandler')

			else:
				logging.info('Quantity Supplied is %s' % str(qnt))
				priceModel, cents_price = shoppingModels.ProductTierPrice.get_price_for_qnt(str(urlsafeProductKey), int(qnt))
				price = float(cents_price)/100
				logging.info('Price returned is %s' % str(price))
			
			if price is None:
				raise Exception('Error determining price from the productTierPrice Model, in function post of ExchangeOrderHandler')

			##:	 This Loop will determine the Maximum Markup Percentage (mmp) a Market Maker can charge on this product.
			maxPercentage = int(percentage)
			oneHPrice = float(priceModel.oH)/100
			per=1.50
			while per >= 1.01:
				sellPrice = float(price) * float(per)
				if float(sellPrice) > float(oneHPrice):
					##: If the determined sell price is higher than the 100 unit Price then this is a fail. It must be lower.
					per -= 0.01
					continue
				else:
					maxPercentage = int(per*100)-100
					maxSellPrice = sellPrice
					break

			if maxPercentage < percentage:
				percentage = maxPercentage

			r_ppp = float(percentage + 100)/100
			if float(price) * float(r_ppp-1.00) <= 0.01:
				rep = float(price) + 0.01
			else:
				rep = float(price) * float(r_ppp)
			pProfit = (float(rep) - float(price)) * float(qnt) ##: Potential Profit

			fee = float(pProfit) * float(0.05) ##: 5% of profit
			
			#: Calculate the cost with the minimums
			cost = float(qnt)*float(price) + float(fee)

		except Exception as e:
			logging.error('Error in function POST of ExchangeOrderHandler : %s' % e)
			message = _('We are having difficulties with the requested Product. Please try again later.')
			self.add_message(message, 'error')
			return self.get(str(pn))

		message = _('Parameters have been updated by your request')
		self.add_message(message, 'success')
			
		params =	{'product': productModel,
					'meq': int(meq), # Needed in template during a Get request
					'mep': dollar_float(mep), # Needed in template during a Get request
					'rep': dollar_float(rep),
					'pProfit': dollar_float(pProfit),
					'percentage': int(percentage),
					'maxPercentage': int(maxPercentage),
					'maxSellPrice': dollar_float(maxSellPrice),
					'qnt': int(qnt), # Needed in template during a POST request
					'up': dollar_float(price), # Needed in template during a POST request
					'cost': dollar_float(cost),
					'fee': dollar_float(fee),
					}
		return self.bournee_template('exchangeOrder.html', **params)

	@webapp2.cached_property
	def exchangeQnt_form(self):
		return forms.ExchangeQNTForm(self)


class CompleteExchangeOrderHandler(BournEEHandler):
	""" Handles the submission of a Exchange Order, then Redirects to a different Handler"""
	## Login Required
	@user_required
	def post(self):
		try:
			if not self.exchangeOrder_form.validate():
				raise Exception('exchangeOrder_form did not Validate, in function POST of CompleteExchangeOrderHandler')
			
			mmlo_key = None
			urlsafeProductKey = str(self.exchangeOrder_form.pk.data.strip()).upper()#
			qnt = int(self.exchangeOrder_form.qnt.data)#
			bup = float(self.exchangeOrder_form.bup.data)#
			sup = float(self.exchangeOrder_form.sup.data)#
			per = float(self.exchangeOrder_form.per.data)
			roi = float(self.exchangeOrder_form.roi.data)
			fee = float(self.exchangeOrder_form.fee.data)
			cost = float(self.exchangeOrder_form.cost.data)

			##: Try to find the part in the Datastore.
			productKey = ndb.Key(urlsafe=urlsafeProductKey)
			productModel = productKey.get()
			
			if productModel:
				##: Check for existing marketMaker Model
				marketMaker = shoppingModels.MarketMaker.get_for_UserKey(self.user_key, str(pn), str(sup))
				if marketMaker:
					mmlo_key = marketMaker.key
				else:
					##: Create the MarketMaker Limit Order
					mmlo = shoppingModels.MarketMaker(
								uk = self.user_key, ##: User Model Key
								pk = productModel.key, ##: Product Model Key
								pn = str(pn), ##: Digi Key Product Number
								d = str(productModel.d), ##: Description
								bup = int(bup*100), ##: Purchased Price / Buy Price (cents)
								sup = int(sup*100), ##: Limit Price / Selling  Price (cents)
								rq = int(qnt), ##: Remaining Quantity
								c = int(cost*100), ##: Full Order Cost
								roi = int(roi*100), ##: Estimated Return on Investment at time of purchase
								f = int(fee*100), ##: Fee charged by BournEE Exchange at time of full order purchase
								p = int(per), ##: Percentage of markup on Buy Price
								img = str(productModel.img), ##: Product Image URI
								)
					mmlo_key = mmlo.put()
			
			if mmlo_key:
				message = _('Your Exchange Product Order has been created for Product Number: %s' % str(pn))
				self.add_message(message, 'success')
				self.redirect_to('product', urlsafeProductKey=productModel.key.urlsafe())
			else:
				raise Exception('No mmlo_key, error creating MarketMaker, in function POST of CompleteExchangeOrderHandler')

		except Exception as e:
			logging.error('Error in function POST of CompleteExchangeOrderHandler : --	%s' % e)
			message = _('We are having difficulties with finalizing the Exchange Order Submission. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


	@webapp2.cached_property
	def exchangeOrder_form(self):
		return forms.ExchangeOrderForm(self)


class CreateAlertHandler(BournEEHandler):
	"""
	Handles the submission of an Alert Form, it creates the model then redirects back to referer
	"""
	@user_required
	def post(self):
		try:
			if not self.createAlert_form.validate():
				message = _('The Create Alert Form had error when submitted. Please try again.')
				self.add_message(message, 'error')
				raise Exception('createAlert_form did not Validate, in function POST of CreateAlertHandler')
			
			logging.info("createAlert_form Form Was valid")
			
			product = None
			aKey = None
			
			productKey = str(self.createAlert_form.pk.data.strip())
			alertPrice = self.createAlert_form.ap.data
			alertQuantity = self.createAlert_form.aq.data
			
			if alertPrice or alertQuantity:
				
				if alertPrice: alertPrice = int(alertPrice*100)
				if alertQuantity: alertQuantity = int(alertQuantity)
				
				if productKey:
					##: Try to get Product Model with Key
					product = ndb.Key(urlsafe=productKey).get()
				
			if product:
				
				##: See if an alert already exists
				alert = shoppingModels.Alert.get_for_UserKey(self.user_key, product.pn)
				
				if alert:
					##: Alert Exists
					if alertPrice:
						if alert.ap:
							apL = alert.ap
							apL.append(int(alertPrice))
							alert.ap = apL
						else:
							alert.ap = [int(alertPrice)]
					
					if alertQuantity:
						if alert.aq:
							aqL = alert.aq
							aqL.append(int(alertQuantity))
							alert.aq = aqL
						else:
							alert.aq = [int(alertQuantity)]
					aKey = alert.put()
				else:
					n_apL = []
					n_aqL = []
					if alertPrice: n_apL.append(int(alertPrice))

					if alertQuantity: n_aqL.append(int(alertQuantity))

					##: No Alert Exists
					alert = shoppingModels.Alert(
							uk = self.user_key, ##: User Model Key
							pk = product.key, ##: Product Key ( NOT urlsafe)
							pn = product.pn, ##: Product Number
							ap = n_apL, ##: Alert Price (list)
							aq = n_aqL, ##: Alert Quantity (list)
							)
					aKey = alert.put()
				
				if aKey:
					##: It all Seemed to Work, creat the message to User
					message = _('Your Alert has been created for Product: %s' % str(product.pn))
					self.add_message(message, 'success')

			else:
				##: We did not find a Product
				message = _('The Create Alert Form had error creating an alert for this Product. Please try again Later.')
				self.add_message(message, 'error')
				raise Exception('Could not find Product, in function POST of CreateAlertHandler')


		except Exception as e:
			logging.error('Error, in CreateAlertFormHandler: -- %s' % str(e))
			message = _('We are having difficulties with the request for the Alert Form. Please try again later.')
			self.add_message(message, 'error')
		
		except:
			message = _('We are having difficulties with the request for the Alert Form. Please try again later.')
			self.add_message(message, 'error')
		
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def createAlert_form(self):
		return forms.CreateAlertForm(self)

class AddToWatchlistHandler(BournEEHandler):
	""" Handles the submission of a Exchange Order, then Redirects to a different Handler"""
	## Login Required
	@user_required
	def post(self):
		try:
			if not self.addToWatchlist_form.validate():
				raise Exception('addToWatchlist_form did not Validate, in function POST of CompleteExchangeOrderHandler')
			
			logging.info("addToWatchlist_form Form Was valid")
			
			wl_key = None
			product_key = str(self.addToWatchlist_form.pk.data.strip())
			wl_name = str(self.addToWatchlist_form.wln.data.strip()).upper()
			if wl_name is None:
				wl_name = 'ALL'
			##: Try to find the part in the Datastore.
			productKey = ndb.Key(urlsafe=product_key)
			productModel = productKey.get()
			
			if productModel:
				logging.info("Found a productModel")
				
				##: Check for existing WatchListItem Model
				watchlist = shoppingModels.Watchlist.get_default_for_user(self.user_key)
				if watchlist:
					L = watchlist.kl
					if productKey not in L:
						L.append(productKey) ##: append the productKey (NOT urlsafe)
						watchlist.kl = L
						wl_key = watchlist.put()
					else:
						wl_key = 'existed'
				else:
					##: Create the Watchlist Item
					watchlist = shoppingModels.Watchlist(
								uk = self.user_key, ##: User Model Key
								n = str(wl_name), ##: Watchlist Name
								kl = [productKey], ##: Product List (NOT urlsafe)
								)
					wl_key = watchlist.put()
				
				if wl_key == 'existed':
					message = _('Object is already in your Watchlist')
					self.add_message(message, 'success')
				elif wl_key:
					message = _('Object has been added to your Watchlist')
					self.add_message(message, 'success')
				else:
					logging.error('Error, No wl_key found in function POST of CompleteExchangeOrderHandler')
					message = _('We are having difficulties with adding this part to your Watchlist. Please try again later.')
					self.add_message(message, 'error')
			else:
				logging.error('Error in function POST of CompleteExchangeOrderHandler : --	No ProductModel found, error creating Watchlist Item, in function POST of AddToWatchlistHandler')
				message = _('We are having difficulties with adding this part to your Watchlist. Please try again later.')
				self.add_message(message, 'error')

		except Exception as e:
			logging.error('Error in function POST of AddToWatchlistHandler : --	 %s' % e)
			message = _('We are having difficulties with adding the product to your Watchlist. Please try again later.')
			self.add_message(message, 'error')
		
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
			


	@webapp2.cached_property
	def addToWatchlist_form(self):
		return forms.WatchlistForm(self)


class DeleteFromWatchlistHandler(BournEEHandler):
	""" Handles the submission of a Exchange Order, then Redirects to a different Handler"""
	## Login Required
	@user_required
	def post(self):
		try:
			if not self.deleteFromWatchlist_form.validate():
				raise FunctionException('deleteFromWatchlist_form did not Validate, in function POST of DeleteFromWatchlistHandler')
			
			logging.info("deleteFromWatchlist_form Form Was valid")
			
			wl_key = None ##: This variable used for verification if watchlist was put
			
			partKey = str(self.deleteFromWatchlist_form.pk.data.strip())
			watchlistKey = str(self.deleteFromWatchlist_form.wlk.data.strip())

			partKey = ndb.Key(urlsafe=partKey)
			watchlistKey = ndb.Key(urlsafe=watchlistKey)

			##: Check for existing WatchListItem Model
			try:
				watchlist = watchlistKey.get()
				logging.info('Found Watchlist: {}'.format(watchlist))
				if watchlist:
					L = watchlist.kl
					logging.info('Watchlist items: {}'.format(L))
					if partKey in L:
						L.remove(partKey)
					watchlist.kl = L
					wl_key = watchlist.put()
				else:
					logging.error('Error in function POST of DeleteFromWatchlistHandler : --  %s' % e)
					message = _('We are having difficulties removing Product from Watchlist. Please try again later.')
					self.add_message(message, 'error')
			except Exception as e:
				logging.error('Error removing product form watchlist in function POST of DeleteFromWatchlistHandler : --  %s' % e)
				message = _('We are having difficulties removing Product from Watchlist. Please try again later.')
				self.add_message(message, 'error')

			if wl_key:
				message = _('Product has been removed from your Watchlist')
				self.add_message(message, 'success')

		except FunctionException as e:
			logging.error('Error in function POST of DeleteFromWatchlistHandler : --  %s' % e)
			message = _('We are having difficulties removing Product from Watchlist. Please try again later.')
			self.add_message(message, 'error')

		except Exception as e:
			logging.error('Error in function POST of DeleteFromWatchlistHandler : --  %s' % e)
			message = _('We are having difficulties removing Product from Watchlist. Please try again later.')
			self.add_message(message, 'error')
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


	@webapp2.cached_property
	def deleteFromWatchlist_form(self):
		return forms.WatchlistDeleteForm(self)



class AddAddressHandler(BournEEHandler):
	@user_required
	def post(self):
		try:
			if not self.addAddress_form.validate():
				raise FunctionException('addAddress_form did not Validate, in function POST of AddAddressHandler')
			
			##: Try to fetch the data from the Form responce
			userKey = str(self.addAddress_form.uk.data).strip() ##: Urlsafe Key
			address_name = str(self.addAddress_form.adn.data).strip().upper()
			address1 = str(self.addAddress_form.ad1.data).strip()
			address2 = str(self.addAddress_form.ad2.data).strip()
			city = str(self.addAddress_form.c.data).strip()
			state = str(self.addAddress_form.s.data).strip()
			country = str(self.addAddress_form.con.data).strip()
			zip_code = str(self.addAddress_form.z.data).strip()
			
			userKey = ndb.Key(urlsafe=userKey)
					
			if userKey == self.user_key:
				logging.info('User Keys Match')
			
				address_key = ndb.Key(userModels.Address, address_name, parent=self.user_key)
				address = address_key.get()
				logging.info(address_key)
				logging.info(address)
				if address:
					logging.info('Found Existing Address')
					address.ad1 = address1
					address.ad2 = address2
					address.c = city
					address.s = state
					address.con = country
					address.z = zip_code
					address.is_default = True
				else:
					address_count = userModels.Address.query(ancestor=self.user_key).count()
					if address_count >= 10:
						logging.info("A maximum of 10 Addresses are allowed, user cannot create an 11th")
						message = _('You already have your maximum of 10 addresses setup. You can update an existing address name, or delete an existing address.')
						self.add_message(message, 'error')
					else:
						logging.info('Creating New Address')
						address = userModels.Address(
									key = address_key, \
									adn = address_name, \
									n = self.user_real_name, \
									ad1 = address1, \
									ad2 = address2, \
									c = city, \
									s = state, \
									con = country, \
									z = zip_code, \
									)
				#
				logging.info(address)
				
				##: Make sure this address is default
				addresses = userModels.Address.query(userModels.Address.is_default==True, ancestor=self.user_key).fetch(10)
				if addresses:
					def chg_default(address_to_test):
						address_to_test.is_default = False
						return address_to_test
					changed_addresses = [chg_default(address_to_test) for address_to_test in addresses if address_to_test.key != address_key and address_to_test.is_default == True ]
					changed_addresses.append(address)
					logging.info(changed_addresses)
					ndb.put_multi(changed_addresses)
				else:
					address.put()

				logging.info("We have updated the addresses on file and we Redirect to referrer")
				message = _('We have updated your addresses on file')
				self.add_message(message, 'success')
			else:
				logging.error("User Keys did not match between User and Address Owner")
				message = _('You do not appear to be the owner of this Cart. We can not complete request.')
				self.add_message(message, 'error')


		except Exception as e:
			logging.error("Error occurred running function POST of class AddAddressHandler: -- %s" % str(e))
			message = _('There was an Error during form Submission. We can not complete request. Please try again Later')
			self.add_message(message, 'error')

		finally:
			logging.debug('Redirecting to Referer')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def addAddress_form(self):
		return forms.AddAddressForm(self)


class RegisterOAuthClientHandler(BournEEHandler):
	"""
	Handler for Register Portals (OAuth Clients)
	"""

	def get(self):
		clients = oauth_models.OAuth_Client.get_all()
		params = {'clients':clients}
		return self.bournee_template('www/register_oauth_clients.html', **params)

	def post(self):
		oc_model = oauth_models.OAuth_Client
		portal_id = self.request.get('portal_id')
		client_id = str(portal_id)+'.oauth.crowdfilings.com'
		if oc_model.verify_unique_client_id(client_id):
			client = oc_model(
				client_id		= client_id, \
				key				= ndb.Key(oc_model, client_id), \
				portal_name		= self.request.get('portal_name'), \
				redirect_uri	= self.request.get('redirect_uri'), \
				)
			client.put()
		else:
			logging.debug('Error - Portal ID already registered. Please try again.')
			message = 'Error - Portal ID already registered. Please try again.'
			self.add_message(message, 'error')

		self.redirect(self.request.path)