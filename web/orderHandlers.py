#!/usr/bin/env python
# encoding: utf-8
"""
orderHandlers.py

Created by Jason Elbourne on 2013-02-21.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

##:  Python Imports
import logging

##:  Webapp2 Imports
import webapp2
from webapp2_extras.i18n import gettext as _

##:  Google Imports
from google.appengine.ext import ndb

##:  BournEE Imports
import forms as forms
from models import shoppingModels
from lib.bourneehandler import BournEEHandler, user_required


class ChangeQuantityOfOrderHandler(BournEEHandler):
    @user_required
    def post(self):
        try:
            if not self.chgQntOfOrder_form.validate():
                raise Exception('chgQntOfOrder_form did not Validate, in function POST of ChangeQuantityOfOrderHandler')

            oldOrderSubtotal = 0
            newOrderSubTotal = 0

            ##: Try to fetch the data from the Form responce
            urlsafeParentKey = str(self.chgQntOfOrder_form.park.data).strip()
            urlsafeOrderKey = str(self.chgQntOfOrder_form.ok.data).strip()
            quantity = self.chgQntOfOrder_form.qnt.data

            if urlsafeParentKey and urlsafeOrderKey:

                ##: Get the Cart to check ownership
                parentKey = ndb.Key(urlsafe=urlsafeParentKey)
                parent = parentKey.get()

                if parent:
                    if parent.uk == self.user_key:
                        order = ndb.Key(urlsafe=urlsafeOrderKey).get()  # Get from Datastore
                        if order:

                            ##: First Check if order quantity will be zero, meaning Delete
                            if int(quantity) <= int(0):
                                ##: We have a quantity of 0 so we are deleting the order
                                ##: Update the Parents's subtotals
                                orderSubTotal = order.st
                                oldParentSubTotal = parent.st
                                newParentSubTotal = int(oldParentSubTotal) - int(orderSubTotal)
                                if int(newParentSubTotal) < 0:
                                    newParentSubTotal = orderSubTotal

                                if parent.key.kind() == 'Cart':
                                    shoppingModels.Cart.update_subtotal_values(parent, newParentSubTotal, oldParentSubTotal)
                                elif parent.key.kind() == 'Tab':
                                    shoppingModels.Tab.update_subtotal_values(parent, newParentSubTotal, oldParentSubTotal)

                                productName = order.productName
                                order.key.delete()

                                logging.info("We have deleted the Order and we Redirect to referrer thru <finally:> block")
                                message = _('You entered a quantity of 0 for the %s Order, so it has been removed from the list.' % (str(productName)))
                                self.add_message(message, 'success')

                            ##: Else, this is simply a quantity update.
                            else:
                                ##: We have a proper quantity so we will just update everything
                                if int(order.q) == int(quantity):
                                    logging.info('The new Quantity is the same as the existing quantity, so we do nothing.')
                                    message = _('The new Quantity is the same as the existing quantity: %s' % (str(order.q)))
                                    self.add_message(message, 'info')
                                elif parent.key != order.key.parent():
                                    logging.error('The order being modified does not have a parent matching this Cart/Tab')
                                    message = _('Things were not matching up on our server so we did not modify the quantity' % (str(order.q)))
                                    self.add_message(message, 'error')
                                else:
                                    oldOrderSubtotal = int(order.st)
                                    order.update_order_new_qnt(order, quantity, put_model=False)
                                    newOrderSubTotal = int(order.st)

                                    if int(oldOrderSubtotal) != int(newOrderSubTotal):
                                        orderSubTotal = int(newOrderSubTotal) - int(oldOrderSubtotal)
                                        oldParentSubTotal = parent.st
                                        newParentSubTotal = int(oldParentSubTotal) - int(orderSubTotal)
                                        if int(newParentSubTotal) < 0:
                                            newParentSubTotal = orderSubTotal

                                        if parent.key.kind() == 'Cart':
                                            shoppingModels.Cart.update_subtotal_values(parent, newParentSubTotal, oldParentSubTotal)
                                        elif parent.key.kind() == 'Tab':
                                            logging.info('Here')
                                            shoppingModels.Tab.update_subtotal_values(parent, newParentSubTotal, oldParentSubTotal)

                                    ##: Now we save both the Tab (Parent) and the Order using put_multi()
                                    ndb.put_multi([parent, order])

                                    ##: All Done
                                    logging.info("We have updated the Order Quantity and we Redirect to referrer thru <finally:> block")
                                    message = _('We have updated the %s Order Quantity to: %s' % (str(order.productName), str(order.q)))
                                    self.add_message(message, 'success')
                        else:
                            ##: Missing Order
                            logging.error('Error - Order not found using given Order Key')
                            message = _('There was an Error during form submission updating your order. Please try again later')
                            self.add_message(message, 'error')
                    else:
                        logging.error("User Keys did not match between User and Cart/Tab Owner")
                        message = _('You do not appear to be the owner of this Cart. We can not complete request.')
                        self.add_message(message, 'error')
                else:
                    logging.error("Cart/Tab was not Found")
                    message = _('There was an Error during form Submission. We can not complete request. Please try again later')
                    self.add_message(message, 'error')
            else:
                logging.error("parentKey or OrderKey not received from the Form Submission")
                message = _('There was an Error during form Submission. We can not complete request. Please try again later')
                self.add_message(message, 'error')

        except Exception as e:
            logging.error("Error occurred running function POST of class ChangeQuantityOfOrderHandler: -- %s" % str(e))
            message = _('There was an Error during form Submission. We can not complete request. Please try again later')
            self.add_message(message, 'error')

        finally:
            try:
                self.redirect(self.request.referer)
            except:
                self.redirect_to('home')

    @webapp2.cached_property
    def chgQntOfOrder_form(self):
        return forms.ChangeQntOfOrderForm(self)
