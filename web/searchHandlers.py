#!/usr/bin/env python
# encoding: utf-8
"""
searchHandlers.py

Created by Jason Elbourne on 2013-03-14.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import urllib
import logging

from google.appengine.api import search
from google.appengine.ext import ndb

from lib.bourneehandler import RegisterBaseHandler
from lib import searchDocument as docs
from lib import utils
from models import shoppingModels, categoryModels

class ProductSearchHandler(RegisterBaseHandler):
	"""The handler for doing a product search."""

	_DEFAULT_DOC_LIMIT = 10  #default number of search results to display per page.
	_OFFSET_LIMIT = 1000

	def parseParams(self):
		"""Filter the param set to the expected params."""
		params = {
			'qtype': '',
			'query': '',
			'category': '',
			'sort': '',
			'rating': '',
			'offset': '0'
			}
		for k, v in params.iteritems():
			# Possibly replace default values.
			params[k] = self.request.get(k, v)
		return params

	def post(self):
		params = self.parseParams()
		self.redirect('/search?' + urllib.urlencode(
			dict([k, v.encode('utf-8')] for k, v in params.items())))

	def _getDocLimit(self):
		"""if the doc limit is not set in the utils file, use the default."""
		doc_limit = self._DEFAULT_DOC_LIMIT
		try:
			doc_limit = int(utils.DOC_LIMIT)
		except ValueError:
			logging.error('DOC_LIMIT not properly set in utils file; using default.')
		return doc_limit

	def get(self):
		"""Handle a product search request."""

		params = self.parseParams()
		self.doProductSearch(params)

	def doProductSearch(self, params):
		"""Perform a product search and display the results."""
		# the product fields that we can sort on from the UI, and their mappings to
		# search.SortExpression parameters
		sort_info = docs.Product.getSortMenu()
		sort_dict = docs.Product.getSortDict()
		query = params.get('query', '')
		user_query = query
		doc_limit = self._getDocLimit()

		categoryq = params.get('category')
		if categoryq:
			# add specification of the category to the query
			# Because the category field is atomic, put the category string
			# in quotes for the search.
			query += ' %s:"%s"' % (docs.Product.PARENT_CATEGORY, categoryq)

		subcategoryq = params.get('subcategory')
		if subcategoryq:
			# add specification of the category to the query
			# Because the category field is atomic, put the category string
			# in quotes for the search.
			query += ' %s:"%s"' % (docs.Product.CATEGORY, subcategoryq)

		sortq = params.get('sort')
		if not sortq: sortq = 'relevance'
		logging.info('sortq: {}'.format(sortq))
		try:
			offsetval = int(params.get('offset', 0))
		except ValueError:
			offsetval = 0

		# Check to see if the query parameters include a ratings filter, and
		# add that to the final query string if so.  At the same time, generate
		# 'ratings bucket' counts and links-- based on the query prior to addition
		# of the ratings filter-- for sidebar display.
		query, rlinks = self._generateRatingsInfo(
			params, query, user_query, sortq, categoryq)
		logging.info('query: %s', query.strip())

		try:
			# build the query and perform the search
			logging.info('Here')
			search_query = self._buildQuery(
				query, sortq, sort_dict, doc_limit, offsetval)
			logging.info('search_query:  {}'.format(search_query))
				
			search_results = docs.Product.getIndex().search(search_query)
			returned_count = len(search_results.results)
			logging.info('search_results:  {}'.format(search_results))

		except search.Error:
			logging.exception("Search error:")  # log the exception stack trace
			message = _('An error occurred while searching the site. Please try again later.')
			self.add_message(message, 'error')
			try:
				self.redirect(self.request.referer)
			except:
				self.redirect_to('home')

		# cat_name = shoppingModels.getCategoryName(categoryq)
		psearch_response = []
		# For each document returned from the search
		modelsToMultiGet = []
		for doc in search_results:
			modelsToMultiGet.append(ndb.Key(urlsafe=str(doc.doc_id)))
			
			# # logging.info("doc: %s ", doc)
			# pdoc = docs.Product(doc)
			# # use the description field as the default description snippet, since
			# # snippeting is not supported on the dev app server.
			# description_snippet = pdoc.getDescription()
			# price = pdoc.getPrice()
			# # on the dev app server, the doc.expressions property won't be populated.
			# logging.info('Here')
			# for expr in doc.expressions:
			# 	if expr.name == docs.Product.DESCRIPTION:
			# 		description_snippet = expr.value
			# 	# uncomment to use 'adjusted price', which should be
			# 	# defined in returned_expressions in _buildQuery() below, as the
			# 	# displayed price.
			# 	# elif expr.name == 'adjusted_price':
			# 		# price = expr.value
			# 
			# # get field information from the returned doc
			# pid = pdoc.getProductNumber()
			# cat = catname = pdoc.getCategory()
			# pname = pdoc.getName()
			# avg_rating = pdoc.getAvgRating()
			# urlsafeKey = doc.doc_id
			# # for this result, generate a result array of selected doc fields, to
			# # pass to the template renderer
			# psearch_response.append(
			# 	[doc, urllib.quote_plus(pid), cat,
			# 	description_snippet, price, pname, catname, avg_rating, urlsafeKey])
		if not query:
			print_query = 'All'
		else:
			print_query = query
		
		try:
			modelResults = None
			if modelsToMultiGet:
				if len(modelsToMultiGet)==1: modelResults = [modelsToMultiGet[0].get()]
				elif len(modelsToMultiGet) > 1: modelResults = ndb.get_multi(modelsToMultiGet)
		except Exception as e:
			logging.error('Could not get_multi from search document urlsafeKeys: -- {}'.format(e))
		# Build the next/previous pagination links for the result set.
		(prev_link, next_link) = self._generatePaginationLinks(
			offsetval, returned_count,
			search_results.number_found, params)
			
		logging.info('returned_count: %s', returned_count)
		# construct the template values
		params = {
			'modelResults':modelResults,
			'base_pquery': user_query, 'next_cursor': next_link,
			'prev_cursor': prev_link, 'qtype': 'product',
			'query': query, 'print_query': print_query,
			'pcategory': categoryq, 'sort_order': sortq, 'category_name': categoryq,
			'first_res': offsetval + 1, 'last_res': offsetval + returned_count,
			'returned_count': returned_count,
			'number_found': search_results.number_found,
			# 'search_response': psearch_response,
			'sort_info': sort_info,
			'ratings_links': rlinks}
		# render the result page.
		self.bournee_template('searchResults.html', **params)
		
	def _buildQuery(self, query, sortq, sort_dict, doc_limit, offsetval):
		"""Build and return a search query object."""

		# computed and returned fields examples.  Their use is not required
		# for the application to function correctly.
		
		computed_expr = search.FieldExpression(name='adjusted_price',
				expression='price * 1.08')
		returned_fields = [docs.Product.PRODUCT_NUMBER, docs.Product.DESCRIPTION,
				docs.Product.CATEGORY, docs.Product.AVG_RATING,
				docs.Product.BEST_PRICE, docs.Product.PRODUCT_NAME]

		if sortq == 'relevance':
 			# If sorting on 'relevance', use the Match scorer.
			sortopts = search.SortOptions(match_scorer=search.MatchScorer())
			
			search_query = search.Query(
					query_string=query.strip(),
					options=search.QueryOptions(
					limit=doc_limit,
					offset=offsetval,
					sort_options=sortopts,
					snippeted_fields=[docs.Product.DESCRIPTION],
					returned_expressions=[computed_expr],
					returned_fields=returned_fields
					))
		else:			
			# Otherwise (not sorting on relevance), use the selected field as the
			# first dimension of the sort expression, and the average rating as the
			# second dimension, unless we're sorting on rating, in which case price
			# is the second sort dimension.
			# We get the sort direction and default from the 'sort_dict' var.
			if sortq == docs.Product.AVG_RATING:
				expr_list = [sort_dict.get(sortq), sort_dict.get(docs.Product.BEST_PRICE)]
				logging.info('Here')
			else:
				expr_list = [sort_dict.get(sortq), sort_dict.get(docs.Product.AVG_RATING)]
				logging.info('Here')
			logging.info('Here')
			
			sortopts = search.SortOptions(expressions=expr_list)
			logging.info('Here')
			
			# logging.info("sortopts: %s", sortopts)
			search_query = search.Query(
						query_string=query.strip(),
						options=search.QueryOptions(
						limit=doc_limit,
						offset=offsetval,
						sort_options=sortopts,
						snippeted_fields=[docs.Product.DESCRIPTION],
						returned_expressions=[computed_expr],
						returned_fields=returned_fields
						))
		return search_query

	def _generateRatingsInfo(self, params, query, user_query, sort, category):
		"""Add a ratings filter to the query as necessary, and build the
		sidebar ratings buckets content."""

		orig_query = query
		try:
			n = int(params.get('rating', 0))
			# check that rating is not out of range
			if n < utils.RATING_MIN or n > utils.RATING_MAX:
				n = None
		except ValueError:
			n = None
		if n:
			if n < utils.RATING_MAX:
				query += ' %s >= %s %s < %s' % (docs.Product.AVG_RATING, n,
						docs.Product.AVG_RATING, n+1)
			else:  # max rating
				query += ' %s:%s' % (docs.Product.AVG_RATING, n)
		query_info = {'query': user_query.encode('utf-8'), 'sort': sort,
				'category': category}
		rlinks = docs.Product.generateRatingsLinks(orig_query, query_info)
		return (query, rlinks)

	def _generatePaginationLinks(self, offsetval, returned_count, number_found, params):
		"""Generate the next/prev pagination links for the query.  Detect when we're
		out of results in a given direction and don't generate the link in that
		case."""

		doc_limit = self._getDocLimit()
		pcopy = params.copy()
		if offsetval - doc_limit >= 0:
			pcopy['offset'] = offsetval - doc_limit
			prev_link = '/search?' + urllib.urlencode(pcopy)
		else:
			prev_link = None
		if ((offsetval + doc_limit <= self._OFFSET_LIMIT)
				and (returned_count == doc_limit)
				and (offsetval + returned_count < number_found)):
			pcopy['offset'] = offsetval + doc_limit
			next_link = '/search?' + urllib.urlencode(pcopy)
		else:
			next_link = None
		return (prev_link, next_link)


