#!/usr/bin/env python
# encoding: utf-8
"""
categoryModels.py

Created by Jason Elbourne on 2013-03-17.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

import logging

from google.appengine.ext import ndb

from lib import searchDocument
from lib import searchCategories

class Category(ndb.Model):
	"""The model class for product category information.  Supports building a
	category tree."""

	_CATEGORY_INFO = None
	_CATEGORY_DICT = None
	_RCATEGORY_DICT = None
	_ROOT = 'ROOT'  # the 'root' category of the category tree

	parent_category = ndb.KeyProperty()
	name = ndb.StringProperty()

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
		try:
			if not category_data:
				return
			cname = category_data.get('name')
			if not cname:
				logging.warn('no category name')
				return
			else:
				safeCName = str(cname.replace("|", "%7C").replace("/", "%2F").replace(" ", "_").replace(":", "%3A")).upper()
			
			##: Check if existing
			existingCat = Category.query(Category.name==safeCName, ancestor=parent_key).count()
			if existingCat < 1:
				##: Initialize a Category Model
				cat = Category()
				cat.name = cname
				if parent_key:
					cat.key = ndb.Key(Category, safeCName, parent=parent_key)
					cat.parent_category = parent_key
				else:
					cat.key = ndb.Key(Category, safeCName)
				cat.put()

				children = category_data.get('children')
				if len(children)>0:
					# if there are any children, build them using their parent key
					cls.buildChildCategories(children, cat.key)
				else: return
			else: return
		except Exception as e:
			logging.error('Error creating categories and child categories: -- {}'.format(e))


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
		cls.buildAllCategories()  	#first build categories from data file if required
		parent_key = ndb.Key(Category, cls._ROOT)
		cats = cls.query(ancestor=parent_key).fetch()
		cats_info = [(c.key.id(), c.name) for c in cats if c.key.id() != cls._ROOT]
		return cats_info

	@classmethod
	def getSubCategoryInfo(cls, parent_key):
		"""Build a list of sub-category id/name correspondences.  This info is
		used to populate html select menus."""
		cats = cls.query(ancestor=parent_key).fetch()
		cat_info = [(c.key.id(), c.name) for c in cats if c.key.id() != cls._ROOT]
		return cat_info


# class SubCategory(ndb.Model):
# 	"""The model class for product category information.  Supports building a
# 	category tree."""
# 
# 	parent_category = ndb.KeyProperty()
# 	name = ndb.StringProperty()
# 
# 	@property
# 	def category_safe_name(self):
# 		return self.key.id()
# 
# 	@classmethod
# 	def buildCategory(cls, name, parent_key):
# 		"""build a category and any children from the given data dict."""
# 		try:
# 			cname = str(name)
# 			if not cname:
# 				logging.warn('no category name')
# 				return
# 			else:
# 				safeCName = str(cname.replace("|", "%7C").replace("/", "%2F").replace(" ", "_").replace(":", "%3A")).upper()
# 			
# 			if parent_key.kind() != 'Category':
# 				logging.warn('parent_key was of the wrong Kind (not Category)')
# 				return
# 			else:
# 				parent = parent_key.get()
# 				if not parent:
# 					logging.warn('no category name')
# 					return
# 			
# 			##: Check if existing
# 			existingCat = SubCategory.query(Category.name==safeCName, ancestor=parent_key).count()
# 			if existingCat < 1:
# 				##: Initialize a Category Model
# 				cat = Category()
# 				cat.name = cname
# 				if parent_key:
# 					cat.key = ndb.Key(Category, safeCName, parent=parent_key)
# 					cat.parent_category = parent_key
# 				else:
# 					cat.key = ndb.Key(Category, safeCName)
# 				cat.put()
# 				return
# 
# 			else: return
# 		except Exception as e:
# 			logging.error('Error creating sub-category: -- {}'.format(e))
