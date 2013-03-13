#!/usr/bin/env python
# encoding: utf-8
"""
parser.py

Created by Jason Elbourne on 2012-12-18.
Copyright (c) 2012 Jason Elbourne. All rights reserved.
"""

from sgmllib import SGMLParser
from htmlentitydefs import name2codepoint
import logging
import string
import re
import sys
import httpagentparser
from urllib import urlopen
from models import shoppingModels
from google.appengine.ext import ndb



headers = [	'Digi-Key Part Number',
			'Manufacturer',
			'Manufacturer Part Number',
			'Description',
			'Operating Temperature',
			'Mounting Type',
			'Package / Case',
			'Supplier Device Package',
			'Packaging',
			'Quantity Available',
			'Minimum Quantity',
			'Unit Price',
			]



class Parser(SGMLParser):
	def reset(self):
		SGMLParser.reset(self)

		self.rows = []
		self.hdrs = {}
		self.inside_center = False
		self.inside_breadcrumb = False
		self.inside_a = False
		self.inside_th = False
		self.inside_td = False
		self.inside_tbody = False
		self.inside_productTable = False
		self.hdr_index = 0
		self.row_index = 0
		self.images = []
		self.datasheets = []
		self.dk_links = []
		self.categories = []
		
	def start_table(self, attrs):
		if dict(attrs).get('id', '') == 'productTable':
			self.inside_productTable = True
	
	def end_table(self):
		self.inside_productTable = False
	
	def start_tbody(self, attrs):
		self.inside_tbody = True
	
	def end_tbody(self):
		self.inside_tbody = False
	
	def start_th(self, attrs):
		self.inside_th = True
	
	def end_th(self):
		self.inside_th = False
		self.hdr_index += 1
	
	def start_tr(self, attrs):
		self.hdr_index = 0
		self.image = None
		self.datasheet = None
		if len(self.rows) > 0:
			self.row_index += 1
	
	def start_td(self, attrs):
		self.inside_td = True
	
	def end_td(self):
		self.inside_td = False
		self.hdr_index += 1

	def start_center(self, attrs):
		if self.inside_productTable and self.inside_td:
			self.inside_center = True
	
	def end_center(self):
		self.inside_center = False
	
	def start_h1(self, attrs):
		if dict(attrs).get('itemprop', '') == 'breadcrumb':
			self.inside_breadcrumb = True
	
	def end_h1(self):
		self.inside_breadcrumb = False
	
	def start_a(self, attrs):
		self.inside_a = True
		
		if self.inside_tbody and self.inside_productTable and self.inside_td:

			href = [v for k, v in attrs if k=='href']
			if href:
				if self.inside_center and len(self.datasheets)<=0:
					self.datasheets.extend(href)
				elif len(self.dk_links)<=0:
					self.dk_links.extend(href)

	def end_a(self):
		self.inside_a = False
	
	def start_img(self, attrs):
		if self.inside_tbody and self.inside_productTable and self.inside_td and not self.inside_center:
			if len(self.images)<=0:
				src = [v for k, v in attrs if k=='src']
				if src:
					self.images.extend(src)

	def handle_data(self, text):
		text = text.strip()
		if self.inside_breadcrumb and self.inside_a:
			logging.info('Inside breadcrumb and an a tag, add the category text.')
			self.categories.append(text)
		if self.inside_productTable:
			if self.inside_th:
				if text in headers:
					self.hdrs[self.hdr_index] = text
			elif self.inside_tbody and self.inside_td:
				if self.hdr_index in self.hdrs:
					while len(self.rows) <= self.row_index:
						self.rows.append({})
					part_info = self.rows[self.row_index]
					h = self.hdrs[self.hdr_index]
					part_info[h] = part_info.get(h, '') + text


