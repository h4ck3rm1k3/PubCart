#!/usr/bin/env python
# encoding: utf-8
"""
registrationHandlers.py

Created by Jason Elbourne on 2013-03-25.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:	 Python Imports
import re
import logging
import httpagentparser
from datetime import datetime

##:	 Webapp2 Imports
import webapp2
from webapp2_extras.i18n import gettext as _
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError


##:	 Google Imports
from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.datastore.datastore_query import Cursor

##:	 BournEE Imports
import forms as forms
from models import shoppingModels, userModels
from lib import bestPrice
from lib import utils
from lib.utils import dollar_float
from lib.bourneehandler import RegisterBaseHandler, BournEEHandler, user_required
from lib.exceptions import FunctionException
from lib import paypal_settings as settings
from lib.livecount.counter import LivecountCounter

##:	 Boilerplate Imports
from boilerplate.lib.basehandler import BaseHandler

class SoftRegisterRequestHandler(RegisterBaseHandler):
	def get(self):
		try:
			continue_url = self.request.get('continue_url', None)

			params = {
					'form': self.form,
					}
			self.bournee_template('/registration/softRegistration.html', **params)
		except Exception as e:
			logging.error('Error during PreLaunchSignupHandler: -- {}'.format(e))
			##: TODO have a safe page to redirect to incase the home page has a server error.....we want a clean failure here for the user.

	def post(self):
		""" Get fields from POST dict """
		try:
			continue_url = self.request.get('continue_url',None)
			
			if not self.form.validate():
				return self.get()
			email = str(self.form.email.data).lower()
			
			##: Check if the supplied email is valid.
			if not utils.is_email_valid(email):
				message = _('Sorry, this email does not seem to be valid: {}'.format(str(email)))
				self.add_message(message, 'error')
				return self.get()
			
			##: Check if a user exists with this email, if one does exist tell the user to log in.
			userModel = userModels.User.get_by_email(str(email))
			if userModel:
				message = _('A user already exists with the supplied email, {}, please log in above.'.format(str(email)))
				self.add_message(message, 'warning')
				return self.get()

			##: Check to see is this email has been saved to the EmailLeads Models.
			existing = userModels.EmailLeads.query(userModels.EmailLeads.email==str(email)).get()
			if not existing:
				emailLead = userModels.EmailLeads()
				emailLead.email = str(email)
				emailLead.ip = str(self.request.remote_addr)
				emailKey = emailLead.put()
				if not emailKey:
					logging.error('Error saving emailLead model in <post> of PreLaunchSignupHandler.')
					message = _('Sorry, we are having troubles saving the email to our servers at this time. Please try again later.')
					self.add_message(message, 'error')
					return self.get()
				message = _('Your email, {}, is now register with PubCart, Lets continue.'.format(str(email)))
				self.add_message(message, 'success')
			else:
				emailKey = existing.key
				message = _('The email, {}, is in our records but is not associated with an account, Let\'s continue.'.format(str(email)))
				self.add_message(message, 'success')

			if continue_url: return self.redirect_to('intimateRegister', ek=str(emailKey.urlsafe()), continue_url=continue_url)
			else: return self.redirect_to('intimateRegister', ek=str(emailKey.urlsafe()))

		except Exception as e:
			logging.error('Error with <post> of PreLaunchSignupHandler: -- {}'.format(e))
			message = _('Sorry, we are having troubles saving the email to our servers at this time. Please try again later.')
			self.add_message(message, 'error')
			return self.get()
		
		
	@webapp2.cached_property
	def form(self):
		return forms.PreRegisterForm(self)

class IntimateRegisterRequestHandler(BaseHandler):
	def get(self, ek):
		continue_url = self.request.get('continue_url', None)
		try:
			if self.user:
				if continue_url: return self.redirect_to('addressRegister', uk=self.user_key.urlsafe(),  continue_url=continue_url)
				else: return self.redirect_to('addressRegister', uk=self.user_key.urlsafe())
			
			try:
				emailModel = None
				urlsafeEmailKey = str(ek)
				
				if urlsafeEmailKey:
					emailModel = ndb.Key(urlsafe=urlsafeEmailKey).get()
				if not emailModel:
					message = _('Sorry, we are experiencing a problem with the email set in the last step.')
					self.add_message(message, 'error')
					if continue_url: return self.redirect_to('softRegister', ck=str(urlsafeEmailKey), continue_url=continue_url)
					else: return self.redirect_to('softRegister', ck=str(urlsafeEmailKey))
				if not utils.is_email_valid(emailModel.email):
					message = _('Sorry, the email {} from the last step does not seem to be valid.'.format(str(emailModel.email)))
					self.add_message(message, 'error')
					if continue_url: return self.redirect_to('softRegister', ck=str(urlsafeEmailKey), continue_url=continue_url)
					else: return self.redirect_to('softRegister', ck=str(urlsafeEmailKey))
			except Exception as e:
				logging.error('Error during urlsafeEmailKey retrieval in PreLaunchSignupHandler: -- {}'.format(e))
				message = _('Sorry, we are experiencing a problem on our servers. Please try again later.')
				self.add_message(message, 'error')
				if continue_url: return self.redirect_to('softRegister', ck=str(urlsafeEmailKey), continue_url=continue_url)
				else: return self.redirect_to('softRegister', ck=str(urlsafeEmailKey))

			params = {
					'form': self.form,
					}
			self.render_template('/registration/intimatesRegistration.html', **params)
		except Exception as e:
			logging.error('Error during IntimateRegisterRequestHandler: -- {}'.format(e))
			if continue_url: return self.redirect_to('softRegister', continue_url=continue_url)
			else: return self.redirect_to('softRegister')

	def post(self, ek):
		try:
			continue_url = self.request.get('continue_url', None)

			if not self.form.validate():
				message = _('Sorry, the form submission does not seem to be valid.')
				self.add_message(message, 'error')
				return self.get(ek)
			username = str(self.form.username.data)
			password = self.form.password.data.strip()
			name = None
			country = None
			email = None
			try:
				emailModel = ndb.Key(urlsafe=ek).get()
				email = emailModel.email
				if not utils.is_email_valid(email):
					raise Exception('utils.is_email_valid(email) failed')
				if not email: raise Exception('Email is none')
			except Exception as e:
				logging.error('Error, getting email during IntimateRegisterRequestHandler step of Registration: {}'.format(e))
				message = _('Sorry, the email from the previous step does not appear to be valid.')
				self.add_message(message, 'error')
				return self.get(ek)
		
			# Password to SHA512
			password = utils.hashing(password, self.app.config.get('salt'))

			# Passing password_raw=password so password will be hashed
			# Returns a tuple, where first value is BOOL.
			# If True ok, If False no new user is created
			unique_properties = ['username', 'email']
			auth_id = "own:%s" % username.lower()
			user = self.auth.store.user_model.create_user(
				auth_id, unique_properties, password_raw=password,
				username=username, name=name, email=email,
				ip=self.request.remote_addr, country=country
			)

			if not user[0]: #user is a tuple
				if "username" in str(user[1]):
					message = _('Sorry, The username %s is already registered.' % '<strong>{0:>s}</strong>'.format(username) )
				elif "email" in str(user[1]):
					message = _('Sorry, The email %s is already registered.' % '<strong>{0:>s}</strong>'.format(email) )
				else:
					message = _('Sorry, The user is already registered.')
				self.add_message(message, 'error')
				return self.get(ek)
			else:
				# User registered successfully
				# But if the user registered using the form, the user has to check their email to activate the account ???
				try:
					
					userModel = user[1].key.get()
					if userModel:
						self.auth.set_session(self.auth.store.user_to_dict(userModel), remember=True)

						if (userModel.activated == False):
							# send email
							subject =  _("%s Account Verification" % self.app.config.get('app_name'))
							confirmation_url = self.uri_for("account-activation",
								user_id=userModel.get_id(),
								token = userModels.User.create_auth_token(userModel.get_id()),
								_full = True)
											
							# load email's template
							template_val = {
								"app_name": self.app.config.get('app_name'),
								"username": username,
								"confirmation_url": confirmation_url,
								"support_url": self.uri_for("contact", _full=True)
							}
							body_path = "emails/account_activation.txt"
							body = self.jinja2.render_template(body_path, **template_val)
											
							email_url = self.uri_for('taskqueue-send-email')
							taskqueue.add(url = email_url, params={
								'to': str(email),
								'subject' : subject,
								'body' : body,
								})
					else:
						message = _('Unexpected error creating the user %s' % username )
						self.add_message(message, 'error')
						return self.get(ek)

					address = userModels.Address.query(userModels.Address.is_default==True,ancestor=user[1].key).get()
					if address:
						if continue_url: return self.redirect_to('shareRegister', continue_url=continue_url)
						else: return self.redirect_to('shareRegister')
					else:
						if continue_url: return self.redirect_to('addressRegister', uk=user[1].key.urlsafe(), continue_url=continue_url)
						else: return self.redirect_to('addressRegister', uk=user[1].key.urlsafe())
						
				except (AttributeError, KeyError), e:
					logging.error('Unexpected error creating the user %s: %s' % (username, e ))
					message = _('Unexpected error creating the user %s' % username )
					self.add_message(message, 'error')
					return self.get(ek)

		except Exception as e:
			logging.error('Error in <POST> of IntimateRegisterRequestHandler:-- {}'.format(e))

	@webapp2.cached_property
	def form(self):
		return forms.IntimatesRegisterForm(self)

class AddressRegisterRequestHandler(BournEEHandler):
	def get(self, uk):
		continue_url = self.request.get('continue_url', None)
		try:
			urlsafeUserKey = uk
			user = ndb.Key(urlsafe=urlsafeUserKey).get()
			if not user:
				logging.error('Error, there is no user with the key supplied in uri for AddressRegisterRequestHandler')
				if continue_url: return self.redirect_to('softRegister', continue_url=continue_url)
				else: return self.redirect_to('softRegister')

			address = userModels.Address.query(userModels.Address.is_default==True,ancestor=user.key).get()
			if address:
				if continue_url: return self.redirect_to('shareRegister', continue_url=continue_url)
				else: return self.redirect_to('shareRegister')
				
			params = {
					'user': user,
					'urlsafeUserKey': urlsafeUserKey,
					'form': self.form,
					}
			self.bournee_template('/registration/addressRegistration.html', **params)
		except Exception as e:
			logging.error('Error during AddressRegisterRequestHandler: -- {}'.format(e))
			message = _('Sorry, there was a server error after creating your account, please try again later.')
			self.add_message(message, 'error')
			if continue_url: return self.redirect_to('softRegister', continue_url=continue_url)
			else: return self.redirect_to('softRegister')


	def post(self, uk):
		try:
			if not self.form.validate():
				return self.get(uk)

			continue_url = self.request.get('continue_url', None)
			
			##: Try to fetch the data from the Form responce
			urlsafeUserKey = str(self.form.uk.data).strip() ##: Urlsafe Key
			full_name = str(self.form.n.data).strip()
			address = str(self.form.ad.data).strip()
			city = str(self.form.c.data).strip()
			state = str(self.form.s.data).strip()
			country = str(self.form.con.data).strip()
			zip_code = str(self.form.z.data).strip()
			phoneNumber = self.form.pn.data

			if urlsafeUserKey == uk:
				userKey = ndb.Key(urlsafe=urlsafeUserKey)
				keyName = 'MAIN'
				address_key = ndb.Key(userModels.Address, keyName, parent=userKey)
				params = {
					'uk': userKey, \
					'key': address_key, \
					'adn' : 'MAIN', \
					'n' : full_name, \
					'ad' : address, \
					'c' : city, \
					's':state, \
					'con' : country, \
					'z' : zip_code, \
					'pn' : phoneNumber, \
					'is_default' : True, \
				}
				address = userModels.Address.create_address(params, put_model=False)
			
				userModel = userKey.get()
				if userModel:
					userModel.name = full_name
					userModel.country = country
					ndb.put_multi([userModel,address])
				else:
					logging.error("Could not find userModel with supplied userKey")
					address.put()
				
				if continue_url: return self.redirect_to('shareRegister', continue_url=continue_url)
				else: return self.redirect_to('shareRegister')

			else:
				logging.error("User Keys did not match between form and uri")
				raise Exception('User Keys did not match between form and uri')

		except Exception as e:
			logging.error("Error occurred running function POST of class AddAddressHandler: -- %s" % str(e))
			message = _('There was an Error during form Submission. We can not complete request. Please try again Later')
			self.add_message(message, 'error')
			return self.get(uk)


	@webapp2.cached_property
	def form(self):
		return forms.RegisterAddressForm(self)


class ShareRegisterRequestHandler(BournEEHandler):
	@user_required
	def get(self):
		continue_url = self.request.get('continue_url', None)
		try:
			params = {'continue_url':continue_url,}
			self.bournee_template('/registration/shareRegistration.html', **params)
		except Exception as e:
			logging.error('Error during AddressRegisterRequestHandler: -- {}'.format(e))
			message = _('Sorry, there was a server error after creating your account, please try again later.')
			self.add_message(message, 'error')
			if continue_url: return self.redirect_to('appRecommendRegister', continue_url=continue_url)
			else: return self.redirect_to('appRecommendRegister')

class AppsRegisterRequestHandler(BournEEHandler):
	@user_required
	def get(self):
		continue_url = self.request.get('continue_url', None)
		try:
			params = {'continue_url':continue_url,}
			self.bournee_template('/registration/appsRegistration.html', **params)
		except Exception as e:
			logging.error('Error during AddressRegisterRequestHandler: -- {}'.format(e))
			message = _('Sorry, there was a server error after creating your account, please try again later.')
			self.add_message(message, 'error')
			if continue_url:
				try:
					return self.redirect(continue_url)
				except:
					pass
			return self.redirect_to('home')