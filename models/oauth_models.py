from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb

import time
import hashlib
import random
import config
import logging

def now():
	return int(time.mktime(time.gmtime()))

def random_str():
	return hashlib.sha1(str(random.random())).hexdigest()

class OAuth_Token(ndb.Model):
	EXPIRY_TIME = 3600*24
	
	user_id			= ndb.StringProperty()
	client_id		= ndb.StringProperty()
	access_token	= ndb.StringProperty()
	token_type		= ndb.StringProperty(default='OAuth')
	refresh_token	= ndb.StringProperty(required=False)
	scope			= ndb.StringProperty(required=False)
	realm			= ndb.StringProperty(required=False)
	expires			= ndb.IntegerProperty(required=False)
	
	@classmethod
	def get_by_refresh_token(cls, refresh_token):
		return cls.query().filter(cls.refresh_token == refresh_token).get()
	
	@classmethod
	def get_by_access_token(cls, access_token):
		key = ndb.Key(OAuth_Token, str(access_token))
		return key.get()
	
	def put(self, can_refresh=True):
		if can_refresh:
			self.refresh_token	= random_str()
		self.access_token		= random_str()
		self.expires			= now() + self.EXPIRY_TIME
		key = ndb.Key(OAuth_Token, str(self.access_token))
		self.key	= key
		super(OAuth_Token, self).put()
	
	def refresh(self):
		if not self.refresh_token:
			return None # Raise exception?
			
		token = OAuth_Token(
			client_id	= self.client_id, 
			user_id		= self.user_id,
			scope		= self.scope, )
		token.put()
		self.delete()
		return token
	
	def is_expired(self):
		return self.expires < now()
	
	def serialize(self, requested_scope=None):
		token = dict(
			access_token		= self.access_token,
			expires_in			= self.expires - now(), )
		if (self.scope and not requested_scope) \
			or (requested_scope and self.scope != requested_scope):
			token['scope']		= self.scope
		if self.refresh_token:
			token['refresh_token'] = self.refresh_token
		return token


class OAuth_Authorization(ndb.Model):
	EXPIRY_TIME = 3600
	
	user_id			= ndb.StringProperty()
	client_id		= ndb.StringProperty()
	code			= ndb.StringProperty()
	redirect_uri	= ndb.StringProperty()
	expires			= ndb.IntegerProperty()
	
	@classmethod
	def get_by_code(cls, code):
		oa = OAuth_Authorization.query(OAuth_Authorization.code == code).get()
		logging.info(oa)
		return oa
	
	def put(cls):
		cls.code		= random_str()
		cls.expires	= now() + cls.EXPIRY_TIME
		super(OAuth_Authorization, cls).put()
	
	def delete(cls):
		cls.key.delete()

	def is_expired(cls):
		return cls.expires < now()
	
	def validate(cls, code, redirect_uri, client_id=None):
		valid = not cls.is_expired() \
				and cls.code == str(code) \
				and cls.redirect_uri == str(redirect_uri)

		if client_id:
			valid &= cls.client_id == client_id
		return valid
	
	def serialize(cls, state=None):
		authz = {'code': cls.code}
		if state:
			authz['state'] = state
		return authz



class OAuth_Client(ndb.Model):
	"""

	"""

	#: Client Id, also used as key_name.
	client_id		= ndb.StringProperty()
	#: Client Secret.
	client_secret	= ndb.StringProperty()
	#: Redirect URI.
	redirect_uri	= ndb.StringProperty()
	#: Creation date.
	created 		= ndb.DateTimeProperty(auto_now_add=True)
	#: Modification date.
	updated 		= ndb.DateTimeProperty(auto_now=True)
	#: Portal Name
	portal_name 	= ndb.StringProperty()


	@classmethod
	def get_all(cls):
		return cls.query().fetch()

	@classmethod
	def get_by_client_id(cls, client_id):
		return ndb.Key(OAuth_Client, str(client_id)).get()

	@classmethod
	def authenticate(cls, client_id, client_secret):
		client = cls.get_by_client_id(client_id)
		if client and client.client_secret == client_secret:
			return client
		else:
			return None

	@classmethod
	def verify_unique_client_id(cls, client_id):
		if ndb.Key(OAuth_Client, str(client_id)).get():
			return False
		return True

	def put(self):
		self.client_secret  = random_str()
		super(OAuth_Client, self).put()

