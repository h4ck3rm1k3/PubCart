#!/usr/bin/env python
# encoding: utf-8
"""
shoppingModels.py

Created by Jason Elbourne on 2012-12-18.
Copyright (c) 2012 Jason Elbourne. All rights reserved.
"""

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api.labs import taskqueue

import re
import time
import config
import logging

from lib import utils
from lib import searchCategories
from lib import searchDocument
from userModels import User, Seller



def verify_cart_subtotals(urlsafeCartKey):
	""" This function should be ran in a Deferred method after a cart has been updated"""
	cartKey = ndb.Key(urlsafe=urlsafeCartKey)
	cart = cartKey.get()
	if cart:
		oldSubTotal = cart.st
		
		cartOrders = Order.get_for_parentKey(cartKey)

		if cartOrders:
			if len(cartOrders) == 1:
				if cartOrders[0]:
					cart.st = cartOrders[0].st
				else:
					logging.error('Error in verify_subtotals for Cart, Could not get orders from keys')
					cart.st = 0
			elif len(cartOrders) > 1:
				cart.st = sum([order.st for order in cartOrders])

		else: logging.error('Error in verify_subtotals for Cart, Cart does not have cartOrders')
		
		newSubTotal = cart.st
		if oldSubTotal != newSubTotal:
			##:  Now lets update the New Carts SubTotal
			Cart.update_subtotal_values(cart, newSubTotal, oldSubTotal, put_model=True, dirty=False)
	else: logging.error('Error in verify_subtotals for Cart, Cart could not be found from the urlsafeCartKey ')


class Product(ndb.Expando):
	"""
		The Model for storing the Product General Info.
	"""

	sk = ndb.KeyProperty(kind=Seller) # Seller Model Key

	##: Genral Info Data
	pn = ndb.StringProperty(required=True) ##: Product Number
	m = ndb.StringProperty(required=True) ##: Manufacturer (Brand)
	d = ndb.StringProperty(required=True, indexed=False) ##: Description
	mq = ndb.StringProperty(default='1', indexed=False) ##: Minimum Quantity
	qa = ndb.IntegerProperty(default=0, indexed=False) ##: Quantity Available ex: '17,558 - Immediate'
	
	##: Pricing Data
	bup = ndb.IntegerProperty(default=0) ##: Best Unit Price (1 Unit)
	pch = ndb.IntegerProperty(default=0, indexed=False) ##: Price Change
	cp = ndb.IntegerProperty(default=0, indexed=False) ##: Last Close Price
	cq = ndb.IntegerProperty(default=1, indexed=False) ##: Last Close Quantity Shipped
	cpt = ndb.IntegerProperty(default=1, indexed=False) ##: Current Price Tier
	hup = ndb.IntegerProperty(default=0, indexed=False) ##: Highest Unit Price (Tier 1)

	##: Media Info Data
	img = ndb.StringProperty(indexed=False) ##:Image
	isl = ndb.StringProperty(indexed=False) ##: Info Sheet Link to PDF
	spl = ndb.StringProperty(indexed=False) ##: Seller Page Link for individual Product
	
	##: Date / Time
	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')
	
	##: Properties for digikey products
	# p = ndb.StringProperty() ##: Packaging
	# ot = ndb.StringProperty() ##: Operating Temperature
	# mt = ndb.StringProperty() ##: Mounting Type
	# pc = ndb.StringProperty() ##: Package / Case
	# sdp = ndb.StringProperty() ##: Supplier Device Package
	
	@property
	def clean_pn(cls):
		return utils.clean_product_number(cls.pn)
	
	@property
	def d_bup(cls):
		return utils.dollar_float(float(cls.bup)/100)

	@property
	def d_cp(cls):
		return utils.dollar_float(float(cls.cp)/100)


	@property
	def d_hup(cls):
		if cls.hup:
			return utils.dollar_float(float(cls.hup)/100)
		else:
			pp, hup = ProductTierPrice.get_price_for_qnt(cls.pn, 1)
			cls.hup = hup
			cls.put()
			return utils.dollar_float(float(hup)/100)

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		return [u'pn', u'm', u'pn', u'd', u'qa']

	def _pre_put_hook(cls):
		n = utils.clean_product_number(cls.pn)
		key = ndb.Key(Product, str(n), parent=cls.sk)
		cls.key = key
		if not cls.cp:  cls.cp  = cls.bup
		if not cls.hup: cls.hup = cls.bup
	
	@classmethod
	def _post_put_hook(cls, future):
		now = time.time()
		productModelKey = future.get_result()
		try:
			taskqueue.add(
						name=str(str(productModelKey.urlsafe())[:16]+'search-worker'+str(int(now/30))), \
						queue_name='search-worker', \
						url='/worker/searchDocUpdate', \
						params={'urlsafeProductKey': str(productModelKey.urlsafe())})
		except Exception as e:
			logging.error('Error Creating the Product Search Document taskqueue: -- {}'.format(e))
		try:
			taskqueue.add(
						name=str(str(productModelKey.urlsafe())[:16]+'parsers-worker'+str(int(now/30))), \
						queue_name='parsers-worker', \
						url='/worker/setProductTierPrices', \
						params={'urlsafeProductKey':  productModelKey.urlsafe()}) # post parameter
		except Exception as e:
			logging.error('Error checking product price tier taskqueue: -- {}'.format(e))

	@staticmethod
	def get_all(quantity=999):
		return Product.query().fetch()

	@staticmethod
	def get_by_pn(pn, quantity=999):
		## pn = Manufacturer Product Number
		n = utils.clean_product_number(pn)
		qry = Product.query(Product.pn == n)
		return qry.fetch(quantity)

	@staticmethod
	def get_by_seller_and_pn(sellerID, productNumber):
		pn = utils.clean_product_number(productNumber)
		sellerKey = ndb.Key(userModels.Seller, str(sellerID)).get(keys_only=True)
		if sellerKey: return ndb.Key(Product, str(pn), parent=sellerKey).get()
		return None
			
	
	@staticmethod
	def create_from_parse_data(parseData):
		try:
			productModel = Product()
			productModel.populate(**parseData)
			productKey = productModel.put()
			if productKey:
				return productModel
			else:
				raise Exception('No productKey returned from productModel.put()')
		except Exception as e:
			logging.error('Exception thrown in function create_from_parse_data of model class Product: -- {}'.format(e))
			return None


