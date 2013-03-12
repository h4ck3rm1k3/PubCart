#!/usr/bin/env python
# encoding: utf-8
"""
cartHandlers.py

Created by Jason Elbourne on 2013-02-21.
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
from google.appengine.datastore.datastore_query import Cursor

##:	 BournEE Imports
import forms as forms
from models import shoppingModels, userModels
from lib import bestPrice, utils
from lib.bourneehandler import RegisterBaseHandler, BournEEHandler
from lib.exceptions import FunctionException
from lib import paypal_settings as settings

##:	 Boilerplate Imports
from boilerplate import models
from boilerplate.lib.basehandler import user_required
from boilerplate.lib.basehandler import BaseHandler


class DiscoverCartsHandler(RegisterBaseHandler):
	def get(self):
		""" Returns a simple HTML form for home """
		try:
			carts = []
			allPublicCarts = shoppingModels.Cart.get_public_carts()
			if allPublicCarts:
				for cart in allPublicCarts:
					if cart.img == None: # TODO remove the None
						carts.append(cart)
				
			params = {'carts':carts}
			self.bournee_template('discoverCarts.html', **params)

		except Exception as e:
			params = {}
			logging.error('Error getting userCarts: -- {}'.format(e))
			message = _('An error occurred while fetching your carts. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


class MyCartsHandler(BournEEHandler):
	@user_required
	def get(self):
		try:
			params = {}
			self.bournee_template('mycarts.html', **params)

		except Exception as e:
			params = {}
			logging.error('Error getting userCarts: -- {}'.format(e))
			message = _('An error occurred while fetching your carts. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


class CreateCartInfoHandler(RegisterBaseHandler):
	def get(self):
		try:
			if self.user:
				return self.loggedin_get()
			params = {}
			self.bournee_template('createCart.html', **params)

		except Exception as e:
			logging.error('Error in function GET of handler CreateCartInfoHandler: -- {}'.format(e))
			message = _('An error occurred while fetching the requested page. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@user_required
	def loggedin_get(self):
		try:
			params = {'createCartForm': self.createCart_form,}
			self.bournee_template('createCartForm.html', **params)

		except Exception as e:
			logging.error('Error in function loggedin_get of handler CreateCartInfoHandler: -- {}'.format(e))
			message = _('An error occurred while fetching the requested page. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@user_required
	def post(self):
		try:
			if not self.createCart_form.validate():
				raise Exception('createCart_form did not Validate, in function POST of AddToCartHandler')
			logging.info("createCart_form Form Was valid")

			##: Try to fetch the data from the Form response
			cartName = str(self.createCart_form.name.data).strip()
			cartDescription = str(self.createCart_form.description.data).strip()
			cartCategory = str(self.createCart_form.category.data).strip()
			
			cartModel = shoppingModels.Cart.get_or_create_cart(self.user_key, urlsafeCartKey=None , cartName=cartName, \
														cartDescritpion=cartDescription, cartCategory=cartCategory)
			
			if not cartModel:
				raise Exception('Could not create cartModel from function get_or_create_cart()')
			
			self.redirect_to('fullPageCart', urlsafeCartKey=cartModel.key.urlsafe(), create=True)


		except Exception as e:
			params = {}
			logging.error('Error getting userCarts: -- {}'.format(e))
			message = _('An error occurred while fetching your carts. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
	
	@webapp2.cached_property
	def createCart_form(self):
		return forms.CreateCartForm(self)	


class FullPageCartHandler(RegisterBaseHandler):
	"""
	Handler to view full page of cart items.
	"""
	def get(self, urlsafeCartKey):
		try:
			##: Make Sure if the cart is Private the owner (userKey) is viewing it.
			cartKey = ndb.Key(urlsafe=urlsafeCartKey)
			cart = cartKey.get()
			if not cart:
				raise Exception('No Cart Found')
			self.do_work(cart)

		except Exception as e:
			logging.error('Error in handler <get> of class - \
						FullPageCartHandler : -- {}'.format(e))
			message = _('We are having difficulties displaying the Full Cart \
						Page. Please try again later.')
			self.add_message(message, 'error')
			self.redirect_to('home')
	
	def public_cart(self, userID, cartName):
		try:
			cartOwnerInfo = models.User.get_by_id(long(userID))
			if cartOwnerInfo:
				cartOwnerKey = cartOwnerInfo.key
				cartKey = ndb.Key(shoppingModels.Cart, str(cartName).upper(), \
						parent=cartOwnerKey)
				
				cart = cartKey.get()
				if cart:
					self.do_work(cart)
				else:
					raise Exception('No Cart Found')
			else:
				raise Exception('No Cart Owner (User Model) Found')
		except Exception as e:
			logging.error('Error in handler <public_cart> of class - \
						FullPageCartHandler : -- {}'.format(e))
			message = _('We are having difficulties displaying the Full \
						Cart Page. Please try again later.')
			self.add_message(message, 'error')
			self.redirect_to('home')
	
	def do_work(self, cart):
		try:
			cartOwner = False

			if self.user:
				if cart.uk == self.user_key:
					cartOwner = True

			##: Very important to have a User for Private Carts (Shopping Carts)
			##: and if a user than the user_key must match the cart's user_key
			if not cart.public:
				if not cartOwner:
					raise Exception('User doing request does not match the \
						owner of the cart, this is a must for Private Carts')


			productOrders = shoppingModels.Order.get_for_cart(cart.key)
			
			createCart = self.request.get('create', None) ##: The create flag for showing the add Product Form at the top of the page
			a = self.request.get('a', None) ##: Address urlsafe Key

			defaultAddress = None
			if a and self.user:
				deferred.defer( \
						userModels.set_default_address, \
						a, ##: a = Address urlsafe key \
						self.user_key \
						) 
			if a:
				defaultAddress = ndb.Key(urlsafe=a).get()
			elif self.user:
				defaultAddress = userModels.Address.query( \
						userModels.Address.is_default == True, \
						ancestor=self.user_key).get()
			else:
				defaultAddress = None

			if cart.n: self.forkCart_form.name.data = cart.n
			if cart.d:
				self.cartDetails_form.description.data = cart.d
				self.forkCart_form.description.data = cart.d
				
			if cart.cat:
				self.cartDetails_form.category.data = cart.cat
				self.forkCart_form.category.data = cart.cat

			params = {
				"productOrders" 	: productOrders, \
				"urlsafeCartKey"	: cart.key.urlsafe(), \
				"createCart"		: createCart, \
				"cart"				: cart, \
				"cartOwner"			: cartOwner, \
				"cartDetailsForm"	: self.cartDetails_form, \
				"forkCartForm"		: self.forkCart_form, \
				"addressForm"		: self.addAddress_form, \
				"addProductForm"	: self.addProduct_form, \
				"address"			: defaultAddress, \
				"userAddresses"		: self.userAddresses, \
				}

			self.bournee_template('fullCart.html', **params)

		except Exception as e:
			logging.error('Error in handler <do_work> in class - \
						FullPageCartHandler : -- {}'.format(e))
			message = _('We are having difficulties displaying the \
						Full Cart Page. Please try again later.')
			self.add_message(message, 'error')
			self.redirect_to('home')
	
	@webapp2.cached_property
	def addAddress_form(self):
		return forms.AddAddressForm(self)

	@webapp2.cached_property
	def cartDetails_form(self):
		return forms.CartDetailsForm(self)

	@webapp2.cached_property
	def forkCart_form(self):
		return forms.ForkCartForm(self)

	@webapp2.cached_property
	def addProduct_form(self):
		return forms.AddProductForm(self)


class AddToCartHandler(BaseHandler):
	""" 
		Handles the submission of an Order either to a Shopping Cart or a
		BeList Cart, then Redirects to a different Handler
	"""
	## Login Required
	@user_required
	def post(self):
		try:
			if not self.addToCart_form.validate():
				raise Exception('addToCart_form did not Validate, in function \
				 				POST of AddToCartHandler')
			
			logging.info("addToCart_form Form Was valid")
			
			order = None
			cart = None
			cartName = None
			urlsafeCartKey = None
			old_order_subtotal = 0
			
			##: Try to fetch the data from the Form responce
			urlsafeProductKey = str(self.addToCart_form.pk.data).strip()
			cartName = str(self.addToCart_form.cn.data).strip().upper()
			urlsafeCartKey = str(self.addToCart_form.ck.data).strip()
			qnt = self.addToCart_form.q.data ##: Quantity
			
			logging.info("{}, {}".format(urlsafeCartKey, type(urlsafeCartKey)))
			logging.info("{}, {}".format(cartName, type(cartName)))
			
			##: This is important for when user selects a cart to use for adding product and wished to creat a new private cart.
			if urlsafeCartKey == 'None' and cartName == '':
				urlsafeCartKey = None
				cartName = 'SHOPPING'
			
			logging.info("{}, {}".format(cartName, type(cartName)))
			
			##: Try to find the part in the Datastore and get Best Price. 
			productModel, orderPrice = bestPrice.getBestPrice(urlsafeProductKey, None, int(qnt))

			if productModel:
				logging.info("Found a productModel")

				##: Initialize a variable for orderPrice with the part's current Best Unit Price
				if not orderPrice:
					orderPrice = int(productModel.bup)
				else:
					orderPrice = int(orderPrice*100)
				logging.info("Best Price so far in AddToCartHandler : %s -- (This should be an integer)" % str(orderPrice))

				##: Get or create the Cart
				cart = shoppingModels.Cart.get_or_create_cart(self.user_key, urlsafeCartKey=urlsafeCartKey , cartName=str(cartName))
				if not cart:
					logging.info("Did not Find a Cart")
					raise Exception('No Cart returned, error creating Cart, in function POST of AddToCartHandler')

				##: Check to see if user already created this Order within this Cart
				currentOrder = shoppingModels.Order.get_for_product_and_cart(cart.key, str(productModel.pn))

				##: Create or Update the Order Model
				if currentOrder:
					old_order_subtotal = currentOrder.st ##: must record the old subTotal before updating the QNT
					order = currentOrder.update_order_add_qnt(currentOrder, int(qnt), put_model=False)
				else:
					order = shoppingModels.Order.create_order(cart.key, productModel.key, int(qnt), put_model=False)

				##: Update the Cart for the Totals Costs
				if order:
					##: Updatte the Cart's subtotals
					orderSubTotal = (int(order.st)-int(old_order_subtotal))
					oldCartSubTotal = cart.st
					newCartSubTotal = int(oldCartSubTotal) + int(orderSubTotal)
					shoppingModels.Cart.update_subtotal_values(cart, newCartSubTotal, oldCartSubTotal, put_model=False)

				ndb.put_multi( [cart, order] )

				##: Run a check in the background to verify Cart Sub-Total
				deferred.defer(shoppingModels.verify_cart_subtotals, cart.key.urlsafe())

				logging.info("We have a order_key and a cart_key so Success and Redirect")
				message = _('Submission request successful for Product number -	 %s' % str(productModel.pn))
				self.add_message(message, 'success')
			else:
				raise Exception('No keys returned, error creating Cart/Order Item, in function POST of AddToCartHandler')

		except Exception as e:
			logging.error('Error in function POST of AddToCartHandler : --	%s' % e)
			message = _('We are having difficulties with finalizing the Order Submission. Please try again later.')
			self.add_message(message, 'error')
		
		finally:
			logging.info('Finished now Redirect to Referrer')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


	@webapp2.cached_property
	def addToCart_form(self):
		return forms.AddToCartForm(self)


class DeleteOrderFromCartHandler(BaseHandler):
	""" Handles the submission of a Exchange Order, then Redirects to a different Handler"""
	## Login Required
	@user_required
	def post(self):
		try:
			if not self.deleteFromCart_form.validate():
				raise Exception('deleteFromCart_form did not Validate, in function POST of DeleteFromCartHandler')
			logging.info("deleteFromCart_form Form Was valid")
			
			##: Try to fetch the data from the Form responce
			urlsafeCartKey = str(self.deleteFromCart_form.ck.data.strip()) ##: Urlsafe Key
			urlsafeOrderKey = str(self.deleteFromCart_form.ok.data.strip()) ##: Urlsafe Key
			orderSubTotal = self.deleteFromCart_form.ost.data

			if urlsafeCartKey and urlsafeOrderKey:
				cartKey = ndb.Key(urlsafe=urlsafeCartKey)
				cart = cartKey.get()
				if cart:
					##: Convert orderKey back to Normal
					orderKey = ndb.Key(urlsafe=urlsafeOrderKey)
					if cart.key != orderKey.parent():
						logging.error('The order being modified does not have a parent matching this cart')
						message = _('Your request could not be completed at this time. Please try again later.')
						self.add_message(message, 'error')
					elif cart.uk == self.user_key:
						##: Updatte the Cart's subtotals
						oldCartSubTotal = cart.st
						newCartSubTotal = int(oldCartSubTotal) - int(orderSubTotal)
						shoppingModels.Cart.update_subtotal_values(cart, newCartSubTotal, oldCartSubTotal)
						
						orderKey.delete()
						
						##: Run a check in the background to verify Cart Sub-Total
						deferred.defer(shoppingModels.verify_cart_subtotals, urlsafeCartKey) ##: cartKey is URLSAFE

						logging.info("We have removed the Order Item form the Cart and we Redirect to referrer")
						message = _('We have removed the Order Item form the Cart')
						self.add_message(message, 'success')
					else:
						logging.error("User Keys did not match between User and Cart Owner")
						message = _('You do not appear to be the owner of this Cart. We can not complete request.')
						self.add_message(message, 'error')
				else:
					logging.error("Cart was not Found")
					message = _('There was an Error during form Submission. We can not complete request. Please try again Later')
					self.add_message(message, 'error')
			else:
				logging.error("CartKey or OrderKey not received from the Form Submission")
				message = _('There was an Error during form Submission. We can not complete request. Please try again Later')
				self.add_message(message, 'error')

		except Exception as e:
			logging.error("Error occurred running function POST of class DeleteOrderFromCartHandler: -- %s" % str(e))
			message = _('There was an Error during form Submission. We can not complete request. Please try again Later')
			self.add_message(message, 'error')

		finally:
			logging.debug('Redirecting to Referer')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
					

	@webapp2.cached_property
	def deleteFromCart_form(self):
		return forms.DeleteFromCartForm(self)


class ChangeQuantityOfOrderHandler(BaseHandler):
	""" Handles the submission of a Exchange Order, then Redirects to a different Handler"""
	## Login Required
	@user_required
	def post(self):
		try:
			if not self.chgQntOfOrder_form.validate():
				raise FunctionException('chgQntOfOrder_form did not Validate, in function POST of ChangeQuantityOfOrderHandler')
			
			logging.info("chgQntOfOrder_form Form Was valid")
			
			oldOrderSubtotal = 0
			newOrderSubTotal = 0
			
			##: Try to fetch the data from the Form responce
			urlsafeCartKey = str(self.chgQntOfOrder_form.ck.data.strip())
			urlsafeOrderKey = str(self.chgQntOfOrder_form.ok.data.strip())
			quantity = self.chgQntOfOrder_form.q.data
			
			if urlsafeCartKey and urlsafeOrderKey:

				##: Get the Cart to check ownership
				cart = ndb.Key(urlsafe=urlsafeCartKey).get()

				if cart:
					logging.info('Cart Found')

					if cart.uk == self.user_key:
						logging.info('User Keys Match')

						order = ndb.Key(urlsafe=urlsafeOrderKey).get() ##: Get from Datastore
						if order:
							if int(order.q) == int(quantity):
								logging.info('The new Quantity is the same as the existing quantity, so we do nothing.')
							elif cart.key != order.key.parent():
								logging.error('The order being modified does not have a parent matching this cart')
							else:
								oldOrderSubtotal = int(order.st)
								order.update_order_new_qnt(order, quantity, put_model=False)
								newOrderSubTotal = int(order.st)
								
								##: Work on Sub-totals
								if int(oldOrderSubtotal) == int(newOrderSubTotal):
									logging.info('The new Sub-Total is the same as the existing Sub-Total, so we do nothing.')
								else:
									logging.info('Quantities are different, so we update Order')
									
									orderSubTotal = int(newOrderSubTotal) - int(oldOrderSubtotal)
									oldCartSubTotal = cart.st
									newCartSubTotal = oldCartSubTotal + orderSubTotal
									shoppingModels.Cart.update_subtotal_values(cart, newCartSubTotal, oldCartSubTotal, put_model=False)

								##: Now we save both the Cart and the Order using put_multi()
								ndb.put_multi( [cart, order] )

								logging.info('We have keys returned for the put_multi on both the Cart and the Order')
								##: Run a check in the background to verify Cart Sub-Total
								deferred.defer(shoppingModels.verify_cart_subtotals, cart.key.urlsafe()) ##: cartKey is URLSAFE
								
								##: All Done
								logging.info("We have updated the Order Quantity and we Redirect to referrer thru <finally:> block")
								message = _('We have updated the %s Order Quantity to: %s' % (str(order.pn), str(order.q)))
								self.add_message(message, 'success')
						else:
							##: Missing Order
							logging.error('Error - Order not found using given Order Key')
							message = _('There was an Error during form submission updating your order. Please try again later')
							self.add_message(message, 'error')
					else:
						logging.error("User Keys did not match between User and Cart Owner")
						message = _('You do not appear to be the owner of this Cart. We can not complete request.')
						self.add_message(message, 'error')
				else:
					logging.error("Cart was not Found")
					message = _('There was an Error during form Submission. We can not complete request. Please try again later')
					self.add_message(message, 'error')
			else:
				logging.error("CartKey or OrderKey not received from the Form Submission")
				message = _('There was an Error during form Submission. We can not complete request. Please try again later')
				self.add_message(message, 'error')
			
		except Exception as e:
			logging.error("Error occurred running function POST of class ChangeQuantityOfOrderHandler: -- %s" % str(e))
			message = _('There was an Error during form Submission. We can not complete request. Please try again later')
			self.add_message(message, 'error')

		finally:
			logging.debug('Redirecting to Referer')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def chgQntOfOrder_form(self):
		return forms.ChangeQntOfOrderForm(self)



class AddToSelectedCartFormHandler(BournEEHandler):
	"""
	Handler for the Products Exchange order form and info page.
	"""
	@user_required
	def get(self, urlsafeProductKey):
		""" Returns page containing part info and exchange order form """
		try:
			q = self.request.GET.get('q', 1)
			##: Make Sure quantity from URL is an integer
			qnt = int(q)
			
			self.do_work(urlsafeProductKey, qnt)

		except Exception as e:
			logging.error('Error, function GET of class AddToSelectedCartFormHandler: -- %s' % str(e))
			message = _('We are having difficulties displaying the form at this time. Please check your entry and try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@user_required
	def post(self, urlsafeProductKey):
		"""
		This POST method is used to update the product quantity for the order best price
		"""
		try:
			if not self.simpleChangeQNT_form.validate():
				raise FunctionException('simpleChangeQNT_form did not Validate, in function POST of ChangeQuantityOfOrderHandler')
			
			logging.info("simpleChangeQNT_form Form Was valid")
			
			##: Try to fetch the data from the Form responce
			urlsafePK = str(self.simpleChangeQNT_form.pk.data).strip()
			q = self.simpleChangeQNT_form.q.data
			##: Make Sure quantity from URL is an integer
			qnt = int(q)
			
			if urlsafePK == urlsafeProductKey:
				self.do_work(urlsafeProductKey, qnt)
			else:
				raise Exception('Urlsafe Product Keys did not match between URI and Form data.')

		except Exception as e:
			logging.error('Error, function POST of class AddToSelectedCartFormHandler: -- %s' % str(e))
			message = _('We are having difficulties updating the Requested Product Quantity. Please check your entry and try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	def do_work(self, urlsafeProductKey, qnt):
		try:
			##: Get the Product Model and Best Price
			productModel, best_price = bestPrice.getBestPrice( urlsafeProductKey , None, int(qnt))
			if best_price == None:
				logging.error('Error, Best Price not determined. ')
				raise Exception('Best Price not determined.')
			if productModel == None:
				logging.error('Error, No Product Model Found ')
				raise Exception('No Product Model Found using urlsafe key')

			##: Run a query for existing Carts the user has. (PUBLIC Carts)
			cartList = shoppingModels.Cart.get_carts_for_user(self.user_key)

			params =	{'product': productModel,
						'cartList': cartList,
						'requested_quantity': int(qnt),
						'best_price': utils.dollar_float(float(best_price)),
						'total_cost': utils.dollar_float(float(best_price)*float(qnt)),}
		
			self.bournee_template('selectCartForm.html', **params)

		except Exception as e:
			logging.error('Error, function do_work of class AddToSelectedCartFormHandler: -- %s' % str(e))
			message = _('We are having difficulties displaying the form at this time. Please check your entry and try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def simpleChangeQNT_form(self):
		return forms.SimpleChangeQNTForm(self)


class MakeCartPublicHandler(BournEEHandler):
	@user_required
	def get(self, urlsafeCartKey):
		try:
			cart = ndb.Key(urlsafe=urlsafeCartKey).get()
			if cart:
				if cart.n: self.forkCart_form.name.data = cart.n
				if cart.d: self.forkCart_form.description.data = cart.d
				if cart.cat: self.forkCart_form.category.data = cart.cat
				
				params = {
					"cartDetailsForm" : self.cartDetails_form, \
					"forkCartForm" : self.forkCart_form, \
					"urlsafeCartKey": urlsafeCartKey, \
					"cart": cart, \
					}
				self.bournee_template('forkCartForm.html', **params)
			else:
				logging.error("Could not find cart in function GET of class MakeCartPublicFormHandler")
				message = _('There was an Error fetching the cart data. We can not complete request at this time. Please try again later')
				self.add_message(message, 'error')
				try:
					self.redirect(self.request.referer)
				except:
					self.redirect_to('home')
		except Exception as e:
			logging.error("Error occurred running function GET of class MakeCartPublicFormHandler: -- %s" % str(e))
			message = _('There was an Error on the servers. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
	
	@user_required
	def post(self, urlsafeCartKey):
		try:
			if not self.forkCart_form.validate():
				self.get(urlsafeCartKey)
			
			logging.info("cartDetails_form Form Was valid")
			
			entitiesToPut = []
			entitiesToDelete = []
			
			##: Try to fetch the data from the Form responce
			formUrlsafeCartKey = str(self.forkCart_form.ck.data).strip()
			cartName = str(self.forkCart_form.name.data).strip()
			cartDescription = str(self.forkCart_form.description.data).strip()
			cartCategory = str(self.forkCart_form.category.data).strip()
			if urlsafeCartKey == formUrlsafeCartKey:
				cart = ndb.Key(urlsafe=urlsafeCartKey).get()
				if cart:

					forkedCart = utils.clone_entity(cart, 
													n = cartName, \
													d = cartDescription, \
													cat = cartCategory, \
													public = True, \
													default = False, \
													)
					forkedCart.key = ndb.Key(shoppingModels.Cart, str(cartName).strip().upper(), parent=self.user_key)

					entitiesToPut = [forkedCart]

					orderItems = shoppingModels.Order.get_for_cart(cart.key)
					if orderItems:
						forkedOrderKeyList = []
						for orderItem in orderItems:
							logging.info(orderItem)
							entitiesToDelete.append(orderItem.key)
							keyname = orderItem.key.id()
							forkedOrder = utils.clone_entity(orderItem, ck=forkedCart.key)
							forkedOrder.key = ndb.Key(shoppingModels.Order, keyname, parent=forkedCart.key)
							entitiesToPut.append(forkedOrder)

					if len(entitiesToPut) > 1:
						ndb.put_multi(entitiesToPut)
					elif len(entitiesToPut) == 1:
						entitiesToPut[0].put()
					
					if len(entitiesToDelete) > 1:
						ndb.delete_multi(entitiesToDelete)
					elif len(entitiesToDelete) == 1:
						entitiesToDelete[0].delete()

					logging.error("Cart has been updated to Public status")
					message = _('Cart has been updated to Public status')
					self.add_message(message, 'success')
				else:
					logging.error("Error occurred running function POST of class MakeCartPublicFormHandler")
					message = _('There was an Error converting cart to public. We can not complete request at this time. Please try again later')
					self.add_message(message, 'error')
				
				self.redirect_to('fullPageCart', urlsafeCartKey = forkedCart.key.urlsafe())
					
			else:
				raise Exception("The urlsafe keys did not match from URI and form data")

		except Exception as e:
			logging.error("Error occurred running function POST of class MakeCartPublicFormHandler: -- %s" % str(e))
			message = _('There was an Error during form submission. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def cartDetails_form(self):
		return forms.CartDetailsForm(self)

	@webapp2.cached_property
	def forkCart_form(self):
		return forms.ForkCartForm(self)

class MakeCartDefaultFormHandler(BaseHandler):
	@user_required
	def post(self):
		try:
			if not self.makeCartDefault_form.validate():
				raise Exception('MakeCartDefault Form was not valid')
			logging.info("makeCartDefault_form Form Was valid")
			
			##: Try to fetch the data from the Form responce
			urlsafeCartKey = str(self.makeCartDefault_form.ck.data).strip()
			shoppingModels.Cart.update_default_cart(self.user_key, urlsafeCartKey)
			
			message = _('Default Cart has been changed.')
			self.add_message(message, 'success')

		except Exception as e:
			logging.error("Error occurred running function POST of class MakeCartDefaultFormHandler: -- %s" % str(e))
			message = _('There was an Error during form submission to make cart default. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def makeCartDefault_form(self):
		return forms.MakeCartDefaultForm(self)

class DeleteCartHandler(BournEEHandler):
	@user_required
	def post(self):
		try:
			if not self.deleteCart_form.validate():
				raise Exception('deleteCart_form Form was not valid')
			logging.info("deleteCart_form Form Was valid")
			
			entitiesToDelete = []
			##: Try to fetch the data from the Form responce
			urlsafeCartKey = str(self.deleteCart_form.ck.data).strip()
			cartKey = ndb.Key(urlsafe=urlsafeCartKey)
			cart = cartKey.get()
			
			if cart:
				if self.user_key == cart.uk:
					cartName = cart.n
					if cart.public:
						cart.garbage = True
						cart.put()
						message = _('The Cart {} has been removed from your list.'.format(cart.n))
						self.add_message(message, 'success')
					else:
						entitiesToDelete.append(cartKey)
						if cart.default:
							shoppingModels.Cart.update_default_cart(self.user_key)
						cartOrders = shoppingModels.Order.get_for_cart(cartKey)
						if cartOrders:
							for order in cartOrders:
								entitiesToDelete.append(order.key)
						if len(entitiesToDelete) == 1:
							logging.info('Here')
							entitiesToDelete[0].delete()
						elif len(entitiesToDelete) > 1:
							logging.info('Here')
							ndb.delete_multi(entitiesToDelete)
						logging.info('Cart and orders were deleted successfuly')
						message = _('The Cart {} has been deleted.'.format(cartName))
						self.add_message(message, 'success')
				else:
					raise Exception('User keys did not match from session user to cart owner')
			else:
				raise Exception('Could not find cart using urlsafeCartKey from form data')

		except Exception as e:
			logging.error("Error occurred running function POST of class DeleteCartHandler: -- %s" % str(e))
			message = _('There was an Error during form submission to delete cart. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
	
	@webapp2.cached_property
	def deleteCart_form(self):
		return forms.DeleteCartForm(self)

class EditCartDetailsFormHandler(BournEEHandler):
	@user_required
	def get(self, urlsafeCartKey):
		try:
			cart = ndb.Key(urlsafe=urlsafeCartKey).get()
			if cart:
				if cart.d: self.cartDetails_form.description.data = cart.d
				if cart.cat: self.cartDetails_form.category.data = cart.cat

				params = {
					"cartDetailsForm" : self.cartDetails_form, \
					"forkCartForm" : self.forkCart_form, \
					"urlsafeCartKey": urlsafeCartKey, \
					"cart": cart, \
					}
				self.bournee_template('editCartDetailsForm.html', **params)
			else:
				logging.error("Could not find cart in function GET of class EditCartDetailsFormHandler")
				message = _('There was an Error fetching the cart data. We can not complete request at this time. Please try again later')
				self.add_message(message, 'error')
				try:
					self.redirect(self.request.referer)
				except:
					self.redirect_to('home')
		except Exception as e:
			logging.error("Error occurred running function GET of class EditCartDetailsFormHandler: -- %s" % str(e))
			message = _('There was an Error on the servers. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@user_required
	def post(self, urlsafeCartKey):
		try:
			if not self.cartDetails_form.validate():
				logging.info("cartDetails_form Form Was not valid")
				return self.get(urlsafeCartKey)
			
			logging.info("cartDetails_form Form Was valid")

			##: Try to fetch the data from the Form responce
			formUrlsafeCartKey = str(self.cartDetails_form.ck.data).strip()
			cartDescription = str(self.cartDetails_form.description.data).strip()
			cartCategory = str(self.cartDetails_form.category.data).strip()

			if urlsafeCartKey == formUrlsafeCartKey:
				cart = ndb.Key(urlsafe=urlsafeCartKey).get()
				if cart:
					shoppingModels.Cart.update_cart_details(cart, cartDescription, cartCategory)
					return self.redirect_to('fullPageCart', urlsafeCartKey = urlsafeCartKey)
			##: If we get here there has been an error
			raise Exception("Either the cartKeys did not match or we could not find a Cart with the key.")
			
		except Exception as e:
			logging.error("Error occurred running function POST of class EditCartDetailsFormHandler: -- %s" % str(e))
			message = _('There was an Error during form submission. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def cartDetails_form(self):
		return forms.CartDetailsForm(self)
	#
	@webapp2.cached_property
	def forkCart_form(self):
		return forms.ForkCartForm(self)


class ForkCartHandler(BournEEHandler):
	@user_required
	def get(self, urlsafeCartKey):
		try:
			cart = ndb.Key(urlsafe=urlsafeCartKey).get()
			if cart:
				if cart.d: self.forkCart_form.description.data = cart.d
				if cart.cat: self.forkCart_form.category.data = cart.cat

				params = {
					"forkCartForm" : self.forkCart_form, \
					"cartDetailsForm" : self.cartDetails_form, \
					"urlsafeCartKey": urlsafeCartKey, \
					"cart": cart, \
					}
				self.bournee_template('forkCartForm.html', **params)
			else:
				logging.error("Could not find cart in function GET of class MakeCartPublicFormHandler")
				message = _('There was an Error fetching the cart data. We can not complete request at this time. Please try again later')
				self.add_message(message, 'error')
				try:
					self.redirect(self.request.referer)
				except:
					self.redirect_to('home')
		except Exception as e:
			logging.error("Error occurred running function GET of class MakeCartPublicFormHandler: -- %s" % str(e))
			message = _('There was an Error on the servers. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')
	
	@user_required
	def post(self, urlsafeCartKey):
		try:
			if not self.forkCart_form.validate():
				logging.info("forkCart_form Form Was not valid")
				return self.get(urlsafeCartKey)
			
			logging.info("forkCart_form Form Was valid")

			##: Try to fetch the data from the Form responce
			formUrlsafeCartKey = str(self.forkCart_form.ck.data).strip()
			cartName = str(self.forkCart_form.name.data).strip()
			cartDescription = str(self.forkCart_form.description.data).strip()
			cartCategory = str(self.forkCart_form.category.data).strip()

			if urlsafeCartKey == formUrlsafeCartKey:
				cart = ndb.Key(urlsafe=urlsafeCartKey).get()
				if cart:

					forkedCart = utils.clone_entity(cart, 
													n = cartName, \
													d = cartDescription, \
													cat = cartCategory, \
													public = False, \
													default = False, \
													)
					forkedCart.key = ndb.Key(shoppingModels.Cart, str(cartName).strip().upper(), parent=self.user_key)

					entitiesToPut = [forkedCart]
					
					orderItems = shoppingModels.Order.get_for_cart(cart.key)
					if orderItems:
						forkedOrderKeyList = []
						for orderItem in orderItems:
							logging.info(orderItem)
							keyname = orderItem.key.id()
							forkedOrder = utils.clone_entity(orderItem, ck=forkedCart.key)
							forkedOrder.key = ndb.Key(shoppingModels.Order, keyname, parent=forkedCart.key)
							entitiesToPut.append(forkedOrder)
							forkedOrderKeyList.append(forkedOrder.key)
					if len(entitiesToPut) > 1:
						ndb.put_multi(entitiesToPut)
					elif len(entitiesToPut) == 1:
						entitiesToPut[0].put()

					logging.info('Here')
					return self.redirect_to('fullPageCart', urlsafeCartKey = forkedCart.key.urlsafe())
			##: If we get here there has been an error
			raise Exception("Either the cartKeys did not match or we could not find a Cart with the key.")
			
		except Exception as e:
			logging.error("Error occurred running function POST of class ForkCartFormHandler: -- %s" % str(e))
			message = _('There was an Error during form submission. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def forkCart_form(self):
		return forms.ForkCartForm(self)
	#
	@webapp2.cached_property
	def cartDetails_form(self):
		return forms.CartDetailsForm(self)

class CopyOrderBetweenCartsHandler(BaseHandler):
	@user_required
	def post(self):
		try:
			if not self.copyOrder_form.validate():
				raise Exception("copyOrder_form did not validate.")
			logging.info("cartDetails_form Form Was valid")
			
			cartOwner = False
			entitiesToPut = []
			orderItemKeys = []
			orderItems = []
			ordersToDeleteKeys = []
			deletedOrderItemsSubTotal = 0
			copiedOrderItemsSubTotal = 0

			##: Try to fetch the data from the Form responce
			originalUrlsafeCartKey = str(self.copyOrder_form.ock.data).strip()
			newUrlsafeCartKey = str(self.copyOrder_form.nck.data).strip()
			newCart = ndb.Key(urlsafe=newUrlsafeCartKey).get()
			originalCart = ndb.Key(urlsafe=originalUrlsafeCartKey).get()

			if newCart and originalCart:
				if self.user:
					if originalCart.uk == self.user_key:
						cartOwner = True

				newCart_oldSubTotal = newCart.st
				
				urlsafeOrderKey_values = self.request.get('oks', allow_multiple=True)
				if cartOwner:
					deleteItemsBoolean = self.request.get('di', None)
				else:
					deleteItemsBoolean = None

				logging.info(urlsafeOrderKey_values)
				if urlsafeOrderKey_values:
					if len(urlsafeOrderKey_values) == 1:
						orderItems = [ndb.Key(urlsafe=urlsafeOrderKey_values[0]).get()]
					elif len(urlsafeOrderKey_values) > 1:
						orderKey_values = [ndb.Key(urlsafe=urlsafeOrderKey) for urlsafeOrderKey in urlsafeOrderKey_values]
						orderItems = ndb.get_multi(orderKey_values)

					for orderItem in orderItems:
						if deleteItemsBoolean and cartOwner:
							ordersToDeleteKeys.append(orderItem.key)
							deletedOrderItemsSubTotal += orderItem.st
							
						keyname = orderItem.key.id()
						forkedOrderKey = ndb.Key(shoppingModels.Order, keyname, parent=newCart.key)
						forkedOrder = forkedOrderKey.get()
						if not forkedOrder:
							copiedOrderItemsSubTotal += orderItem.st
							forkedOrder = utils.clone_entity(orderItem, ck=newCart.key)
							forkedOrder.key = forkedOrderKey
							entitiesToPut.append(forkedOrder)

					if len(entitiesToPut) > 0:
						if deleteItemsBoolean and cartOwner:
							##: We have the orginal Cart so we Delete the orders requested
							if len(ordersToDeleteKeys) > 1:
								ndb.delete_multi(ordersToDeleteKeys)
								logging.info('Order items have been deleted during Order Copy in class CopyOrderBetweenCartsHandler')
							elif len(ordersToDeleteKeys) == 1:
								ordersToDeleteKeys[0].delete()
								logging.info('Order items have been deleted during Order Copy in class CopyOrderBetweenCartsHandler')
							##: Now we must update the Cart subtotals
							oldSubTotal = originalCart.st
							newSubTotal = (oldSubTotal - deletedOrderItemsSubTotal)
							shoppingModels.Cart.update_subtotal_values(originalCart, newSubTotal, oldSubTotal, put_model=False)
							entitiesToPut.append(originalCart)

							##: Run a check in the background to verify Cart Sub-Total
							deferred.defer(shoppingModels.verify_cart_subtotals, originalUrlsafeCartKey) ##: cartKey is URLSAFE

						##:	 Now lets update the New Carts SubTotal
						oldSubTotal = newCart.st
						newSubTotal = (oldSubTotal + copiedOrderItemsSubTotal)
						shoppingModels.Cart.update_subtotal_values(newCart, newSubTotal, oldSubTotal, put_model=False)

						entitiesToPut.append(newCart)
						ndb.put_multi(entitiesToPut)
						
						##: Run a check in the background to verify Cart Sub-Total
						deferred.defer(shoppingModels.verify_cart_subtotals, newUrlsafeCartKey) ##: cartKey is URLSAFE

						logging.error("The Order items have been copied.")
						message = _('The Order items have been copied to the Cart named {}'.format(newCart.n))
						self.add_message(message, 'success')
					else:
						logging.error("All orders selected were already in the other Cart")
						message = _('All the orders selected were already in the Cart named {}'.format(newCart.n))
						self.add_message(message, 'error')
				else:
					logging.error("None of the orders were selected for the form submission")
					message = _('You did not select any of the orders below.')
					self.add_message(message, 'error')
			else:
				logging.error("Cart was not found in function POST of class CopyOrderBetweenCartsHandler")
				raise Exception("Cart was not found in function POST of class CopyOrderBetweenCartsHandler")

		except Exception as e:
			logging.error("Error occurred running function POST of class CopyOrderBetweenCartsHandler: -- %s" % str(e))
			message = _('There was an Error during form submission. We can not complete request at this time. Please try again later')
			self.add_message(message, 'error')
		finally:
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

	@webapp2.cached_property
	def copyOrder_form(self):
		return forms.CopyOrderForm(self)	