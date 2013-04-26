#!/usr/bin/env python
# encoding: utf-8
"""
widgetHandlers.py

Created by Jason Elbourne on 2013-04-19.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:  Python Imports
import logging

##:  Google Imports
from google.appengine.ext import ndb

##:  BournEE Imports
from lib.bourneehandler import BournEEHandler
#from models import shoppingModels


class CartWidgetHandler(BournEEHandler):
    def get(self):
        template = self.create_html()
        logging.info(template)  
        data = "{'html': '%s' }" % template
        if self.request.get('callback'):
            data = "%s (%s)" % (self.request.get('callback'), data)
            logging.info(data)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(data)

    def create_html(self):
        cartKey = ndb.Key(urlsafe=self.request.get('ck'))
        cart = cartKey.get()
        #productOrders = shoppingModels.Order.get_for_parentKey(cart.key)

        template = '<div class="pubCart-content-wrapper"><div class="span2">'

        if cart.img:
            template += '<img class="img-rounded" src="{}" width="170px" alt="{{cart.n}}">'.format(cart.img)
        else:
            template += '<img class="img-rounded" data-src="holder.js/170x170/text:PubCart." alt="{{cart.n}}">'

        template += '<iframe></iframe>'

        if cart.owner:
            template += '<div class="cartInfoWrapper"><div class="cartInfoTitle">Cart creator:</div><div class="cartInfo">{}</div></div>'.format(cart.owner)

        if cart.cat:
            template += '<div class="cartInfoWrapper"><div class="cartInfoTitle">Category:</div><div class="cartInfo">{}</div></div>'.format(cart.cat)
        if cart.ud:
            template += '<div class="cartInfoWrapper"><div class="cartInfoTitle">Updated on:</div><div class="cartInfo">{}</div></div>'.format(cart.ud)
        template += '</div></div>'
        return template
