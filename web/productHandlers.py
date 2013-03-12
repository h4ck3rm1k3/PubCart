#!/usr/bin/env python
# encoding: utf-8
"""
productHandler.py

Created by Jason Elbourne on 2013-03-05.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:	 Python Imports
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
from lib import parsers
from lib.bourneehandler import RegisterBaseHandler, BournEEHandler
from lib.exceptions import FunctionException
from lib import paypal_settings as settings

##:	 Boilerplate Imports
from boilerplate import models
from boilerplate.lib.basehandler import user_required
from boilerplate.lib.basehandler import BaseHandler


class DiscoverProductsHandler(RegisterBaseHandler):
	def get(self):
		try:
			pass
		except Exception as e:
			logging.error('Error finding list of Product function GET of DiscoverProductsHandler : %s' % e)
			message = _('Sorry, there was an error getting the page of products. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


class ProductRequestHandler(RegisterBaseHandler):
	"""
	Handler for the Products page, BOTH for general info page (GET) as well as search result page (POST).
	"""
	def get(self, urlsafeProductKey):
		""" Returns main page for a Part/Product """
		try:
			
			product = ndb.Key(urlsafe=urlsafeProductKey).get()
			if not product:
				raise Exception('Could not find product with urlsafeProductKey given in URI')

			self.doWork(product)

		except Exception as e:
			logging.error('Error in function GET of the ProductRequestHandler: -- %s' % str(e))
			message = _('Error, we are having difficulties finding the request Product Page . Please try again.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
	
	def sellers_product(self, sellerID, productNumber):
		try:
			
			product = ndb.Key(urlsafe=urlsafeProductKey).get()
			if not product:
				raise Exception('Could not find product with urlsafeProductKey given in URI')

			self.doWork(product)

		except Exception as e:
			logging.error('Error in function GET of the ProductRequestHandler: -- %s' % str(e))
			message = _('Error, we are having difficulties finding the request Product Page . Please try again.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


	def doWork(self, productModel):
		""" This is a common function for both Methods GET and POST """
		best_price = None		
		qnt = self.request.get('q', 1)
		try:
			quantity = int(qnt)
		except:
			logging.error('Error, QNT supplied in request URI was not an integer: QNT = %s' % str(qnt))
			raise Exception('Error, QNT supplied in request URI was not an integer: QNT = %s' % str(qnt))
		try:
			########################################################################
			#################
			########   Send to bestPrice script
			#################
			########################################################################
			try:
				best_price = bestPrice.getBestPrice(productModel.key.urlsafe(), int(quantity))
			except Exception as e:
				logging.error('Error finding Product and/or Price in function getProduct of ProductRequestHandler : %s' % e)
				message = _('We could not find a Price result for your Product Request. Please try again later.')
				self.add_message(message, 'error')
				try:
					self.redirect(self.request.referer)
				except:
					self.redirect_to('home')

			########################################################################
			#################
			########   Check Results for None's
			#################
			########################################################################
			if best_price == None or best_price <= 0.0:
				raise Exception('We could not find a Price result for your Product Request. Please try again later.')
				## This is an error and we Need a Price to show the User
				logging.error("Best Price returned as None in function getProduct of ProductRequestHandler.")
				message = _('We could not find a Price result for your Product Request. Please try again later.')
				self.add_message(message, 'error')
				try:
					self.redirect(self.request.referer)
				except:
					self.redirect_to('home')

			try:
				##: Add this product to the last products viewed memcache
				lpv = memcache.get('%s:lastProductsViewed' % str(self.request.remote_addr))
				if lpv == None: lpv = []
				if productModel in lpv: lpv.remove(productModel)
				if len(lpv)>10: lastItem = lpv.pop()
				lpv.insert(0,productModel)
				memcache.set('%s:lastProductsViewed' % str(self.request.remote_addr),lpv)
			except Exception as e:
				logging.error('Error setting Memcache for lastProductsViewed in class ProductRequestHandler : %s' % e)

			params = {
					'product': productModel,
					'best_price': utils.dollar_float(float(best_price)),
					'requested_quantity': int(quantity),
					'total_cost': utils.dollar_float(float(best_price)*float(quantity))
					}

			self.bournee_template('product.html', **params)

		except Exception as e:
			logging.error('Error finding Product and/or Price in function doWork of ProductRequestHandler : %s' % e)
			message = _('We could not find a Price result for your Product Request. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


class GetProductFormHandler(BaseHandler):
	@user_required
	def post(self):
		try:
			if not self.addProduct_form.validate():
				raise Exception('addProduct_form did not Validate, in function POST of GetProductFormHandler')
			logging.info("addProduct_form Form Was valid")
			
			best_price = None
			productModel = None
			quantity = 1
			
			##: Try to fetch the data from the Form responce
			productNumber = str(self.addProduct_form.productNumber.data).strip() ##: Product Number
			urlsafeSellerKey = str(self.addProduct_form.urlsafeSellerKey.data).strip() ##: Urlsafe Seller Key
			urlsafeCartKey = str(self.request.POST.get('ck', None)).strip() ##: Urlsafe Cart Key Optional
			qnt = self.request.POST.get('qnt', None) ##: Urlsafe Seller Key
			logging.info('here')
			if qnt:
				try:
					quantity = int(qnt)
				except:
					logging.error('The quantity supplied in the form submission could not be converted into an integer')
					message = _('Sorry, the quantity supplied in the form submission was not valid. Please try again later.')
					self.add_message(message, 'error')
					try:
						self.redirect(self.request.referer)
					except:
						self.redirect_to('home')
			
			cleanProductNUmber = utils.clean_product_number(productNumber)
			logging.info('here')
			
			sellerKey = ndb.Key(urlsafe=urlsafeSellerKey)
			productKey = ndb.Key(shoppingModels.Product, cleanProductNUmber, parent=sellerKey)
			productModel = productKey.get()
			if not productModel:
				logging.info('here')
				
				########################################################################
				#################
				########   We don't have this product yet so we must Parse the website.
				#################
				########################################################################
				try:
					sellerModel = ndb.Key(urlsafe=urlsafeSellerKey).get()
					logging.info('here')
					
					if not sellerModel:
						raise Exception('Seller of requested product was not found.')
					if sellerModel.parser == 'DIGIKEY':
						# Call to parser
						logging.info('Product Number to search: {}'.format(productNumber))
						productModel, best_price_cents = parsers.DK_Search(sellerModel, str(productNumber), int(quantity))
					else:
						raise Exception('At this time we cannot get product info from Seller')

					# Check over results of Parser
					if not productModel:
						raise Exception('Missing a productModel from the parser response')
					if not best_price_cents:
						raise Exception('Missing a best_price_cents from the parser response')
					best_price = float(best_price_cents)/100 # convert to dollars
					productPriceTiers = shoppingModels.ProductTierPrice.get_for_product(productModel.pn, productModel.key)
					if not productPriceTiers:
						logging.info('Deferred to parser for Product Tiers')
						deferred.defer(parsers.parseDigiKey, productModel.key.urlsafe())
				
				except Exception as e:
					logging.error('Error creating a productModel: -- {}'.format(e))
					message = _('Sorry, we could not retrieve your product request. Please try again later.')
					self.add_message(message, 'error')
					try:
						return self.redirect(self.request.referer)
					except:
						return self.redirect_to('home')

			##: A Product Model was found
			else:
				logging.info('here')
				
				########################################################################
				#################
				########   Send to bestPrice script
				#################
				########################################################################
				try:
					best_price = bestPrice.getBestPrice(productModel.key.urlsafe(), int(quantity))
					if not best_price:
						raise Exception('Best price returned None for product number: {}'.format(productModel.pn))
				except Exception as e:
					logging.error('Error finding Product and/or Price in function getProduct of ProductRequestHandler : %s' % e)
					message = _('Sorry, we could not find a price result for your product request. Please try again later.')
					self.add_message(message, 'error')
					try:
						return self.redirect(self.request.referer)
					except:
						return self.redirect_to('home')
			logging.info('here')
			
			if not productModel or not best_price:
				raise Exception('Either the productModel or the best_price is missing')

			if urlsafeCartKey:
				logging.info('here')
				old_order_subtotal = 0
				
				cartModel = ndb.Key(urlsafe=urlsafeCartKey).get()
				if not cartModel:
					raise Exception('cartModel was not found using the urlsafeCartKey given in the form.')

				##: Check to see if user already created this Order within this Cart
				currentOrder = shoppingModels.Order.get_for_product_and_cart(cartModel.key, str(productModel.pn))

				##: Create or Update the Order Model
				if currentOrder:
					old_order_subtotal = currentOrder.st ##: must record the old subTotal before updating the QNT
					order = currentOrder.update_order_add_qnt(currentOrder, int(quantity), put_model=False)
				else:
					old_order_subtotal = 0
					order = shoppingModels.Order.create_order(cartModel.key, productModel.key, int(quantity), put_model=False)

				##: Update the Cart for the Totals Costs
				if order:
					##: Updatte the Cart's subtotals
					orderSubTotal = (int(order.st)-int(old_order_subtotal))
					oldCartSubTotal = cartModel.st
					newCartSubTotal = int(oldCartSubTotal) + int(orderSubTotal)
					shoppingModels.Cart.update_subtotal_values(cartModel, newCartSubTotal, oldCartSubTotal, put_model=False)

				ndb.put_multi( [cartModel, order] )
				logging.info('here')

				##: Run a check in the background to verify Cart Sub-Total
				deferred.defer(shoppingModels.verify_cart_subtotals, cartModel.key.urlsafe())
				logging.info('here')

				message = _('We have found the requested Product: {} and have added it to your cart {}.'.format(productModel.pn, cartModel.n))
				self.add_message(message, 'success')
			else:
				logging.info('here')
				
				message = _('We have saved the requested Product: {} to our database.'.format(productModel.pn))
				self.add_message(message, 'success')
			
		except Exception as e:
			logging.error('Error finding or creating Product in function post of GetProductFormHandler : %s' % e)
			message = _('Sorry, there was an error getting the Product requested. Please try again later.')
			self.add_message(message, 'error')
		finally:
			logging.info('here')
			
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def addProduct_form(self):
		return forms.AddProductForm(self)


class ClearLastProductsViewedHandler(BaseHandler):
	def post(self):
		try:
			deleteResult = memcache.delete('%s:lastProductsViewed' % str(self.request.remote_addr))
			message = _('Your last viewed products list has been cleared.')
			self.add_message(message, 'success')
		except Exception as e:
			logging.error('Error getting clearing memcache in class ClearLastProductsViewedHandler: -- {}'.format(e))
			message = _('An error occurred while clearing your last viewed products list. Please try again later.')
			self.add_message(message, 'error')
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')