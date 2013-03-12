# -*- coding: utf-8 -*-
import webapp2
import forms
from web import cartHandlers
from models import userModels as models
from boilerplate import forms as bForms
from boilerplate.handlers import BaseHandler
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from google.appengine.api import users
from collections import OrderedDict, Counter
from wtforms import fields


class Logout(BaseHandler):
	def get(self):
		self.redirect(users.create_logout_url(dest_url=self.uri_for('home')))


class Geochart(BaseHandler):
	def get(self):
		users = models.User.query().fetch(projection=['country'])
		users_by_country = Counter()
		for user in users:
			if user.country:
				users_by_country[user.country] += 1
		params = {
			"data": users_by_country.items()
		 }
		return self.render_template('admin/geochart.html', **params)


class EditProfileForm(bForms.EditProfileForm):
	activated = fields.BooleanField('Activated')

class EditSellerForm(forms.EditSellerForm):
	active = fields.BooleanField('Activated')
	parser = fields.TextField('Parser Name')
	


class List(BaseHandler):
	def get(self):
		p = self.request.get('p')
		q = self.request.get('q')
		c = self.request.get('c')
		forward = True if p not in ['prev'] else False
		cursor = Cursor(urlsafe=c)

		if q:
			qry = models.User.query(ndb.OR(models.User.last_name == q,
										   models.User.email == q,
										   models.User.username == q))
		else:
			qry = models.User.query()

		PAGE_SIZE = 5
		if forward:
			users, next_cursor, more = qry.order(models.User.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
			if next_cursor and more:
				self.view.next_cursor = next_cursor
			if c:
				self.view.prev_cursor = cursor.reversed()
		else:
			users, next_cursor, more = qry.order(-models.User.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
			users = list(reversed(users))
			if next_cursor and more:
				self.view.prev_cursor = next_cursor
			self.view.next_cursor = cursor.reversed()
 
		def pager_url(p, cursor):
			params = OrderedDict()
			if q:
				params['q'] = q
			if p in ['prev']:
				params['p'] = p
			if cursor:
				params['c'] = cursor.urlsafe()
			return self.uri_for('user-list', **params)

		self.view.pager_url = pager_url
		self.view.q = q
		
		params = {
			"list_columns": [('username', 'Username'),
							 ('last_name', 'Last Name'), 
							 ('email', 'E-Mail'),
							 ('country', 'Country')],
			"users" : users,
			'pageTitle': 'Users List',
			"count" : qry.count()
		}
		return self.render_template('admin/list.html', **params)


class Edit(BaseHandler):
	def get_or_404(self, user_id):
		try:
			user = models.User.get_by_id(long(user_id))
			if user:
				return user
		except ValueError:
			pass
		self.abort(404)

	def edit(self, user_id):
		if self.request.POST:
			user = self.get_or_404(user_id)
			if self.form.validate():
				self.form.populate_obj(user)
				user.put()
				self.add_message("Changes saved!", 'success')
				return self.redirect_to("user-edit", user_id=user_id)
			else:
				self.add_message("Could not save changes!", 'error')
		else:
			user = self.get_or_404(user_id)
			self.form.process(obj=user)

		params = {
			'user' : user,
			'pageTitle': 'Edit User',
			'formAction': webapp2.uri_for('user-edit', user_id=user_id),
			'cancelUrl': webapp2.uri_for('user-list'),
		}
		return self.render_template('admin/edit.html', **params)

	@webapp2.cached_property
	def form(self):
		return EditProfileForm(self)


class SellerList(BaseHandler):
	def get(self):
		p = self.request.get('p')
		q = self.request.get('q')
		c = self.request.get('c')
		forward = True if p not in ['prev'] else False
		cursor = Cursor(urlsafe=c)

		if q:
			qry = models.Seller.query(ndb.OR(models.Seller.n == q,
										   models.Seller.cn == q))
		else:
			qry = models.Seller.query()

		PAGE_SIZE = 5
		if forward:
			sellers, next_cursor, more = qry.order(models.User.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
			if next_cursor and more:
				self.view.next_cursor = next_cursor
			if c:
				self.view.prev_cursor = cursor.reversed()
		else:
			sellers, next_cursor, more = qry.order(-models.Seller.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
			sellers = list(reversed(users))
			if next_cursor and more:
				self.view.prev_cursor = next_cursor
			self.view.next_cursor = cursor.reversed()
 
		def pager_url(p, cursor):
			params = OrderedDict()
			if q:
				params['q'] = q
			if p in ['prev']:
				params['p'] = p
			if cursor:
				params['c'] = cursor.urlsafe()
			return self.uri_for('user-list', **params)

		self.view.pager_url = pager_url
		self.view.q = q
		
		params = {
			"list_columns": [('n', 'Seller'),
							 ('dom', 'Domain'), 
							 ('cn', 'Contact Name'),
							 ('pn', 'Phone Number'),
							('cat', 'Category'),
							('active', 'Active'),
							('auth', 'Authenticated')],
			"sellers" : sellers,
			'pageTitle': 'Sellers List',
			"count" : qry.count()
		}
		return self.render_template('admin/list.html', **params)

class SellerEdit(BaseHandler):
	def get_or_404(self, urlsafeSellerKey):
		try:
			seller = ndb.Key(urlsafe=urlsafeSellerKey).get()
			if seller:
				return seller
		except ValueError:
			pass
		self.abort(404)

	def edit(self, urlsafeSellerKey):
		if self.request.POST:
			seller = self.get_or_404(urlsafeSellerKey)
			if self.form.validate():
				self.form.populate_obj(seller)
				seller.put()
				self.add_message("Changes saved!", 'success')
				return self.redirect_to("seller-list")
			else:
				self.add_message("Could not save changes!", 'error')
		else:
			seller = self.get_or_404(urlsafeSellerKey)
			self.form.process(obj=seller)

		params = {
			'seller' : seller,
			'pageTitle': 'Edit Seller',
			'formAction': webapp2.uri_for('seller-edit', urlsafeSellerKey=urlsafeSellerKey),
			'cancelUrl': webapp2.uri_for('seller-list'),
		}
		return self.render_template('admin/edit.html', **params)


	def add(self):
		if self.request.POST:
			if self.form.validate():
				seller = models.Seller()
				self.form.populate_obj(seller)
				seller.put()
				self.add_message("Seller Added!", 'success')
				return self.redirect_to("seller-list")
			else:
				self.add_message("Could not save changes!", 'error')
		else:
			self.form.process()

		params = {
			'pageTitle': 'Add Seller',
			'formAction': webapp2.uri_for('seller-add'),
			'cancelUrl': webapp2.uri_for('seller-list'),
		}
		return self.render_template('admin/edit.html', **params)

	@webapp2.cached_property
	def form(self):
		return EditSellerForm(self)