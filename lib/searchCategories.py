#!/usr/bin/env python
# encoding: utf-8
"""
searchCategories.py

Created by Jason Elbourne on 2013-03-07.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""

from google.appengine.api import search


electronics = {'name': 'electronics', 'children': []}

ctree =	 {'name': 'root', 'children': [electronics]}

# [The core fields that all products share are: product id, name, description,
# category, category name, and price]
# Define the non-'core' (differing) product fields for each category
# above, and their types.
product_dict =	{'ELECTRONICS': {'p': search.TextField,  ##: Packaging
								'ot': search.TextField,  ##: Operating Temperature
								'mt': search.TextField,  ##: Mounting Type
								'pc': search.TextField,  ##: Package / Case
								'sdp': search.TextField, ##: Supplier Device Package
								},
				}