def createProductPriceTier(productModel, productNumber, parsedData):
	
	newProductTierPricing = None
	productTierPricing = None
	logging.info('Here')
	
	try:
		priceTiers = parsedData['priceTiers']
		
		params = {}
		params['pk'] = productModel.key # Product Model Key
		params['pn'] = productModel.pn # Product Number
		for k, v in priceTiers.items():
			if not priceTiers.get('mep', ""):
				params['meq'] = int(k) ##: Minimum Exchange Quantity
				params['mep'] = int(v) ##: Maximum Exchange Buying Price (Price gets higher the lower the quantity)
				params['hq']  = int(k) ##: Highest Quantity before price stabalized
				params['lp']  = int(v) ##: Lowest Possible Price
			else:
				if params['meq'] == '1' and v > priceTiers[str(1)]:
					params['meq'] = int(k)
					params['mep'] = int(v)
				if v == previous_price:  params['hq'] = int(previous_qnt)
				if v < params['lp']: params['lp'] = v
			##: Now set the params for tier values
			if k == str(1): 	params['o'] = v
			if k == str(10): 	params['t'] = v
			if k == str(100): 	params['oH'] = v
			if k == str(250): 	params['tf'] = v
			if k == str(500): 	params['fH'] = v
			if k == str(1000):	params['oT'] = v
			if k == str(2500):	params['tHT'] = v
			if k == str(5000):	params['fT'] = v
			if k == str(10000): params['tT'] = v				
			##: Now set the previous values for next iteration
			previous_price = v
			previous_qnt = k

		productTierPricing = shoppingModels.ProductTierPrice.get_for_product(productModel.pn, productModel.key)
		if productTierPricing:
			newProductTierPricing = productTierPrice.update_from_parse_data(**params)
		else:
			##:  Create the Product Price Model info for this loop rotation.
			newProductTierPricing = shoppingModels.ProductTierPrice.create_from_parse_data(**params)
	except Exception as e:
		logging.error('Error creating ProductTierPrice model in function (createProductPriceTier) :  --  %s' % str(e))

	##: Now that we have an up to Date productTierPrice, we update the productModel
	try:
		logging.info('Here')
		##: Now we set the initial price tier value in the productModel.
		if newProductTierPricing:
			logging.info('Attempting to update productModel')
			if not productModel.bup or productModel.bup != int(newProductTierPricing.o):
				logging.info('Start to update productModel')
				productModel.bup = int(newProductTierPricing.o) ##: Best Unit Price
				productModel.hup = int(newProductTierPricing.o) ##: Highest Unit Price
				productModel.cp = int(newProductTierPricing.o) ##: Closing Unit Price
				productModel.cq = 1 ##: Closing Quantity Sold
				productModel.pch = 0 ##: Price Change (-/+)
				productModel.cpt = 1 ##: Current Product Tier
				productModel.put()
	except Exception as e:
		logging.error('Error updating price Tier Values in the ProductModel, in function (createProductPriceTier) :  --  %s' % str(e))
	
	return newProductTierPricing
	

