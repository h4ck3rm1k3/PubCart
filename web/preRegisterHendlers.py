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

##:	 BournEE Imports
import forms as forms
from models import userModels
from lib import utils

##:	 Boilerplate Imports
from boilerplate.lib.basehandler import BaseHandler

class PreLaunchSignupHandler(BaseHandler):
	def get(self):
		try:
			
			email=None
			
			newFlag = self.request.get('new', None)
			if not newFlag:
				try:
					urlsafeEmailKey = self.request.get('ck', None)
					if not urlsafeEmailKey:
						urlsafeEmailKey = utils.read_cookie(self,"pR")
					if urlsafeEmailKey:
						emailModel = ndb.Key(urlsafe=urlsafeEmailKey).get()
						if emailModel:
							email = emailModel.email
							logging.info('Email: {}'.format(email))
				except Exception as e:
					logging.error('Error during urlsafeEmailKey retrieval in PreLaunchSignupHandler: -- {}'.format(e))

			logging.info('Email: {}'.format(email))
			
			params = {
					'preReg_email': email,
					'form': self.form,
					}
			self.render_template('/prelaunch/preRegisterSignIn.html', **params)
		except Exception as e:
			logging.error('Error during PreLaunchSignupHandler: -- {}'.format(e))

	def post(self):
		""" Get fields from POST dict """
		try:
			if not self.form.validate():
				return self.get()
			email = str(self.form.email.data).lower()
			if not utils.is_email_valid(email):
				message = _('Sorry, this email does not seem to be valid.')
				self.add_message(message, 'error')
				return self.get()

			existing = userModels.EmailLeads.query(userModels.EmailLeads.email==str(email)).fetch()
			if existing:
				message = _('Sorry, this email has already been registered.')
				self.add_message(message, 'error')
				return self.get()
		
			emailLead = userModels.EmailLeads()
			emailLead.email = email
			returnedKey = emailLead.put()
			logging.info('returnedKey: {}'.format(returnedKey))
			if not returnedKey:
				logging.error('Error saving emailLead model in <post> of PreLaunchSignupHandler.')
				message = _('Sorry, we are having troubles saving the email to our servers at this time. Please try again later.')
				self.add_message(message, 'error')
				return self.get()
		
			# message = _('Welcome, you are now Pre-Registered with the email %s' % '<strong>{0:>s}</strong>'.format(email) )
			# self.add_message(message, 'success')
			utils.write_cookie(self, "pR", str(returnedKey.urlsafe()), "/", 32096000)
			return self.redirect_to('preLaunchSignup', ck=str(returnedKey.urlsafe()))

		except Exception as e:
			logging.error('Error with <post> of PreLaunchSignupHandler: -- {}'.format(e))
			message = _('Sorry, we are having troubles saving the email to our servers at this time. Please try again later.')
			self.add_message(message, 'error')
			return self.get()
		
		
	@webapp2.cached_property
	def form(self):
		return forms.PreRegisterForm(self)


class PreLaunchAboutHandler(BaseHandler):
	def get(self):
		try:
			params = {
					'form': self.form,
					}
			self.render_template('/prelaunch/preRegisterAbout.html', **params)
		except:
			logging.error('Error during PreLaunchAboutHandler')

	@webapp2.cached_property
	def form(self):
		return forms.RegisterForm(self)

class PreLaunchJobsHandler(BaseHandler):
	def get(self):
		try:
			params = {
				'form': self.form,
					}
			self.render_template('/prelaunch/preRegisterJobs.html', **params)
		except:
			logging.error('Error during PreLaunchAboutHandler')

	@webapp2.cached_property
	def form(self):
		return forms.RegisterForm(self)