class ProductTierPrice(ndb.Model):
	"""
		The Model for storing the Products individual price tier.
	"""
	pk = ndb.KeyProperty(kind=Product) # Product Model Key
	pn = ndb.StringProperty() # Product Number

	o = ndb.IntegerProperty() # 1
	t = ndb.IntegerProperty() # 10
	oH = ndb.IntegerProperty() # 100
	tf = ndb.IntegerProperty() # 250
	fH = ndb.IntegerProperty() # 500
	oT = ndb.IntegerProperty() # 1,000
	tHT = ndb.IntegerProperty() # 2,500
	fT = ndb.IntegerProperty() # 5,000
	tT = ndb.IntegerProperty() # 10,000
	
	meq = ndb.IntegerProperty() # Minimum Exchange Quantity
	mep = ndb.IntegerProperty() # Maximum Exchange Buy Price
	hq = ndb.IntegerProperty() # High Quantity (this is the quantity where the price stops dropping)
	lp = ndb.IntegerProperty() # Lowest Price

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')
	
	@property
	def clean_pn(cls):
		return utils.clean_product_number(cls.pn)

	def _pre_put_hook(cls):
		pn = utils.clean_product_number(cls.pn)
		key = ndb.Key(ProductTierPrice, str(pn), parent=cls.pk)
		cls.key = key

	@staticmethod
	def create_from_parse_data(**parseData):
		try:
			productTierModel = ProductTierPrice()
			productTierModel.populate(**parseData)
			productTierKey = productTierModel.put()
			if productTierKey:
				return productTierModel
			else:
				raise Exception('No productTierKey returned from productTierModel.put()')
		except Exception as e:
			logging.error('Exception thrown in function create_from_parse_data of model class ProductTierPrice: -- {}'.format(e))
			return None
	
	@staticmethod
	def update_from_parse_data(productTierModel, **parseData):
		try:
			productTierModel.populate(**parseData)
			productTierKey = productTierModel.put()
			if productTierKey:
				return productTierModel
			else:
				raise Exception('No productTierKey returned from productTierModel.put()')
		except Exception as e:
			logging.error('Exception thrown in function create_from_parse_data of model class ProductTierPrice: -- {}'.format(e))
			return None
	
	@staticmethod
	def get_price_for_qnt(urlsafeProductKey, qnt, return_PTModel=True):
		" Use this function if you only have a product number and need the price amount @ a Tier."
		qnt_to_search = qnt
		qL = [1,10,100,250,500,1000,2500,5000,10000]
		dic = {'1':'o','10':'t','100':'oH','250':'tf','500':'fH', '1000':'oT', '2500':'tHT', '5000':'fT', '10000':'tT'}
		##:  Need to set the qnt to the closest tier quantity in 'dic{}' utherwise we return a None for best_price
		previous = '1'
		for i in qL:
			logging.info('Qnt = %s,  i = %s' % (str(qnt),str(i)))
			if int(qnt) >= int(i):
				qnt_to_search = str(previous) ##: This creates our margin always using the price of the tier right before the searched amount
				previous = str(i) ##: We set the current tier number to the <previous> variable
				continue
			else:
				break
		logging.info('Determined qnt_to_search is = %s' % str(qnt_to_search))
		productKey = ndb.Key(urlsafe=urlsafeProductKey)
		pp = ProductTierPrice.query(ancestor=productKey).get()
		if pp:
			if dic.has_key(str(qnt_to_search)):
				prop = dic[str(qnt_to_search)]
				logging.info('prop: {}'.format(prop))
				price = getattr(pp, prop)
				logging.info('Price: {}'.format(price))
				if return_PTModel:
					return pp, price  ##: productTierPrice, Price
				else:
					logging.info('Price: {}'.format(price))
					return price

		logging.error("ProductTierPrice not found in function get_price_for_qnt of model ProductTierPrice")
		if return_PTModel: return None, None
		else: return None

	@classmethod
	def get_for_product(cls, productPN, productKey):
		pn = utils.clean_product_number(productPN)
		return ndb.Key(ProductTierPrice, str(pn), parent=productKey).get()


