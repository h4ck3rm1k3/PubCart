#!/usr/bin/env python
# encoding: utf-8
"""
livecounter.py

Created by Jason Elbourne on 2013-03-13.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

import webapp2
from lib.livecount import counter, counter_admin

app = webapp2.WSGIApplication([
	('/livecount/worker', counter.LivecountCounterWorker),
	('/livecount/writeback_all_counters', counter.WritebackAllCountersHandler),
	('/livecount/clear_entire_cache', counter.ClearEntireCacheHandler),
	('/livecount/counter_admin', counter_admin.CounterHandler),
], debug=True)
