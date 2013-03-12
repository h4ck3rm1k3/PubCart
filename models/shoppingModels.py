#!/usr/bin/env python
# encoding: utf-8
"""
shoppingModels.py

Created by Jason Elbourne on 2012-12-18.
Copyright (c) 2012 Jason Elbourne. All rights reserved.
"""

from google.appengine.api import memcache
from google.appengine.ext import ndb

import re
import config
import logging

from lib import utils
from lib import searchCategories
from lib import searchDocument
from models.userModels import User, Seller


def verify_cart_subtotals(urlsafeCartKey):
	""" This function should be ran in a Deferred method after a cart has been updated"""
	cartKey = ndb.Key(urlsafe=urlsafeCartKey)
	cart = cartKey.get()
	if cart:
		oldSubTotal = cart.st
		
		cartOrders = Order.get_for_cart(cartKey)

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
			Cart.update_subtotal_values(cart, newSubTotal, oldSubTotal)
	else: logging.error('Error in verify_subtotals for Cart, Cart could not be found from the urlsafeCartKey ')


class Category(ndb.Model):
	"""The model class for product category information.  Supports building a
	category tree."""

	_CATEGORY_INFO = None
	_CATEGORY_DICT = None
	_RCATEGORY_DICT = None
	_ROOT = 'root'  # the 'root' category of the category tree

	parent_category = ndb.KeyProperty()

	@property
	def category_name(self):
		return self.key.id()

	@classmethod
	def buildAllCategories(cls):
		""" build the category instances from the provided static data, if category
		entities do not already exist in the Datastore. (see categories.py)."""

		# Don't build if there are any categories in the datastore already
		if cls.query().get():
			return
		root_category = searchCategories.ctree
		cls.buildCategory(root_category, None)

	@classmethod
	def buildCategory(cls, category_data, parent_key):
		"""build a category and any children from the given data dict."""

		if not category_data:
			return
		cname = category_data.get('name')
		if not cname:
			logging.warn('no category name')
			return
		if parent_key:
			cat = cls(id=cname, parent_category=parent_key)
		else:
			cat = cls(id=cname)
		cat.put()

		children = category_data.get('children')
		# if there are any children, build them using their parent key
		cls.buildChildCategories(children, cat.key)

	@classmethod
	def buildChildCategories(cls, children, parent_key):
		"""Given a list of category data structures and a parent key, build the
		child categories, with the given key as their entity group parent."""
		for cat in children:
			cls.buildCategory(cat, parent_key)

	@classmethod
	def getCategoryInfo(cls):
		"""Build and cache a list of category id/name correspondences.  This info is
		used to populate html select menus."""
		if not cls._CATEGORY_INFO:
			cls.buildAllCategories()  	#first build categories from data file if required
			cats = cls.query().fetch()
			cls._CATEGORY_INFO = [(c.key.id(), c.key.id()) for c in cats if c.key.id() != cls._ROOT]
		return cls._CATEGORY_INFO


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
	def get_all(cls):
		return cls.query().fetch()

	@staticmethod
	def get_by_pn(pn, quantity=999):
		## pn = Manufacturer Product Number
		n = utils.clean_product_number(pn)
		qry = Product.query(Product.pn == n)
		return qry.fetch(quantity)
	
	@staticmethod
	def create_from_parse_data(parseData):
		try:
			productModel = Product()
			productModel.populate(**parseData)
			productKey = productModel.put()
			if productKey:
				try:
					del parseData['sk']
					parseData['urlsafeProductKey'] = productKey.urlsafe()
					searchDocument.Product.buildProduct(**parseData)
				except Exception as e:
					logging.error('Creating the Product Search Document Failed: -- {}'.format(e))
				return productModel
			else:
				raise Exception('No productKey returned from productModel.put()')
		except Exception as e:
			logging.Error('Exception thrown in function create_from_parse_data of model class Product: -- {}'.format(e))
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
	rep = ndb.IntegerProperty() # Recommended Exchange Price
	pp = ndb.IntegerProperty() # Potential Profit
	ppp = ndb.IntegerProperty() # Potential Profit Percentage
	
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
	def create_from_parse_data(parseData):
		try:
			productTierModel = ProductTierPrice()
			productTierModel.populate(**parseData)
			productTierKey = productTierModel.put()
			if productTierKey:
				return productTierModel
			else:
				raise Exception('No productTierKey returned from productTierModel.put()')
		except Exception as e:
			logging.Error('Exception thrown in function create_from_parse_data of model class ProductTierPrice: -- {}'.format(e))
			return None
	
	@classmethod
	def update_from_parse_data(cls, parseData):
		try:
			cls.populate(**parseData)
			productTierKey = cls.put()
			if productTierKey:
				return cls
			else:
				raise Exception('No productTierKey returned from productTierModel.put()')
		except Exception as e:
			logging.Error('Exception thrown in function create_from_parse_data of model class ProductTierPrice: -- {}'.format(e))
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
				price = getattr(pp, prop)
				p = price
				if return_PTModel:
					return pp, p  ##: productTierPrice, Price
				else:
					return p

		logging.error("ProductTierPrice not found in function get_price_for_qnt of model ProductTierPrice")
		return None, None

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