class MarketMaker(ndb.Model):
	"""
		The Model for storing the Market Maker Limit Order Info.
	"""
	uk = ndb.KeyProperty(kind=User) ##: User Model Key
	pk = ndb.KeyProperty(kind=Product) ##: Product Model Key
	pn = ndb.StringProperty() ##: Product Number
	d = ndb.StringProperty() ##: Description
	bup = ndb.IntegerProperty() ##: Purchased Price (cents)
	sup = ndb.IntegerProperty() ##: Limit Price / Selling  Price (cents)
	rq = ndb.IntegerProperty() ##: Remaining Quantity
	qoh = ndb.IntegerProperty(default=0) ##: Quantity on Hold
	c = ndb.IntegerProperty() ##: Full Order Cost (cents)
	roi = ndb.IntegerProperty() ##: Estimated Return on Investment at time of purchase (cents)
	f = ndb.IntegerProperty() ##: Fee charged by BournEE Exchange at time of full order purchase (cents)
	p = ndb.IntegerProperty() ##: Percentage of markup on Buy Price
	img = ndb.StringProperty() ##: Image URL

	pd = ndb.BooleanProperty(default=False) # Has the order been paid for

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@property
	def d_sup(cls):
		## dlp = Dollar Limit Price
		return utils.dollar_float(float(cls.sup)/100)
	
	@property
	def price_change(cls):
		return 0.00
		
	@property
	def is_best_sell_price(cls):
		product = cls.pk.get()
		if product:
			part_current_best_price = product.bup
			if part_current_best_price:
				if int(part_current_best_price) < int(cls.sup):
					return False
		return True

	@property
	def clean_pn(cls):
		return utils.clean_product_number(cls.pn)

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'pn', u'd', u'pp', u'lp', u'q']
		return []

	def _pre_put_hook(cls):
		p = utils.clean_product_number(cls.pn)
		key = ndb.Key(MarketMaker, str(p)+str(cls.sup), parent=cls.uk)
		cls.key = key

	@classmethod
	def get_all(cls, quantity=999):
		try:
			return cls.query().fetch(quantity)
		except:
			logging.error("Error with query in function get_all for Model class OrderItem ")
			return None

	@classmethod
	def get_by_pn(cls, pn, quantity=999):
		try:
			return cls.query(ndb.AND(MarketMaker.pn == str(pn).upper(), MarketMaker.pd == True)).order(-cls.lp).fetch(quantity)
		except:
			logging.error("Error with query in function get_by_pn for Model class OrderItem")
			return None

	@classmethod
	def get_for_UserKey(cls, uk, pn=None, sup=None, quantity=999):
		##: uk = User Key
		try:
			if pn != None or sup != None:
				p = utils.clean_product_number(pn)
				logging.info('Going to run ndb.Key - get()')
				return ndb.Key(MarketMaker, str(p)+str(sup), parent=cls.uk).get()
			logging.info('Going to run Query on MarketMaker Model')
			return cls.query(ancestor=uk).order(-cls.cd).fetch(quantity)
		except:
			logging.error("Error with query in function get_for_UserKey for Model class OrderItem")
			return None

