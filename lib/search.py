#!/usr/bin/env python
# encoding: utf-8
"""
search.py

Created by Jason Elbourne on 2013-03-07.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

from google.appengine.api import search


index = search.Index(name='shoppingSearch')

fields = [
	search.TextField(name=n, value = pid),
	search.TextField(name=PID, value = pid),
	search.TextField(name=PID, value = pid),
	search.TextField(name=PID, value = pid),
]
