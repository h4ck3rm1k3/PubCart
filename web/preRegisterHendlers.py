#!/usr/bin/env python
# encoding: utf-8
"""
preRegisterHendlers.py

Created by Jason Elbourne on 2013-03-12.
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
from google.appengine.api import memcache
from google.appengine.datastore.datastore_query import Cursor

##:	 BournEE Imports
import forms as forms
from models import shoppingModels, userModels
from lib import bestPrice
from lib import utils
from lib.utils import dollar_float
from lib.bourneehandler import RegisterBaseHandler, BournEEHandler
from lib.exceptions import FunctionException
from lib import paypal_settings as settings

##:	 Boilerplate Imports
from boilerplate import models
from boilerplate.lib.basehandler import user_required
from boilerplate.lib.basehandler import BaseHandler

class PreLaunchSignupHandler(RegisterBaseHandler):
	def get(self):
		try:
			if self.user:
				return self.redirect_to('preLaunchThankyou')
			params = {
					'form': self.form,
					}
			self.bournee_template('preRegisterSignIn.html', **params)
		except:
			logging.error('Error during PreLaunchSignupHandler')

	def post(self):
		""" Get fields from POST dict """

		if not self.form.validate():
			return self.get()
		username = self.form.username.data.strip()
		email = self.form.email.data.lower()
		
		tempPassword = utils.random_string(size=10)
		# Password to SHA512
		password = utils.hashing(tempPassword, self.app.config.get('salt'))

		# Passing password_raw=password so password will be hashed
		# Returns a tuple, where first value is BOOL.
		# If True ok, If False no new user is created
		unique_properties = ['username', 'email']
		auth_id = "own:%s" % username
		user = self.auth.store.user_model.create_user(
			auth_id, unique_properties, password_raw=password,
			username=username, name='Pre-Registered', last_name='Pre-Registered', email=email,
			ip=self.request.remote_addr, country='Pre-Registered'
		)

		if not user[0]: #user is a tuple
			if "username" in str(user[1]):
				message = _('Sorry, The username %s is already registered.' % '<strong>{0:>s}</strong>'.format(username) )
			elif "email" in str(user[1]):
				message = _('Sorry, The email %s is already registered.' % '<strong>{0:>s}</strong>'.format(email) )
			else:
				message = _('Sorry, The user is already registered.')
			self.add_message(message, 'error')
		else:
			# User registered successfully
			db_user = self.auth.get_user_by_password(user[1].auth_ids[0], password)
			
			try:
				message = _('Welcome %s, you are now Pre-Registered.' % '<strong>{0:>s}</strong>'.format(username) )
				self.add_message(message, 'success')
			except (AttributeError, KeyError), e:
				logging.error('Unexpected error creating the user %s: %s' % (username, e ))
				message = _('Unexpected error during pre-registration of %s' % username )
				self.add_message(message, 'error')
		
		return self.redirect_to('home')
		
		
	@webapp2.cached_property
	def form(self):
		return forms.PreRegisterForm(self)

class PreLaunchThankyouHandler(BournEEHandler):
	@user_required
	def get(self):
		try:
			params = {}
			self.bournee_template('preRegisterThankyou.html', **params)
		except:
			logging.error('Error during PreLaunchThankyouHandler')


class PreLaunchLogoutHandler(BournEEHandler):
	"""
	Destroy user session and redirect to login
	"""
	def get(self):
		try:
			if self.user:
				message = _("You've signed out successfully. Warning: Please clear all cookies and logout "
							"of OpenId providers too if you logged in on a public computer.")
				self.add_message(message, 'info')

			self.auth.unset_session()
			# User is logged out, let's try redirecting to login page
			return self.redirect_to('preLaunchSignup')
		except (AttributeError, KeyError), e:
			logging.error("Error logging out: %s" % e)
			message = _("User is logged out, but there was an error on the redirection.")
			self.add_message(message, 'error')
			return self.redirect_to('preLaunchSignup')

class PreLaunchAboutHandler(RegisterBaseHandler):
	def get(self):
		try:
			params = {
					'form': self.form,
					}
			self.bournee_template('preRegisterAbout.html', **params)
		except:
			logging.error('Error during PreLaunchAboutHandler')

	@webapp2.cached_property
	def form(self):
		return forms.RegisterForm(self)

class PreLaunchJobsHandler(RegisterBaseHandler):
	def get(self):
		try:
			params = {
				'form': self.form,
					}
			self.bournee_template('preRegisterJobs.html', **params)
		except:
			logging.error('Error during PreLaunchAboutHandler')

	@webapp2.cached_property
	def form(self):
		return forms.RegisterForm(self)

