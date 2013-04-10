#!/usr/bin/env python
# encoding: utf-8
"""
tabHandlers.py

Created by Jason Elbourne on 2013-04-02.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:	 Python Imports
import re
import time
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
from lib.livecount import counter
from lib.bourneehandler import RegisterBaseHandler, BournEEHandler, user_required
from lib.exceptions import FunctionException
from lib import paypal_settings as settings

##:	 Boilerplate Imports
from boilerplate.lib.basehandler import BaseHandler


class PaidTabsRequestHandler(BournEEHandler):
	@user_required
	def get(self):
		pass


class ViewTabRequestHandler(BournEEHandler):
	@user_required
	def get(self, urlsafeTabKey):
		pass


class AddToTabHandler(BournEEHandler):
	@user_required
	def post(self):
		try:
			if not self.addToTab_form.validate():
				raise Exception('addToTab_form did not Validate, in function \
				 				POST of AddToTabHandler')

			logging.info("addToTab_form Form Was valid")
			
			order = None
			old_order_subtotal = 0
			
			##: Try to fetch the data from the Form responce
			urlsafeProductKey = str(self.addToTab_form.pk.data).strip()
			urlsafeUserKey = str(self.addToTab_form.uk.data).strip()
			qnt = self.addToTab_form.q.data ##: Quantity

			##: Must have both urlsafeUserKey and urlsafeProductKey
			if not urlsafeUserKey or not urlsafeProductKey:
				logging.error("Error, Missing urlsafeUserKey or urlsafeProductKey")
			
			##: Try to find the part in the Datastore and get Best Price. 
			productModel, orderPrice = bestPrice.getBestPrice(urlsafeProductKey, int(qnt), returnProductModel=True)

			if productModel:
				logging.info("Found a productModel")

				##: Initialize a variable for orderPrice with the part's current Best Unit Price
				if not orderPrice:
					orderPrice = int(productModel.bup)
				else:
					orderPrice = int(orderPrice*100)
				logging.info("Best Price so far in AddToTabHandler : %s -- (This should be an integer)" % str(orderPrice))

				##: Get or create the Cart
				tab = shoppingModels.Tab.get_or_create_tab(self.user_key)
				if not tab:
					logging.info("Did not Find a Tab")
					raise Exception('No Tab returned, error creating Tab, in function POST of AddToTabHandler')

				##: Check to see if user already created this Order within this Cart
				currentOrder = shoppingModels.Order.get_for_product_and_parent(tab.key, str(productModel.pn))

				##: Create or Update the Order Model
				if currentOrder:
					old_order_subtotal = currentOrder.st ##: must record the old subTotal before updating the QNT
					order = currentOrder.update_order_add_qnt(currentOrder, int(qnt), put_model=False)
				else:
					order = shoppingModels.Order.create_order(tab.key, productModel.key, int(qnt), put_model=False)

				##: Update the Cart for the Totals Costs
				if order:
					##: Updatte the Cart's subtotals
					orderSubTotal = (int(order.st)-int(old_order_subtotal))
					oldTabSubTotal = tab.st
					newTabSubTotal = int(oldTabSubTotal) + int(orderSubTotal)
					if int(newTabSubTotal) < 0: newTabSubTotal = orderSubTotal
					shoppingModels.Tab.update_subtotal_values(tab, newTabSubTotal, oldTabSubTotal, put_model=False)

				ndb.put_multi( [tab, order] )

				message = _('Product number, {}, has been added onto your tab at a quantity of {}'.format(str(productModel.pn), str(qnt)))
				self.add_message(message, 'success')
			else:
				raise Exception('No productModel found, error creating Tab/Order Item, in function POST of AddToTabHandler')

		except Exception as e:
			logging.error('Error in function POST of AddToTabHandler : --	%s' % e)
			message = _('We are having difficulties with finalizing the Tab Submission. Please try again later.')
			self.add_message(message, 'error')
		
		finally:
			logging.info('Finished now Redirect to Referrer')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


	@webapp2.cached_property
	def addToTab_form(self):
		return forms.AddToTabForm(self)


class AddCartToTabHandler(BournEEHandler):
	@user_required
	def post(self):
		try:
			if not self.addCartToTab_form.validate():
				raise Exception('addCartToTab_form did not Validate, in function \
				 				POST of AddToTabHandler')

			logging.info("addCartToTab_form Form Was valid")

			ordersSubtotal = 0
			entitiesToPut = []
			oldTabSubTotal = 0
			newTabSubTotal = 0

			##: Try to fetch the data from the Form responce
			urlsafeCartKey = str(self.addCartToTab_form.ck.data).strip()

			##: Must have both urlsafeUserKey and urlsafeProductKey
			if not urlsafeCartKey:
				logging.error("Error, Missing urlsafeCartKey")

			cartModel = ndb.Key(urlsafe=urlsafeCartKey).get()

			if cartModel:
				logging.info("Found a cartModel")

				##: Get or create the Cart
				tab = shoppingModels.Tab.get_or_create_tab(self.user_key)
				if not tab:
					logging.info("Did not Find a Tab")
					raise Exception('No Tab returned, error creating Tab, in function POST of AddToTabHandler')

				##: Now we run thru all the orders in the cart and clone them to have the tab as parent.
				orderItems = shoppingModels.Order.get_for_parentKey(cartModel.key)
				if orderItems:
					for orderItem in orderItems:
						keyname = orderItem.key.id()
						tabOrder = ndb.Key(shoppingModels.Order, keyname, parent=tab.key).get()
						if tabOrder:
							tabOrder.q += orderItem.q
						else:
							tabOrder = utils.clone_entity(orderItem)
							tabOrder.key = ndb.Key(shoppingModels.Order, keyname, parent=tab.key)
						entitiesToPut.append(tabOrder)
						ordersSubtotal += orderItem.st

					##: Update the Cart's subtotals
					oldTabSubTotal = tab.st
					newTabSubTotal = int(oldTabSubTotal) + int(ordersSubtotal)
					if int(newTabSubTotal) < 0: newTabSubTotal = ordersSubtotal
					shoppingModels.Tab.update_subtotal_values(tab, newTabSubTotal, oldTabSubTotal, put_model=False)

					entitiesToPut.append(tab)

					if len(entitiesToPut) > 1:
						ndb.put_multi(entitiesToPut)
					elif len(entitiesToPut) == 1:
						entitiesToPut[0].put()

					message = _('The cart {}, has been added onto your tab.'.format(str(cartModel.n)))
					self.add_message(message, 'success')

				else:
					logging.error("Could not find any orders to go with the submitted cart")
					message = _('We are having difficulties with the order items in this cart. We did not add them to your Tab. Please try again later.')
					self.add_message(message, 'error')

			else:
				raise Exception('No cartModel found, error adding Cart to Tab, in function POST of AddCartToTabHandler')

		except Exception as e:
			logging.error('Error in function POST of AddCartToTabHandler : --	%s' % e)
			message = _('We are having difficulties adding this Cart to the Tab. Please try again later.')
			self.add_message(message, 'error')

		finally:
			logging.info('Finished now Redirect to Referrer')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')


	@webapp2.cached_property
	def addCartToTab_form(self):
		return forms.AddCartToTabForm(self)