class Tab(ndb.Model):
	uk = ndb.KeyProperty(kind=User) ##: User Model Key

	st = ndb.IntegerProperty(default=0) ##: Sub-Total (Cents)
	
	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')
	
	pdd = ndb.DateTimeProperty(verbose_name='paid_datetime') ##: Paid Date time
	pd = ndb.BooleanProperty(default=False) ##: Paid Boolean
	sh = ndb.BooleanProperty(default=False) ##: Shipped Boolean
	##: If the tabs's orders have been modified (added or taken out) dirty flag is set.
	##: When the task queue runs a check on the tabs's subtotal, this is set to false.
	dirty = ndb.BooleanProperty(default=False)

	@property
	def num_items(cls):
		return Order.query(ancestor=cls.key).count()

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'd', u'pp', u'lp', u'q']
		return []

	@staticmethod
	def get_or_create_tab(userKey):
		try:
			tab = Tab.query(Tab.pd==False, ancestor=userKey).get()
			if tab:
				return tab
			else:
				first, last = Tab.allocate_ids(1, parent=userKey)
				keyName = first
				tab = Tab()
				tab.key = ndb.Key(Tab, keyName, parent=userKey)
				tab.uk = userKey
				tabKey = tab.put()
				if tabKey: return tab
			return None
		except Exception as e:
			logging.error("Error in function get_or_create_cart for Model class Cart: -- {}".format(e))
			return None

	@staticmethod
	def update_subtotal_values(tab, newSubTotal, old_subtotal=0, put_model=True):
		try:
			tab.st = int(newSubTotal)
			if int(old_subtotal) != int(tab.st):
				if put_model:
					tab.put()
		except Exception as e:
			logging.error("Error with function update_subtotal_values for Model class Cart: -- {}".format(e))



