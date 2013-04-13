#!/usr/bin/env python
# encoding: utf-8
"""
bestPrice.py

Created by Jason Elbourne on 2013-01-11.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
import logging

from google.appengine.ext import ndb

from models import shoppingModels


def getBestPrice(urlsafeProductKey, quantity=1, returnProductModel=False):

    productModel = None
    productTierPrice = None
    current_BestPrice = None
    new_best_price = None
    current_PaidOrders = None
    potential_Quantity = int(quantity)

    ########################################################################
    #################
    ########   STEP 1
    ########   Check if we have a ProductModel existing as well as any existing order Paid
    #################
    ########################################################################
    try:
        ## Try to find the part in the Datastore.
        productKey = ndb.Key(urlsafe=urlsafeProductKey)
        productModel = productKey.get()
        if not productModel:
            raise Exception('urlsafeProductKey provided as argument did not return a productModel')
    except Exception as e:
        logging.error('Error in attempt to get Product : --  %s' % str(e))
        return None

    try:
        linkKey = ndb.Key(urlsafe='ag9kZXZ-cHViY2FydC1odWJyLgsSBFVzZXIYMQwLEgRDYXJ0IghFTEVQSEFOVAwLEgVPcmRlciIHVEw0OTRDRAw')
        logging.info('productModel Key: {}'.format(productModel.key))
        logging.info('link Key: {}'.format(linkKey))
        current_BestPrice = float(productModel.bup)/100  # Best Unit price in Cents then converted to Floating Point Number (1 Unit)
        current_PaidOrders = shoppingModels.Order.get_paid_qnt(productKey)

        if current_BestPrice:
            logging.info('Current Best Price = %s ' % str(current_BestPrice))
            if current_PaidOrders:
                logging.info('Current Paid Orders QNT = %s ' % str(current_PaidOrders))
                if int(current_PaidOrders) > 1:
                    potential_Quantity = int(current_PaidOrders) + int(quantity)

            ########################################################################
            #################
            ########   STEP 2
            ########   Check if this potential Quantity's Tier Price is better than the Curretn Best Price
            #################
            ########################################################################
            try:
                ##: Run this check her to make sure we have setup a priceModel for thei Product
                if str(productModel.pn):
                    logging.info('About to run function get_price_for_qnt')
                    productTierPrice, tier_cents_price = shoppingModels.ProductTierPrice.get_price_for_qnt(urlsafeProductKey, int(potential_Quantity))
                    logging.info('ProductTierPrice = %s ' % str(productTierPrice))
                else:
                    raise Exception('productModel does not have a valid property pn')
            except Exception as e:
                raise Exception('Problems with function get_price_for_qnt for ProductTierPrice model when calling from function getBestPrice: -- {}'.format(e))

            ##:  We need a copy of the current_BestPrice so we can modify a new_BestPrice and then compare the two variables
            new_best_price = current_BestPrice  # current_BestPrice is a Floating Point Number as we converted to it from the productModel.bup
            logging.info('new_best_price assigned value = %s ' % str(new_best_price))
            if int(potential_Quantity) > int(1):
                logging.info('potential_Quantity is > 1, so we use the info found in the productTierPrice for the Tier QNT')
                if productTierPrice and tier_cents_price:
                    logging.info('Updating new_best_price')
                    new_best_price = float(tier_cents_price)/100
                    if float(new_best_price) > float(current_BestPrice):
                        new_best_price = float(current_BestPrice)
            if returnProductModel:
                return productModel, new_best_price
            else:
                return new_best_price  # New Best Price is a Floating Point Number as we get from the ProductTierPrice function get_price_for_qnt
        else:
            raise Exception('Could not determine a current_BestPrice for productModel')
    except Exception as e:
        logging.error('Error in attempt to get Product and Best Price with function .getBestPrice() : --  %s' % str(e))
        if returnProductModel:
            return None, None
        else:
            return None
