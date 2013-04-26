#!/usr/bin/env python
# encoding: utf-8
"""
userModels.py

Created by Jason Elbourne on 2013-02-14.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import logging

from google.appengine.ext import ndb
from webapp2_extras.appengine.auth.models import User

class User(User):
    """
    Universal user model. Can be used with App Engine's default users API,
    own auth or third party authentication methods (OpenID, OAuth etc).
    based on https://gist.github.com/kylefinley
    """

    #: Creation date.
    created = ndb.DateTimeProperty(auto_now_add=True)
    #: Modification date.
    updated = ndb.DateTimeProperty(auto_now=True)
    #: User defined unique name, also used as key_name.
    # Not used by OpenID
    username = ndb.StringProperty()
    #: User Full Name
    name = ndb.StringProperty()
    #: User email
    email = ndb.StringProperty()
    #: Paypal Email
    paypal_email = ndb.StringProperty(default=None, indexed=False)
    #: Hashed password. Only set for own authentication.
    # Not required because third party authentication
    # doesn't use password.
    password = ndb.StringProperty()
    #: User Country
    country = ndb.StringProperty()
    #: Account activation verifies email
    activated = ndb.BooleanProperty(default=False)
    
    @classmethod
    def get_by_email(cls, email):
        """Returns a user object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A user object.
        """
        return cls.query(cls.email == email).get()

    @classmethod
    def create_resend_token(cls, user_id):
        entity = cls.token_model.create(user_id, 'resend-activation-mail')
        return entity.token

    @classmethod
    def validate_resend_token(cls, user_id, token):
        return cls.validate_token(user_id, 'resend-activation-mail', token)

    @classmethod
    def delete_resend_token(cls, user_id, token):
        cls.token_model.get_key(user_id, 'resend-activation-mail', token).delete()

    def get_social_providers_names(self):
        social_user_objects = SocialUser.get_by_user(self.key)
        result = []
#        import logging
        for social_user_object in social_user_objects:
#            logging.error(social_user_object.extra_data['screen_name'])
            result.append(social_user_object.provider)
        return result

    def get_social_providers_info(self):
        providers = self.get_social_providers_names()
        result = {'used': [], 'unused': []}
        for k,v in SocialUser.PROVIDERS_INFO.items():
            if k in providers:
                result['used'].append(v)
            else:
                result['unused'].append(v)
        return result


class LogVisit(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    uastring = ndb.StringProperty()
    ip = ndb.StringProperty()
    timestamp = ndb.StringProperty()


class LogEmail(ndb.Model):
    sender = ndb.StringProperty(
        required=True)
    to = ndb.StringProperty(
        required=True)
    subject = ndb.StringProperty(
        required=True)
    body = ndb.TextProperty()
    when = ndb.DateTimeProperty()


class EmailLeads(ndb.Model):
    email = ndb.StringProperty(required=True)
    notified = ndb.BooleanProperty(default=False)
    ip = ndb.StringProperty(required=True, indexed=False)


class Address(ndb.Model):
    uk = ndb.KeyProperty(kind=User) ##: User Model Key
    adn = ndb.StringProperty(required=True, indexed=False) ##: Address Name

    n = ndb.StringProperty(required=True, indexed=False) ##: Name
    ad = ndb.StringProperty(required=True, indexed=False) ##: Address1
    c = ndb.StringProperty(required=True) ##: City
    s = ndb.StringProperty(required=True) ##: State/Province
    con = ndb.StringProperty(required=True) ##: Country
    z = ndb.StringProperty(required=True, indexed=False) ##: Zip Code / Postal Code
    pn = ndb.IntegerProperty(required=True, indexed=False) ##: Phone Number
    
    is_default = ndb.BooleanProperty(default=True)
    
    cd = ndb.DateTimeProperty(auto_now_add=True, verbose_name='created_datetime')
    ud = ndb.DateTimeProperty(auto_now=True, verbose_name='updated_datetime')

    @classmethod
    def get_for_UserKey(cls, userKey, quantity):
        return cls.query(ancestor=userKey).fetch(quantity)
    
    @staticmethod
    def create_address(params, put_model=True):
        try:
            addressModel = Address()
            addressModel.populate(**params)
            if put_model:
                addressKey = addressModel.put()
            return addressModel
        except Exception as e:
            logging.error('Error while creating addressModel: {}'.format(e))
            return None
            
        


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