class Cart(ndb.Model):
	"""
		The Model for storing the different Cart's.
		Carts can be public
	"""
	uk = ndb.KeyProperty(kind=User) ##: User Model Key
	n = ndb.StringProperty(default='My list') ##: Cart Name
	d = ndb.StringProperty(indexed=False) ##: Cart Description
	cat = ndb.StringProperty() ##: Cart Category
	img = ndb.StringProperty(indexed=False) ##: Image

	st = ndb.IntegerProperty(default=0) ##: Sub-Total (Cents)

	public = ndb.BooleanProperty(default=False) ##: Shopping Carts are PRIVATE and BeList Carts are public.
	
	garbage = ndb.BooleanProperty(default=False) ##: The Creator (User) deleted cart but we still need to serve to embeded carts

	##: If the cart's orders have been modified (added or taken out) dirty flag is set.
	##: When the task queue runs a check on the carts subtotal, this is set to false.
	dirty = ndb.BooleanProperty(default=False)

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')
	
	@property
	def d_st(cls):
		## d_st = Dollar Sub-Total
		return utils.dollar_float(float(cls.st)/100)

	@property
	def num_items(cls):
		return Order.query(ancestor=cls.key).count()
	
	@property
	def owner(cls):
		user = cls.uk.get()
		if user:
			return user.username
		return None

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'd', u'pp', u'lp', u'q']
		return []

	@classmethod
	def _post_put_hook(cls, future):
		try:
			logging.info('future: {}'.format(future.get_result()))
			now = time.time()
			cartModelKey = future.get_result()
			taskqueue.add(
						name=str(str(cartModelKey.urlsafe())[:16]+'cartTotals-worker'+str(int(now/30))), \
						queue_name='cartTotals-worker', \
						url='/worker/checkCartSubtotals', \
						params={'urlsafeCartKey':  cartModelKey.urlsafe()}) # post parameter
			logging.info('Ran a task queue to verify cart subtotals for cart: {}'.format(cartModelKey))
		except Exception as e:
			logging.error('Error checking cart subtotals with taskqueue: -- {}'.format(e))


	@staticmethod
	def create_cart(cartKey, userKey, cartName, cartDescritpion=None, cartCategory=None, put_model=True):
		try:
			cart = Cart(
						key = cartKey, \
						uk = userKey, \
						n = cartName, \
						d = cartDescritpion, \
						cat = cartCategory, \
						)
			if put_model:
				cart.put()
			return cart
		except Exception as e:
			logging.error("Error in function _create_cart for Model class Cart: -- {}".format(e))
			return None

	@staticmethod
	def get_or_create_cart(userKey, urlsafeCartKey , cartName, cartDescritpion=None, cartCategory=None):
		try:
			if urlsafeCartKey:
				return ndb.Key(urlsafe=urlsafeCartKey).get()
			else:
				cartKeyName = "{}".format(str(cartName).upper())
				cartKey = ndb.Key(Cart, cartKeyName, parent=userKey)
				cart = cartKey.get()
				if cart: return cart
				else: return Cart.create_cart(cartKey, userKey, str(cartName).lower(), cartDescritpion, cartCategory)

			return None
		except Exception as e:
			logging.error("Error in function get_or_create_cart for Model class Cart: -- {}".format(e))
			return None


	@staticmethod
	def get_public_carts(userKey=None, quantity=999):
		try:
			if userKey: qry = Cart.query(ndb.AND(Cart.public == True, Cart.garbage == False), ancestor=userKey)
			else: qry = Cart.query(ndb.AND(Cart.public == True, Cart.garbage == False))
			return qry.order(Cart.ud).fetch(quantity)
		except Exception as e:
			logging.error("Error with query in function get_public_carts for Model class Cart: -- {}".format(e))
			return None

	@staticmethod
	def get_carts_for_user(userKey, quantity=999):
		try:
			qry =  Cart.query(Cart.garbage == False, ancestor=userKey)
			return qry.order(Cart.ud).fetch(quantity)
		except Exception as e:
			logging.error("Error with query in function get_carts_for_user for Model class Cart: -- {}".format(e))
			return None

	@staticmethod
	def update_subtotal_values(cart, newSubTotal, old_subtotal=0, put_model=True, dirty=True):
		try:
			cart.st = int(newSubTotal)
			cart.dirty = dirty
			if int(old_subtotal) != int(cart.st):
				if put_model:
					cart.put()
		except Exception as e:
			logging.error("Error with function update_subtotal_values for Model class Cart: -- {}".format(e))
	
	@staticmethod
	def update_cart_to_be_public(cart, cartDescription, cartCategory, put_model=True):
		try:
			cart.d = cartDescription
			cart.cat = cartCategory
			cart.public = True
			cart.garbage = False
			if put_model:
				cart.put()
		except Exception as e:
			logging.error("Error with function update_cart_to_be_public for Model class Cart: -- {}".format(e))

	@staticmethod
	def update_cart_details(cart, cartDescription, cartCategory, put_model=True):
		try:
			cart.d = cartDescription
			cart.cat = cartCategory
			if put_model:
				cart.put()
		except Exception as e:
			logging.error("Error with function update_cart_to_be_public for Model class Cart: -- {}".format(e))


