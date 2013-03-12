#!/usr/bin/env python
# encoding: utf-8
"""
exceptions.py

Created by Jason Elbourne on 2013-01-18.
Copyright (c) 2013 Jason Elbourne. All rights reserved.
"""
class Error(Exception):
  """Base error type."""

  def __init__(self, error_message):
	self.error_message = error_message


class NotFoundError(Error):
  """Raised when necessary entities are missing."""


class OperationFailedError(Error):
  """Raised when necessary operation has failed."""

class FunctionException(Error):
	pass