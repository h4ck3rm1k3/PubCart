#!/usr/bin/env python
# encoding: utf-8
"""
tabHandlers.py

Created by Jason Elbourne on 2013-04-02.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:  Python Imports
import logging

##:  Webapp2 Imports
import webapp2
from webapp2_extras.i18n import gettext as _
from webapp2_extras.security import check_password_hash

##:  Google Imports
from google.appengine.ext import ndb

##:  BournEE Imports
import forms as forms
from models import shoppingModels, userModels
from lib import bestPrice, utils
from lib.bourneehandler import BournEEHandler, user_required


class PaidTabsRequestHandler(BournEEHandler):
    @user_required
    def get(self):
        pass


class ViewTabRequestHandler(BournEEHandler):
    @user_required
    def get(self, urlsafeTabKey):
        message = None
        try:
            ##: Make Sure if the cart is Private the owner (userKey) is viewing it.
            tabKey = ndb.Key(urlsafe=urlsafeTabKey)
            tab = tabKey.get()
            if not tab:
                raise Exception('No Tab Found')
            if self.user_key:
                if tab.uk != self.user_key:
                    message = _('You do not apear to be the owner of the Tab your are trying to view.')
                    raise Exception('Not the owner of the Tab! user: {}'.format(self.user_key))
            else:
                raise Exception('Error getting user info.')

            self.do_work(tab)

        except Exception as e:
            logging.error('Error in handler <get> of class - ViewTabRequestHandler : -- {}'.format(e))
            if not message:
                message = _('We are having difficulties displaying the Full Tab Page. Please try again later.')
            self.add_message(message, 'error')
            try:
                self.redirect(self.request.referer)
            except:
                self.redirect_to('home')

    def do_work(self, tab):
        try:
            tabOrders = shoppingModels.Order.get_for_parentKey(tab.key)

            defaultAddress = userModels.Address.query(
                userModels.Address.is_default == True,
                ancestor=self.user_key
            ).get()

            ########################################################################
            ##: This is the analytics counter for an idividual carts
            ########################################################################

            try:
                counter.load_and_increment_counter(name=tab.key.urlsafe(), namespace="unPaidTabView")
            except Exception as e:
                logging.error('Error setting LiveCount for tab view in class ViewTabRequestHandler : %s' % e)

            params = {
                "tabOrders": tabOrders,
                "urlsafeTabKey": tab.key.urlsafe(),
                "tab": tab,
                "address": defaultAddress,
            }

            self.bournee_template('fullTab.html', **params)

        except Exception as e:
            logging.error('Error in handler <do_work> in class - ViewTabRequestHandler : -- {}'.format(e))
            message = _('We are having difficulties displaying the Full Tab Page. Please try again later.')
            self.add_message(message, 'error')
            try:
                self.redirect(self.request.referer)
            except:
                self.redirect_to('home')


class AddToTabHandler(BournEEHandler):
    @user_required
    def post(self):
        try:
            message = None

            if not self.addToTab_form.validate():
                message = _('The submitted form was not valid.')
                raise Exception('addToTab_form did not Validate, in function \
                                POST of AddToTabHandler')

            logging.info("addToTab_form Form Was valid")

            order = None
            old_order_subtotal = 0

            ##: Try to fetch the data from the Form responce
            urlsafeProductKey = str(self.addToTab_form.pk.data).strip()
            urlsafeUserKey = str(self.addToTab_form.uk.data).strip()
            raw_password = str(self.addToTab_form.p.data).strip()
            turn_password_check_off = self.addToTab_form.p_off.data
            qnt = 1  # This is a placeholder for future quntity input on request

            password = utils.hashing(raw_password, self.app.config.get('salt'))
            valid_pass = check_password_hash(password, self.user_info.password)
            if not valid_pass:
                message = _('The password you supplied was not valid.')
                raise Exception('Password Supplied did not match session users password')

            ##: Set the flag on the user model to not require password security
            if turn_password_check_off:
                pass

            ##: Must have both urlsafeUserKey and urlsafeProductKey
            if not urlsafeUserKey or not urlsafeProductKey:
                logging.error("Error, Missing urlsafeUserKey or urlsafeProductKey")

            ##: Try to find the part in the Datastore and get Best Price.
            productModel, orderPrice = bestPrice.getBestPrice(urlsafeProductKey, int(qnt), returnProductModel=True)

            if productModel:
                ##: Initialize a variable for orderPrice with the part's current Best Unit Price
                if not orderPrice:
                    orderPrice = int(productModel.bup)
                else:
                    orderPrice = int(orderPrice*100)

                ##: Get or create the Cart
                tab = shoppingModels.Tab.get_or_create_tab(self.user_key)
                if not tab:
                    raise Exception('No Tab returned, error creating Tab, in function POST of AddToTabHandler')

                ##: Check to see if user already created this Order within this Cart
                currentOrder = shoppingModels.Order.get_for_product_and_parent(tab.key, str(productModel.pn))

                ##: Create or Update the Order Model
                if currentOrder:
                    old_order_subtotal = currentOrder.st  # must record the old subTotal before updating the QNT
                    order = currentOrder.update_order_add_qnt(currentOrder, int(qnt), put_model=False)
                else:
                    order = shoppingModels.Order.create_order(tab.key, productModel.key, int(qnt), put_model=False)

                ##: Update the Cart for the Totals Costs
                if order:
                    ##: Update the Tab's subtotals
                    orderSubTotal = (int(order.st)-int(old_order_subtotal))
                    oldTabSubTotal = tab.st
                    newTabSubTotal = int(oldTabSubTotal) + int(orderSubTotal)
                    if int(newTabSubTotal) < 0:
                        newTabSubTotal = orderSubTotal
                    shoppingModels.Tab.update_subtotal_values(tab, newTabSubTotal, oldTabSubTotal, put_model=False)

                ndb.put_multi([tab, order])

                message = _('Product number, {}, has been added onto your tab at a quantity of {}'.format(str(productModel.pn), str(qnt)))
                self.add_message(message, 'success')
            else:
                raise Exception('No productModel found, error creating Tab/Order Item, in function POST of AddToTabHandler')

        except Exception as e:
            logging.error('Error in function POST of AddToTabHandler : --   %s' % e)
            if not message:
                message = _('We are having difficulties with finalizing the Tab Submission. Please try again later.')
            self.add_message(message, 'error')

        finally:
            logging.info('Finished now Redirect to Referrer')
            try:
                self.redirect(self.request.referer)
            except:
                self.redirect_to('home')

    @webapp2.cached_property
    def addToTab_form(self):
        return forms.AddToTabForm(self)


class AddCartToTabHandler(BournEEHandler):
    @user_required
    def post(self):
        try:
            if not self.addCartToTab_form.validate():
                raise Exception('addCartToTab_form did not Validate, in function \
                                POST of AddToTabHandler')

            logging.info("addCartToTab_form Form Was valid")

            ordersSubtotal = 0
            entitiesToPut = []
            oldTabSubTotal = 0
            newTabSubTotal = 0

            ##: Try to fetch the data from the Form responce
            urlsafeCartKey = str(self.addCartToTab_form.ck.data).strip()
            raw_password = str(self.addToTab_form.p.data).strip()
            turn_password_check_off = self.addToTab_form.p_off.data

            password = utils.hashing(raw_password, self.app.config.get('salt'))

            if self.user_info.password != password:
                message = _('The password you supplied was not valid.')
                raise Exception('Password Supplied did not match session users password')

            ##: Set the flag on the user model to not require password security
            if turn_password_check_off:
                pass

            ##: Must have both urlsafeUserKey and urlsafeProductKey
            if not urlsafeCartKey:
                logging.error("Error, Missing urlsafeCartKey")

            cartModel = ndb.Key(urlsafe=urlsafeCartKey).get()

            if cartModel:
                logging.info("Found a cartModel")

                ##: Get or create the Cart
                tab = shoppingModels.Tab.get_or_create_tab(self.user_key)
                if not tab:
                    logging.info("Did not Find a Tab")
                    raise Exception('No Tab returned, error creating Tab, in function POST of AddToTabHandler')

                ##: Now we run thru all the orders in the cart and clone them to have the tab as parent.
                orderItems = shoppingModels.Order.get_for_parentKey(cartModel.key)
                if orderItems:
                    for orderItem in orderItems:
                        keyname = orderItem.key.id()
                        tabOrder = ndb.Key(shoppingModels.Order, keyname, parent=tab.key).get()
                        if tabOrder:
                            tabOrder.q += orderItem.q
                        else:
                            tabOrder = utils.clone_entity(orderItem)
                            tabOrder.key = ndb.Key(shoppingModels.Order, keyname, parent=tab.key)
                        entitiesToPut.append(tabOrder)
                        ordersSubtotal += orderItem.st

                    ##: Update the Cart's subtotals
                    oldTabSubTotal = tab.st
                    newTabSubTotal = int(oldTabSubTotal) + int(ordersSubtotal)
                    if int(newTabSubTotal) < 0:
                        newTabSubTotal = ordersSubtotal
                    shoppingModels.Tab.update_subtotal_values(tab, newTabSubTotal, oldTabSubTotal, put_model=False)

                    entitiesToPut.append(tab)

                    if len(entitiesToPut) > 1:
                        ndb.put_multi(entitiesToPut)
                    elif len(entitiesToPut) == 1:
                        entitiesToPut[0].put()

                    message = _('The cart {}, has been added onto your tab.'.format(str(cartModel.n)))
                    self.add_message(message, 'success')

                else:
                    logging.error("Could not find any orders to go with the submitted cart")
                    message = _('We are having difficulties with the order items in this cart. We did not add them to your Tab. Please try again later.')
                    self.add_message(message, 'error')

            else:
                raise Exception('No cartModel found, error adding Cart to Tab, in function POST of AddCartToTabHandler')

        except Exception as e:
            logging.error('Error in function POST of AddCartToTabHandler : --   %s' % e)
            if not message:
                message = _('We are having difficulties adding this Cart to the Tab. Please try again later.')
            self.add_message(message, 'error')

        finally:
            logging.info('Finished now Redirect to Referrer')
            try:
                self.redirect(self.request.referer)
            except:
                self.redirect_to('home')

    @webapp2.cached_property
    def addCartToTab_form(self):
        return forms.AddCartToTabForm(self)