class Order(ndb.Model):
	"""
		The Model for storing the Order Item information.
	"""
	pk = ndb.KeyProperty(kind=Product) ##: Product Model Key
	
	q = ndb.IntegerProperty() ##: Quantity
	
	removed = ndb.BooleanProperty(default=False) ##: Was the Order removed from the User's Tab

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@property
	def productName(cls):
		return cls.key.id()

	@property
	def clean_pn(cls):
		return utils.clean_product_number(cls.key.id())
	
	@property
	def seller(cls):
		return "TODO"
			
	@property
	def popularity(cls):
		return str(20)

	@property
	def description(cls):
		if cls.pk:
			product = cls.pk.get()
			if product:
				return product.d
		return " "

	@property
	def fetch_bup(cls):
		if cls.pk:
			urlsafeProductKey = cls.pk.urlsafe()
			ptp = ProductTierPrice.get_price_for_qnt(urlsafeProductKey, cls.q, return_PTModel=False)
			if ptp: return ptp
			else:
				product = ndb.Key(urlsafe=urlsafeProductKey).get()
				if product:
					return product.bup
		return 0
			
	@property
	def d_bup(cls):
		if cls.fetch_bup: return ("%.2f" % (float(cls.fetch_bup)/100))
		else: return None

	@property
	def st(cls):
		if cls.q:
			subTotal = None
			price = cls.fetch_bup
			if price: return cls.q * price
		return 0

	@property
	def d_st(cls):
		if cls.st: return ("%.2f" % (float(cls.st)/100))
		return None

	
	@property
	def fetch_img(cls):
		if cls.pk:
			img = None
			product = cls.pk.get()
			if product:
				img = product.img
				if img: return img
		return None

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'pn', u'm', u'pn', u'd', u'qa']
		return []
	
	@classmethod
	def _post_put_hook(cls, future):
		try:
			now = time.time()
			orderModelKey = future.get_result()
			orderModel = orderModelKey.get()
			if orderModel:
				taskqueue.add(
							name=str(str(orderModel.pk.urlsafe())[:16]+'parsers-worker'+str(int(now/30))), \
							queue_name='parsers-worker', \
							url='/worker/setProductTierPrices', \
							params={'urlsafeProductKey':  orderModel.pk.urlsafe()}) # post parameter
		except Exception as e:
			logging.error('Error checking product price tier taskqueue: -- {}'.format(e))

	@classmethod
	def create_order(cls, parentKey, productKey, qnt, put_model=True):
		try:
			product = productKey.get()
			if product:
				pn = utils.clean_product_number(product.pn)
				order = cls(
							key = ndb.Key(Order, str(pn), parent=parentKey),
							pk = productKey, ##: Product Model Key
							q = int(qnt), ##: Quantity for Order
							)
				if put_model:
					orderKey = order.put()
					if orderKey:
						return order
				else:
					return order
			return None
		except Exception as e:
			logging.error("Error creating the order model in function create_order for Model class Order : -- %s " % str(e))
			return None

	@classmethod
	def update_order_add_qnt(cls, order, qnt, put_model=True):
		try:
			order.q += qnt ##: Update Quantity
			if put_model:
				orderKey = order.put()
				if orderKey:
					return order
			else:
				return order
			return None
		except Exception as e:
			logging.error("Error updating the order model's qnt in function update_order_qnt for Model class Order : -- %s " % str(e))
			return None

	@classmethod
	def update_order_new_qnt(cls, order, qnt, put_model=True):
		try:
			order.q = qnt ##: Update Quantity
			if put_model:
				orderKey = order.put()
				if orderKey:
					return order
			else:
				return order
			return None
		except Exception as e:
			logging.error("Error updating the order model's qnt in function update_order_qnt for Model class Order : -- %s " % str(e))
			return None

	@classmethod
	def get_for_product(cls, productKey, quantity=999):
		try:
			logging.info('Going to run query within the function get_for_product')
			orders = cls.query(Order.pk == productKey).fetch(quantity)
			return orders
		except Exception as e:
			logging.error("Error with query in function get_for_product for Model class Order : -- %s " % str(e))
			return None

	@classmethod
	def get_all(cls, quantity=999):
		try:
			return cls.query().fetch(quantity)
		except:
			logging.error("Error with query in function get_all for Model class Order ")
			return None

	@classmethod
	def get_for_parentKey(cls, parentKey, quantity=999):
		try:
			return Order.query(ancestor=parentKey).fetch(quantity)
		except:
			logging.error("Error with query in function get_for_UserKey for Model class Order ")
			return None

	@classmethod
	def get_for_product_and_parent(cls, parentKey, productNumber, quantity=999):
		try:
			pn = utils.clean_product_number(productNumber)
			return ndb.Key(Order, str(pn), parent=parentKey).get()
		except:
			logging.error("Error with query in function get_for_UserKey for Model class Order ")
			return None


