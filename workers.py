#!/usr/bin/env python
# encoding: utf-8
"""
workers.py

Created by Jason Elbourne on 2013-03-15.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

import webapp2
from worker import searchWorkers
from worker import parserWorkers
from worker import cartWorkers
from worker import tabWorkers
from worker import historyWorkers

app = webapp2.WSGIApplication([
    ('/worker/searchDocUpdate', searchWorkers.ProductSearchUpdateHandler),
    ('/worker/setProductTierPrices', parserWorkers.CreateProductTierPriceModel),
    ('/worker/checkCartSubtotals', cartWorkers.CheckCartSubtotalsWorker),
    ('/worker/checkTabSubtotals', tabWorkers.CheckTabSubtotalsWorker),
    ('/worker/createProductHistory', historyWorkers.CreateProductHistoryWorker)
], debug=True)