def parseDigiKey(urlsafeProductKey, productNumber=None, quantity=None, region='US'):
	"""
	This function will parse the DigiKey website for each productNumber/quantity pair it has.
	If quantity is supplied it will parse the site ONCE for that particular quantity number.
	If no quantity is supplied it will run thru a loop of pre-determined quantityTiers parsing the site for each particular quantity Tier.
	If a quantity is supplied it will return a dictionary of parsedData
	Else: if a quantity arg is None then it will not return anything (Typically would be done as a deferred call)
	"""
	try:
		productModel = None
		quantityTiers = [1]
		priceTiers = {}
		previousPrice = 0
		update_meq = True
		logging.info('supplied quantity: {}'.format(quantity))

		if not urlsafeProductKey and not productNumber:
			raise Exception('Neither a partKey or a productNumber was supplied to the function parseDigiKey')
		if urlsafeProductKey:
			productModel = ndb.Key(urlsafe=urlsafeProductKey).get()
			if productModel:
				logging.info('Here')
				productNumber = str(productModel.pn)
			else:
				raise Exception('Could not find a ProductModel using the productKey arg in the function parseDigiKey')
		#
		if not quantity or quantity < 1:
			logging.info('Here')
			if productModel:
				productPriceTiers = shoppingModels.ProductTierPrice.get_for_product(productModel.pn, productModel.key)
				if not productPriceTiers:
					quantityTiers = [1,10,100,250,500,1000,2500,5000,10000]
			else:
				raise Exception('Neither a productModel was found or a quantity was supplied to the function parseDigiKey')
		else:
			quantityTiers = [quantity]

		logging.info('quantityTiers: {}'.format(quantityTiers))

		##: Setup a dictionary which we will fill with the data we parse and then return this object
		parsedData = {	'm':None,'pn':None,'d':None, \
						'ot':None,'mt':None,'pc':None, \
						'sdp':None,'p':None,'qa':None, \
						'mq':None, 'bup':None, 'cat':None, \
						'lp':0, 'dkl':None, 'img':None, 'ds':None,\
						}

		## Loop thru the different Price Tiers to populate a dictionary from the results.
		for tier in quantityTiers:
			try:
				# URL for DigiKey
				dk_url = 'http://search.digikey.com/scripts/DkSearch/dksus.dll'
				# KWARGS for Digikey Search
				dk_params = '?k=%s&mnonly=0&newproducts=0&ColumnSort=1000011&page=1&stock=0&pbfree=0&rohs=0&quantity=%s&ptm=0&fid=0' % (str(productNumber),str(tier))
				sock = urlopen(dk_url + dk_params)
				parser = Parser()
				parser.feed(sock.read())
				sock.close()
				parser.close()
			except Exception as e:
				logging.error('Error with urlopen or parser initialization :  --  %s' % str(e))
				return None

			try:
				if parser:
					logging.info('Here')
					if len(parser.rows) > 0:
						part = parser.rows[0]
						for k, v in part.items():
							# Manufacturer
							if str(k) == str(headers[1]):
								parsedData['m'] = str(v)
							# Manufacturer Part Number
							if str(k) == str(headers[2]):
								parsedData['pn'] = str(v)
							# Description
							if str(k) == str(headers[3]):
								parsedData['d'] = str(v)
							# Operating Temperature
							if str(k) == str(headers[4]):
								parsedData['ot'] = str(v)
							# Mounting Type
							if str(k) == str(headers[5]):
								parsedData['mt'] = str(v)
							# Package / Case
							if str(k) == str(headers[6]):
								parsedData['pc'] = str(v)
							# Supplier Device Package
							if str(k) == str(headers[7]):
								parsedData['sdp'] = str(v)
							# Packaging
							if str(k) == str(headers[8]):
								parsedData['p'] = str(v)
							# Quantity Available
							if str(k) == str(headers[9]):
								try:
									qa = str(v).split(' ')[0].strip().replace(",", "")
									qa = int(qa)
									parsedData['qa'] = qa
								except:
									parsedData['qa'] = None
							# Minimum Quantity
							if str(k) == str(headers[10]):
								parsedData['mq'] = str(v)
							# Unit Price
							if str(k) == str(headers[11]):
								price = str(v)
								up = str(price).split('@')[0].strip() ##: Dollars
								rup = round(float(up), 2)*100 ##: rup = Rounded Unit Price (Cents)
								if rup >= int(float(up)*100):
									parsedData['bup'] = int(float(up)*100) ##: Cents
								else:
									parsedData['bup'] = int(rup) ##: Cents
					else:
						logging.error('The Parser object did not have any rows of data')
						return None
				else:
					logging.error('A Parser object was not created')
					return None
				
				##: At this stage things have works and we have the data from the Parser Object
				##: We will run a few more calculations before returning the data
				logging.info('Tier: %s' % str(tier))
				
				if parsedData['bup']:
					logging.info('There is an up')
					priceTiers[str(tier)] = parsedData['bup']
					previousPrice = parsedData['bup']
				else:
					logging.error('Did not find unitPrice value in returned parser info, so cannot add Price Tier to Dictionary for Model')
					if previousPrice > 0:
						priceTiers[str(tier)] = previousPrice
					else:
						priceTiers[str(tier)] = None
					

			except BaseException as e:
				logging.error('Error using data from the created parser object :  --  %s' % str(e))
				return None

		##: All Done the Loop of priceTiers
		if not quantity:
			logging.info('Here')
			parsedData['priceTiers'] = priceTiers
			if productModel:
				##: After we have completed the loop and gathered the Data call the createProductPriceTier Function
				logging.info('Calling createProductPriceTier')
				productTierPrice = createProductPriceTier(productModel, productNumber, parsedData)
				logging.info('Calling createProductPriceTier')

		else:
			logging.info('Here')
			##: We run a string substitution on the Image link to get the full size image rather than the thumb image
			parsedData['img'] = re.sub(u'tmb.jpg', u'sml.jpg', parser.images[0], flags=re.IGNORECASE)
			parsedData['isl'] = parser.datasheets[0]
			if len(parser.categories)>0: parsedData['cat'] = parser.categories[-1]
			else: parsedData['cat'] = None
			##:  We must add the digikey address onto the retruned DigiKey link from our parser.
			if parser.dk_links[0]: dk_link = "http://www.digikey.com/"+ str(parser.dk_links[0])
			else: dk_link = None
			parsedData['spl'] = dk_link

			return parsedData

	except Exception as e:
		logging.error('Error creating new Product Pricing model in function (parseDigiKey) :  --  %s' % str(e))


def DK_Search(sellerModel, productNumber, quantity=1, region='US'):
	"""
	This function gets called is we have not found any record of any productModel using the searched productNumber.
	We then turn to the Parser and search the DigiKey website for this productNumber.
	the parser will return the requested data in a dictionary.
	We then create the new productModel.
	Returns the productModel and the bestPrice
	"""
	##: Setup the initial variables
	productModel = None
	partKey = None
	try:
		parseData = parseDigiKey(None, str(productNumber), int(quantity), str(region))
		
		logging.info('Manufacturer Part Number from DigiKey: %s' % str(parseData['pn']))
		
		productKey = None
		if parseData:
			logging.info('Received Parse Data')
			##: Now create the Model
			if sellerModel:
				parseData['sk'] = sellerModel.key
				parseData['pCat'] = sellerModel.cat
			else:
				parseData['sk'] = None
				parseData['pCat'] = None
			productModel = shoppingModels.Product.create_from_parse_data(parseData)

		if productModel:
			logging.info('We have a product')
			# We reached the end now return the info
			return productModel, parseData['bup'] ##: up = Unit Price (Cents)
		else:
			logging.info('No productKey')
			return None, None
		
	except BaseException as e:
		logging.error('Creating productModel failed in (DK_Search):  --  %s' % str(e))




