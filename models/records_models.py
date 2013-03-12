#!/usr/bin/env python
# encoding: utf-8
"""
records_models.py

Created by Jason Elbourne on 2012-06-23.
Copyright (c) 2012 Jason Elbourne. All rights reserved.
"""
import logging
import config
import re

from google.appengine.ext import ndb
from libr import utils


class Corporation(ndb.Model):
	"""
		The Model for storing the API Corporation Data.
	"""
	fein = ndb.StringProperty()
	name = ndb.StringProperty()
	
	portal_id = ndb.StringProperty()
	
	created_datetime = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
	updated_datetime = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

	@staticmethod
	def _write_properties_for_api():
		return [u'fein', u'name', u'portal_id']

	@staticmethod
	def _read_properties_for_api():
		return [u'fein', u'portal_id']

	def _pre_put_hook(cls):
		key = ndb.Key(Corporation, str(cls.fein))
		cls.key	= key


class Investor(ndb.Model):
	"""
		The Model for storing the API Investor Data.
	"""
	investorId = ndb.StringProperty(required=True)
	name = ndb.StringProperty(required=True)

	portalId = ndb.StringProperty(required=True)

	createdDatetime = ndb.DateTimeProperty(auto_now_add=True, indexed=False)
	updatedDatetime = ndb.DateTimeProperty(auto_now=True)

	@staticmethod
	def _write_properties_for_api():
		return [u'investorId', u'name', u'portalId']

	@staticmethod
	def _read_properties_for_api():
		return [u'investorId']

	def _pre_put_hook(cls):
		key = ndb.Key(Investor, str(cls.investorId))
		cls.key	= key



class Investment(ndb.Model):
	"""
		Child of Investor
		The Model for storing the API Investment Data.
		
		namespace = Country
		
		parent = Investor
	"""

	corporation_key = ndb.KeyProperty('ck')

	price_interest = ndb.IntegerProperty('pi')
	shares_interest = ndb.IntegerProperty('si')

	price_confirmed = ndb.IntegerProperty('pc', default=0)
	shares_confirmed = ndb.IntegerProperty('sc', default=0)
	
	created_datetime = ndb.DateTimeProperty('cd', auto_now_add=True)
	updated_datetime = ndb.DateTimeProperty('ud', auto_now=True)

	def _pre_put_hook(cls):
		key = ndb.Key(Investment, str(cls.investor_id))
		cls.key	= key