class Cart(ndb.Model):
	"""
		The Model for storing the different Cart's.
		Shopping Cart is Private
		BeList Cart is Public
	"""
	uk = ndb.KeyProperty(kind=User) ##: User Model Key
	ouk = ndb.KeyProperty(kind=User) ##: Original User Key
	n = ndb.StringProperty(default='SHOPPING') ##: Watchlist Name
	d = ndb.StringProperty(indexed=False) ##: Cart Description
	cat = ndb.StringProperty() ##: Cart Category
	img = ndb.StringProperty(indexed=False) ##: Image
	
	st = ndb.IntegerProperty(default=0) ##: Sub-Total (Cents)
	txrp = ndb.IntegerProperty(default=0, indexed=False) ##: Tax Rate Percentage (Integer for Percentage)
	tx = ndb.IntegerProperty(default=0, indexed=False) ##: Taxes (Cents)
	sh = ndb.IntegerProperty(default=0, indexed=False) ##: Shipping (Cents)
	mu = ndb.IntegerProperty(default=0, indexed=False) ##: BournEE Exchange Mark-up (5% + $0.30) (Cents)
	gt = ndb.IntegerProperty(default=0) ##: Grand Total (Cents)
	
	public = ndb.BooleanProperty(default=False) ##: Shopping Carts are PRIVATE and BeList Carts are public.
	default = ndb.BooleanProperty(default=True) ##: When adding products to cart, this defines which cart to add to.
	
	garbage = ndb.BooleanProperty(default=False) ##: The Creator (User) deleted cart but we still need to serve to embeded carts

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')
	
	@property
	def d_st(cls):
		## d_st = Dollar Sub-Total
		return utils.dollar_float(float(cls.st)/100)

	@property
	def d_tx(cls):
		## d_tx = Dollar Taxes
		return utils.dollar_float(float(cls.tx)/100)

	@property
	def d_sh_fees(cls):
		## d_sh = Dollar Shipping
		sh_fees = int(cls.sh) + int(cls.mu)
		return utils.dollar_float(float(sh_fees)/100)

	@property
	def d_mu(cls):
		## d_mu = Dollar Mark-up
		return utils.dollar_float(float(cls.mu)/100)

	@property
	def d_gt(cls):
		## d_gt = Dollar Grand-Total
		return utils.dollar_float(float(cls.gt)/100)

	@property
	def num_items(cls):
		return Order.query(ancestor=cls.key).count()
	
	@property
	def published(cls):
		return 0

	@staticmethod
	def _write_properties_for_api():
		return []

	@staticmethod
	def _read_properties_for_api():
		# Example : return [u'd', u'pp', u'lp', u'q']
		return []

	def _pre_put_hook(cls):
		pass
	
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
			dc = Cart.query(Cart.default == True, ancestor=userKey).get()
			if dc:
				cart.default = False
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
				if str(cartName).upper() not in utils.RESERVEDCARTNAMES:
					cartName = str(cartName).upper()
				else:
					first, last = Cart.allocate_ids(1, parent=userKey)
					cartID = first
					cartName = "{}_({})".format(str(cartName).upper(),cartID)
				cartKey = ndb.Key(Cart, cartName, parent=userKey)
				cart = cartKey.get()
				if cart: return cart
				else: return Cart.create_cart(cartKey, userKey, str(cartName).upper(), cartDescritpion, cartCategory)

			return None
		except Exception as e:
			logging.error("Error in function get_or_create_cart for Model class Cart: -- {}".format(e))
			return None
	
	@staticmethod
	def get_all_defaults(userKey, quantity=999):
		try:
			return Cart.query(Cart.default == True, ancestor=userKey).fetch(quantity)
		except Exception as e:
			logging.error("Error with query in function get_all_defaults for Model class Cart: -- {}".format(e))
			return None

	@staticmethod
	def get_default_private_cart(userKey):
		try:
			return Cart.query(ndb.AND(Cart.public == False, Cart.default == True), ancestor=userKey).get()
		except Exception as e:
			logging.error("Error with query in function get_default_private_cart for Model class Cart: -- {}".format(e))
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
	def update_subtotal_values(cart, newSubTotal, old_subtotal=0, put_model=True):
		try:
			cart.st = newSubTotal
			if old_subtotal != cart.st:
				tax_perc = float(cart.txrp)/100
				cart.tx = int(((float(cart.st)/100) * float(tax_perc))*100)
				cart.sh = 0 ##: Not known at this time
				cart.mu = int((( ( (float(cart.st)/100) + (float(cart.tx)/100) )*0.05)+0.3)*100)
				if cart.mu == 30:
					cart.mu = 0
				cart.gt = int(cart.st)+int(cart.tx)+int(cart.mu)+int(cart.sh)
			if put_model:
				cart.put()
		except Exception as e:
			logging.error("Error with function update_subtotal_values for Model class Cart: -- {}".format(e))
	
	@staticmethod
	def update_cart_to_be_public(cart, cartName, cartDescription, cartCategory, put_model=True):
		try:
			cart.n = cartName
			cart.d = cartDescription
			cart.cat = cartCategory
			cart.public = True
			cart.default = False
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

	@staticmethod
	def update_default_cart(userKey, urlsafeCartKey=None):
		try:
			entitiesToPut = []
			if urlsafeCartKey:
				currentCartKey = ndb.Key(urlsafe=urlsafeCartKey)

				currentCart = currentCartKey.get()
				currentDefaultCarts = Cart.get_all_defaults(userKey)

				if currentDefaultCarts:
					logging.info('Here')
					if len(currentDefaultCarts) >= 1:
						for dc in currentDefaultCarts:
							if dc.key != currentCartKey:
								logging.info('Here')
								dc.default = False
								entitiesToPut.append(dc)
		
				if currentCart.public == False:
					logging.info('Here')
					currentCart.default = True
					entitiesToPut.append(currentCart)

				if len(entitiesToPut) == 1:
					logging.info('Here')
					entitiesToPut[0].put()
				elif len(entitiesToPut) > 1:
					logging.info('Here')
					ndb.put_multi(entitiesToPut)
			else:
				cart = Cart.query(ndb.AND(Cart.default==False, Cart.public==False), ancestor=userKey).get()
				if cart:
					cart.default=True
					cart.put()
		except Exception as e:
			logging.error("Error with function update_default_cart for Model class Cart: -- {}".format(e))
				