class PurchaseRecord(ndb.Model):
	'''a completed transaction'''
	ck = ndb.KeyProperty(kind=Cart) ##: Cart Key
	cuk = ndb.KeyProperty(kind=User) ##: Cart Owner User Key
	puk = ndb.KeyProperty(kind=User) ##: Purchaser User Key
	st = ndb.StringProperty( choices=( 'NEW', 'CREATED', 'ERROR', 'CANCELLED', 'RETURNED', 'COMPLETED', 'SHIPPED' ) ) ##: Status
	std = ndb.StringProperty(indexed=False) ##: Status_detail
	s = ndb.StringProperty(indexed=False) ##: Secret # to verify return_url
	dreq = ndb.TextProperty(indexed=False) ##: debug_request
	dres = ndb.TextProperty(indexed=False) ##: debug_responce
	pk = ndb.StringProperty(indexed=False) ##: payKey
	sh = ndb.StringProperty(indexed=False) ##: Shipping
	cd = ndb.DateTimeProperty(auto_now_add=True) ##: Created Date
	ud = ndb.DateTimeProperty(auto_now=True) ##: Updated Date
	
	@classmethod
	def get_by_cartKey(cls, cartKey):
		return cls.query(PurchaseRecord.ck==cartKey).get()
	


class OrderPurchaseRecord(ndb.Model):
	prk = ndb.KeyProperty(kind=PurchaseRecord) ##: PurchaseRecord Key
	pk = ndb.KeyProperty(kind=Product) ##: Product Key
	q = ndb.IntegerProperty() ##: Qunatity for Ordered Product

	cd = ndb.DateTimeProperty(auto_now_add=True) ##: Created Date
	ud = ndb.DateTimeProperty(auto_now=True) ##: Updated Date

	@staticmethod
	def get_purchased_qnt_for_product_number(urlsafeProductKey, quantity=999):
		productKey = ndb.Key(urlsafe=urlsafeProductKey)
		if productKey:
			qnt = 0
			purchasedOrders = OrderPurchaseRecord.query(OrderPurchaseRecord.pk == productKey).fetch(quantity)
			for order in  purchasedOrders:
				pr = order.prk.get()
				if pr.st == 'COMPLETED':
					qnt += order.q
			return qnt
		else:
			return 0
		

class Alert(ndb.Model):
	"""
		The Model for an Alert.
	"""
	uk = ndb.KeyProperty(kind=User) ##: User Model Key
	pk = ndb.KeyProperty(kind=Product) ##: Product Key (urlsafe)
	d = ndb.StringProperty() ##: Product Description
	pn = ndb.StringProperty() ##: Product Number
	img = ndb.StringProperty() ##: Product Image URL
	
	ap = ndb.IntegerProperty(repeated=True) ##: Alert Price
	aq = ndb.IntegerProperty(repeated=True) ##: Alert Quantity

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	
	@property
	def clean_pn(cls):
		return utils.clean_product_number(cls.pn)

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'pn', u'd', u'pp', u'lp', u'q']
		return []

	def _pre_put_hook(cls):
		pn = utils.clean_product_number(cls.pn)
		key = ndb.Key(Alert, "A_"+str(mpn), parent=cls.uk)
		cls.key = key

	@classmethod
	def get_for_UserKey(cls, uk, pn=None, quantity=999):
		## uk = User Key
		## pn = Manufacturers Product Number
		try:
			if pn:
				n = utils.clean_product_number(pn)
				return ndb.Key(Alert, str(n), parent=uk).get()
			else:
				return cls.query(ancestor=uk).fetch(quantity)
		except:
			logging.error("Error with query in function get_for_UserKey for Model class OrderItem")
			return None


class Watchlist(ndb.Model):
	"""
		The Model for a Watchlist.
	"""
	uk = ndb.KeyProperty(kind=User) ##: User Model Key
	n = ndb.StringProperty(default='ALL') ##: Watchlist Name

	kl = ndb.KeyProperty(repeated=True) ##: Key List for models watched

	default = ndb.BooleanProperty(default=True) ##: When adding products to cart, this defines which cart to add to.

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'pn', u'd', u'pp', u'lp', u'q']
		return []

	def _pre_put_hook(cls):
		key = ndb.Key(Watchlist, str(cls.n), parent=cls.uk)
		cls.key = key

	@classmethod
	def get_default_for_user(cls, userKey):
		try:
			return cls.query(Watchlist.default == True, ancestor=userKey).get()
		except:
			logging.error("Error with query in function get_for_UserKey for Model class OrderItem")
			return None