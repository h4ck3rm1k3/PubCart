#!/usr/bin/env python
# encoding: utf-8
"""
userModels.py

Created by Jason Elbourne on 2013-02-14.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import logging

from google.appengine.ext import ndb
from boilerplate.models import User

class User(User):
	paypal_email = ndb.StringProperty(default=None)

class EmailLeads(ndb.Model):
	email = ndb.StringProperty(required=True)
	
class Address(ndb.Model):
	uk = ndb.KeyProperty(kind=User) ##: User Model Key
	adn = ndb.StringProperty(required=True) ##: Address Name

	n = ndb.StringProperty(required=True) ##: Name
	ad1 = ndb.StringProperty(required=True) ##: Address1
	ad2 = ndb.StringProperty() ##: Address2
	c = ndb.StringProperty(required=True) ##: City
	s = ndb.StringProperty(required=True) ##: State/Province
	con = ndb.StringProperty(required=True) ##: Country
	z = ndb.StringProperty(required=True) ##: Zip Code / Postal Code
	pn = ndb.IntegerProperty(required=True) ##: Phone Number
	
	is_default = ndb.BooleanProperty(default=True)
	
	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@classmethod
	def get_for_UserKey(cls, userKey, quantity):
		return cls.query(ancestor=userKey).fetch(quantity)


class Seller(ndb.Model):
	n = ndb.StringProperty(required=True) ##: Name
	dom = ndb.StringProperty(required=True) ##: Domain
	cn = ndb.StringProperty(required=True) ##: Contact Name
	pn = ndb.IntegerProperty(required=True) ##: Phone Number
	cat = ndb.StringProperty(required=True) ##: Category
	
	auth = ndb.BooleanProperty(default=True) ##: Authenticated
	active = ndb.BooleanProperty(default=True) ##: Account is active
	parser = ndb.StringProperty(default=None) ##: Parser Name (eg: DIGIKEY)
	
	cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@staticmethod
	def get_all_for_category(category, quantity=999):
		return Seller.query(ndb.AND(Seller.auth==True,Seller.active==True,Seller.cat==str(category).upper())).fetch(quantity)


def set_default_address(urlsafeAddressKey, userKey):
	def chg_default(address):
		address.is_default = False
		return address
	defaultAddress = ndb.Key(urlsafe=urlsafeAddressKey).get()
	defaultAddress.is_default = True
	addresses = Address.query(Address.is_default==True, ancestor=userKey).fetch(10)
	logging.info(addresses)
	
	changed_addresses = [chg_default(address) for address in addresses if address.key != defaultAddress.key and address.is_default == True ]
	changed_addresses.append(defaultAddress)
	logging.info(changed_addresses)
	
	ndb.put_multi(changed_addresses)