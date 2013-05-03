#!/usr/bin/env python
# encoding: utf-8
"""
userModels.py

Created by Jason Elbourne on 2013-02-14.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import logging

from lib import utils
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
    def get_by_email(self, email):
        """Returns a user object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A user object.
        """
        return self.query(self.email == email).get()

    def create_resend_token(self, user_id):
        entity = self.token_model.create(user_id, 'resend-activation-mail')
        return entity.token

    def validate_resend_token(self, user_id, token):
        return self.validate_token(user_id, 'resend-activation-mail', token)

    def delete_resend_token(self, user_id, token):
        self.token_model.get_key(user_id, 'resend-activation-mail', token).delete()


class History(ndb.Model):
    ob = ndb.KeyProperty()  # Object viewed (ie: Product, Cart) (key)
    uag = ndb.StringProperty(repeated=True)  # User Agent
    ip = ndb.StringProperty(repeated=True)  # User's IP
    ts = ndb.DateTimeProperty(auto_now=True, verbose_name='timestamp')  # Timestamp

    @classmethod
    def get_events_for_user(self, userKey, quantity=25):
        try:
            return self.query(ancestor=userKey).order(-History.ts).fetch(quantity)
        except Exception as e:
            logging.error('Error while getting History event: {}'.format(e))
            return None

    @staticmethod
    def get_event(userKey, objectKey):
        try:
            eventKey = ndb.Key(History, objectKey.urlsafe(), parent=userKey)
            return eventKey.get()
        except Exception as e:
            logging.error('Error while getting History event: {}'.format(e))
            return None

    @classmethod
    def get_sorted_history(self, userKey, quantity=25):
        try:
            events = self.get_events_for_user(userKey, quantity)
            if events:
                productHistory = []
                cartHistory = []
                productKeys = []
                cartKeys = []
                for event in events:
                    if event.ob.kind() == 'Product':
                        productKeys.append(event.ob)
                    else:
                        cartKeys.append(event.ob)

                if len(productKeys) > 1:
                    productHistory = ndb.get_multi(productKeys)
                elif len(productKeys) == 1:
                    productHistory.append(productKeys[0].get())

                if len(cartKeys) > 1:
                    cartHistory = ndb.get_multi(cartKeys)
                elif len(cartKeys) == 1:
                    cartHistory.append(cartKeys[0].get())

                return productHistory, cartHistory
            return None, None
        except Exception as e:
            logging.error('Error while getting History: {}'.format(e))
            return None, None

    @classmethod
    def create_event(self, userKey, objectKey, ip, userAgent, put_model=True):
        try:
            event = self.get_event(userKey, objectKey)
            if event:
                if userAgent not in event.uag:
                    uagl = event.uag
                    uagl.append(userAgent)
                    event.uag = uagl  # User Agent
                if ip not in event.ip:
                    ipl = event.uag
                    ipl.append(ip)
                    event.ip = ipl  # User Agent
            else:
                event = self()
                event.key = ndb.Key(History, objectKey.urlsafe(), parent=userKey)
                event.ob = objectKey  # Object viewed (ie: Product, Cart) (key)
                event.uag = [userAgent]  # User Agent
                event.ip = [ip]  # User's IP
            if put_model:
                eventKey = event.put()
                if not eventKey:
                    raise Exception('Error when atempting to put event model.')
            return event
        except Exception as e:
            logging.error('Error while creating History event: {}'.format(e))
            return None


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