class Order(ndb.Model):
	"""
		The Model for storing the Order Item information.
	"""
	ck = ndb.KeyProperty(kind=Cart) ##: Cart Model Key
	pk = ndb.KeyProperty(kind=Product) ##: Product Model Key

	q = ndb.IntegerProperty() ##: Quantity

	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@property
	def pn(cls):
		return cls.key.id()

	@property
	def clean_pn(cls):
		return utils.clean_product_number(cls.key.id())

	@property
	def fetch_bup(cls):
		if cls.pk:
			urlsafeProductKey = cls.pk.urlsafe()
			return ProductTierPrice.get_price_for_qnt(urlsafeProductKey, cls.q, return_PTModel=False)
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
	def fetch_d(cls):
		if hasattr(cls, 'd'):
			return cls.d
		else:
			if cls.pk:
				d = None
				product = cls.pk.get()
				if product:
					d = product.d
					if d: return d
			return None
	
	@property
	def fetch_img(cls):
		if hasattr(cls, 'img'):
			return cls.img
		else:
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
	def create_order(cls, cartKey, productKey, qnt, put_model=True):
		try:
			product = productKey.get()
			if product:
				pn = utils.clean_product_number(product.pn)
				order = cls(
							key = ndb.Key(Order, str(pn), parent=cartKey),
							pk = productKey, ##: Product Model Key
							ck = cartKey, ##: Cart Model Key
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
	def get_for_cart(cls, cartKey, quantity=999):
		try:
			return Order.query(ancestor=cartKey).fetch(quantity)
		except:
			logging.error("Error with query in function get_for_UserKey for Model class Order ")
			return None

	@classmethod
	def get_for_product_and_cart(cls, cartKey, productName, quantity=999):
		try:
			pn = utils.clean_product_number(productName)
			return ndb.Key(Order, str(pn), parent=cartKey).get()
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