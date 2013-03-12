#!/usr/bin/env python
# encoding: utf-8
"""
decorators.py

Created by Jason Elbourne on 2012-07-02.
Copyright (c) 2012 Jason Elbourne. All rights reserved.
"""

from models.oauth_models import OAuth_Token
import logging

def oauth_required(scope=None, realm='portal'):
	""" This is a decorator to be used with RequestHandler methods
		that accepts/requires OAuth to access a protected resource
		in accordance with Section 5 of the spec.
		
		If the token is valid, it's passed as a named parameter to 
		the request handler. The request handler is responsible for
		validating the user associated with the token. """
	def wrap(handler):
		def check_token(self, *args, **kwargs):     
			try:
				if self.request.headers.get('Authorization', '').startswith('OAuth'):
					token = self.request.headers['Authorization'].split(' ')[1]
				else:
					token = self.request.get('oauth_token', None)
				logging.debug("token = " + str(token))
				if not token:
					self.render_error(int(400), 'invalid_request(1)', 'Not a valid request for an OAuth protected resource, missing TOKEN')
					return
			except Exception, e:
				self.render_error(int(400), 'invalid_request(2)', 'Not a valid request for an OAuth protected resource, missing TOKEN - %s' % str(e))
				return
			token = OAuth_Token.get_by_access_token(token)
			if token:
				if token.is_expired():
					if token.refresh_token:
						self.render_error(int(400), 'expired_token', 'This token has expired, use refresh token to renew.')
						return
					else:
						self.render_error(int(400), 'invalid_token', 'This token is no longer valid')
						return
				
				if scope != token.scope:
					self.render_error(int(400), 'insufficient_scope', "This resource requires higher priveleges")
					return
			else:
				self.render_error(int(400), 'invalid_token', "This token sent is not a valid token")
				return
			
			return handler(self, token=token, *args, **kwargs)
		return check_token
	return wrap

