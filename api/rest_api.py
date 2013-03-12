#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on Mar 23, 2012

@author: visser
'''

import webapp2
import logging
import re
import operator
import json

from google.appengine.ext.ndb import metadata
from google.appengine.ext import ndb

import parser
from models import records_models as model
from lib.decorators import oauth_required


METADATA_URI_NAME = 'resources'


class Authenticator(object):
    """Handles authentication of REST API calls."""

    def authenticate(self, dispatcher):
        """Authenticates the current request for the given dispatcher.
        Returns if authentication succeeds, otherwise raises a
        DispatcherException with an appropriate error code, e.g. 403 or 404
        (see the Dispatcher.forbidden() and Dispatcher.not_found() methods).
        Note, an error_code of None is handled specially by the Dispatcher
        (the response is not modified) so that, for example, the
        Authenticator could issue an HTTP authentication challenge by
        configuring the response appropriately and then throwing a
        DispatcherException with no code.

        Args:
          dispatcher: the dispatcher for the request to be authenticated
        """
        pass

class Authorizer(object):
    """Handles authorization for REST API calls.  In general, authorization
    failures in can_* methods should raise a DispatcherException with an
    appropriate error code while filter_* methods should simply remove any
    unauthorized data."""

    def can_read_metadata(self, dispatcher, model_name):
        """Returns if the metadata of the model with the given model_name is
        visible to the user associated with the current request for the given
        dispatcher, otherwise raises a DispatcherException with an
        appropriate error code (see the Dispatcher.forbidden() method).

        Args:
          dispatcher: the dispatcher for the request to be authorized
          model_name: the name of the model whose metadata has been requested
        """
        pass

    def filter_read_metadata(self, dispatcher, model_names):
        """Returns the model_names from the given list whose metadata is
        visible to the user associated with the current request for the given
        dispatcher.

        Args:
          dispatcher: the dispatcher for the request to be authorized
          model_names: the names of models whose metadata has been requested
        """
        return model_names

    def can_read(self, dispatcher, model):
        """Returns if the given model can be read by the user associated with
        the current request for the given dispatcher, otherwise raises a
        DispatcherException with an appropriate error code (see the
        Dispatcher.forbidden() method).

        Args:
          dispatcher: the dispatcher for the request to be authorized
          model: the model to be read
        """
        pass

    def filter_read(self, dispatcher, models):
        """Returns the models from the given list which can be read by the
        user associated with the current request for the given dispatcher.
        Note, the check_query() method can also be used to filter the models
        retrieved from a query.

        Args:
          dispatcher: the dispatcher for the request to be authorized
          models: the models to be read
        """
        return models

    def check_query(self, dispatcher, query_expr, query_params):
        """Verifies/modifies the given query so that it is valid for the user
        associated with the current request for the given dispatcher.  For
        instance, if every model has an 'owner' field, an implementation of
        this method could be:

            query_params.append(authenticated_user)
            if(not query_expr):
                query_expr = 'WHERE owner = :%d' % (len(query_params))
            else:
                query_expr += ' AND owner = :%d' % (len(query_params))
            return query_expr

        Args:
          dispatcher: the dispatcher for the request to be authorized
          query_expr: currently defined query expression, like 'WHERE foo = :1
                      AND blah = :2', or None for 'query all'
          query_params: the list of positional query parameters associated with
                        the given query_expr
        """
        return query_expr

    def can_write(self, dispatcher, model, is_replace):
        """Returns if the given model can be modified by the user associated
        with the current request for the given dispatcher, otherwise raises a
        DispatcherException with an appropriate error code (see the
        Dispatcher.forbidden() method).

        Args:
          dispatcher: the dispatcher for the request to be authorized
          model: the model to be modified
          is_replace: True if this is a full update (PUT), False otherwise
                      (POST)
        """
        pass

    def filter_write(self, dispatcher, models, is_replace):
        """Returns the models from the given list which can be modified by
        the user associated with the current request for the given
        dispatcher.

        Args:
          dispatcher: the dispatcher for the request to be authorized
          models: the models to be modified
          is_replace: True if this is a full update (PUT), False otherwise
                      (POST)
        """
        return models

    def can_write_blobinfo(self, dispatcher, model, property_name):
        """Returns if the a blob for the given property_name on the given
        model can be uploaded by the user associated with the current request
        for the given dispatcher, otherwise raises a DispatcherException with
        an appropriate error code (see the Dispatcher.forbidden() method).
        This call is a pre-check _before_ the blob is uploaded (there will be
        another, normal can_write() check after the upload succeeds).

        Args:
          dispatcher: the dispatcher for the request to be authorized
          model: the model to be (eventually) modified
          property_name: the name of the BlobInfo to be uploaded.
        """
        pass

    def can_delete(self, dispatcher, model_type, model_key):
        """Returns if the given model can be deleted by the user associated
        with the current request for the given dispatcher, otherwise raises a
        DispatcherException with an appropriate error code (see the
        Dispatcher.forbidden() method).

        Args:
          dispatcher: the dispatcher for the request to be authorized
          model_type: the class of the model to be be deleted
          model_key: the key of the model to be deleted
        """
        pass

    def check_delete_query(self, dispatcher, query_expr, query_params):
        """Verifies/modifies the given delete query so that it is valid for
        the user associated with the current request for the given
        dispatcher.  See check_query() for example usage.

        Args:
          dispatcher: the dispatcher for the request to be authorized
          query_expr: currently defined delete query expression, like
                      'WHERE foo = :1 AND blah = :2', or None for 'query all'
          query_params: the list of positional query parameters associated with
                        the given query_expr
        """
        return query_expr

class Rest(webapp2.RequestHandler):
    '''
    This class provides a RESTful API from which we can
    completely control our data model. It should be self-documenting to
    a certain degree
    '''

    authenticator = Authenticator()
    authorizer = Authorizer()


    def render_error(self, http_error_code, error_type, error_description):
        self.error(int(http_error_code))
        self.response.headers['content-type'] = 'application/json'
        self.response.out.write(json.dumps(
            {'error': error_type, 'error_description': error_description,})) 

    def _create_if_necessary(self, cls, currentEntity):
        default_properties = self.request.get('default');
        if not currentEntity and default_properties:
            #If the policy is to create an object if it doesn't already exist,
            #we should do that here
            initialValues = json.loads(default_properties)
            brandNewObj = cls(**initialValues)
            bnoKey = brandNewObj.put()
            if self.request.get('load') != 'all':
                currentEntity = [bnoKey]
            else:
                currentEntity = [brandNewObj]
        return currentEntity;

    def _write_all_objects_of_type(self, model_type, list_props):
        '''This finds all objects of a given type and writes them as a response'''
        model_handler = getattr(model, model_type)
        model_query = parser.ModelQuery()
        model_query.parse(self, model_handler)
        if model_query.error:
            self.render_error(model_query.error_code, model_query.error, model_query.error_description)
        else:
            model_query.query_expr = self.authorizer.check_query(
                self, model_query.query_expr, model_query.query_params)

            models = model_query.perform_filter(self, model_handler, model_query)

            if model_query.fetch_cursor:
                list_props[parser.QUERY_CURSOR_PARAM] = model_query.fetch_cursor
                models.append(list_props)

            models = self.authorizer.filter_read(self, models)
            
            #Write JSON back to the client
            self.response.headers['Content-Type'] = "application/json"
            self.response.write(parser.get_json_string(models))
        
    def _write_object_with_encodedkey(self, encoded_key, property_name=None):
        '''
        Writes an entity back to the client based on id. The value written will
        always be in JSON format. All filters will be ignored. It will by default 
        perform a load of all properties. Why else would you call this?
        '''
        #Simply get the object using NDB's class methods
        try:
            key = ndb.Key(urlsafe=encoded_key)
            obj_result = key.get()
            #We need to make these objects return arrays too
            objectString = parser.get_json_string(obj_result, property_name)
                
            #Return the values in the entity dictionary
            self.response.headers['Content-Type'] = "application/json"
            self.response.write(objectString)
        except Exception, e:
            self.render_error(int(400), 'key_error', "The Key supplied in the URI was not valid - " + str(e))
            return

    def _get_resources(self):
        try:
            #We need to make these objects return arrays too
            meta = parser.GetMetaData()
            objectString = meta.get_resources_json_string()
            #Return the values in the entity dictionary
            self.response.headers['Content-Type'] = "application/json"
            self.response.write(objectString)
        except Exception, e:
            self.render_error(int(400), 'key_error', "The Key supplied in the URI was not valid - " + str(e))
            return

    def get(self):
        '''Handles any and all 'get' requests'''

        objectType = None
        encodedKey = None
        propertyName = None

        path = self.request.path_info
        path = path.split('/')
        if (len(path) > 0):
            # Remove initial space at beginning of path_info from request
            ###########
            del path[0]
            ###########
        if (len(path) > 0):
            api_name = path.pop(0)
            if not api_name == 'api':
                self.render_error(int(400), 'uri_error', "Path info must start with /api")
                return
        if (len(path) > 0):
            api_version = path.pop(0)
            if not api_version:
                self.render_error(int(400), 'uri_error', "Api Version must be included in URI")
                return
        if (len(path) > 0):
            objectType = path.pop(0)
        if (len(path) > 0):
            encodedKey = path.pop(0) 
        if (len(path) > 0):
            propertyName = path.pop(0) 


        if objectType:
            if str(objectType) == str(METADATA_URI_NAME):
                self._get_resources()
            #If no ID, then we will return all objects of this type
            elif encodedKey:
                self._write_object_with_encodedkey(str(encodedKey), propertyName)
            else:
                list_props = {}
                self._write_all_objects_of_type(objectType, list_props)
        else:
            self.render_error(int(400), 'URI_error', "Missing required Entity name in URI for a GET request")
            return 

    @oauth_required(scope='write', realm='portal')
    def post(self, token):
        '''Handles POST requests'''

        if self.request.content_type == 'application/json':
            match = re.match(r'^/api/v1$',
                         self.request.path_info)
            if not match:
                self.render_error(int(400), 'method_error', 'The only supported POST url is: "/api"')
                return
            client_id = token.client_id
            #Simple: Load the JSON values that were sent to the server
            newObj = parser.put_model_obj(self.request.body, client_id)
            if isinstance(newObj, dict):
                try:
                    self.render_error(int(400), newObj['error'], newObj['error_description'])
                    return
                except:
                   self.render_error(int(400), 'api_error', 'Invalid Error message for post object')
                   return
            if not newObj:
                self.render_error(int(400), 'json_error', "The JSON supplied in your POST request was not valid")
                return

        else: 
            self.render_error(int(400), 'invalid_content_type', "All data must be posted using JSON.")
            return 
                
        #Write back the id of the new object
        self.response.write(str(newObj.key.urlsafe())) 

    def delete(self):
        '''Deletes an entity as specified'''
        logging.getLogger().warn(self.request.path_info)
        match = re.match(r'^/api/v1(?:/(?P<entity>\w+)(?:/(?P<encoded_key>\S+))?)?$',
                         self.request.path_info)
        if match:
            object_type = match.group('entity') 
            encodedKey = match.group('encoded_key')
            if object_type:
                property_to_delete = self.request.get('propogate')
                delete_props = property_to_delete.split(',') if property_to_delete else []
                if encodedKey:
                    deleteObjKey = ndb.Key(urlsafe=encodedKey)
                    returned_obj = deleteObjKey.get()
                    logging.getLogger().warn('Attempting to delete: %s, with key: %s and got this: %s' %(object_type, encodedKey, returned_obj))
                    for prop in delete_props:
                        res = getattr(returned_obj,prop)
                        if res:
                            res.delete()
                    deleteObjKey.delete()
                else:
                    self.render_error(int(400), 'URL_parsing_error', "MUST include Entity KEY to use the DELETE method")
                    return
            else:
                self.render_error(int(400), 'URL_parsing_error', "MUST include Entity Name to use the DELETE method")
                return
        else:
            self.render_error(int(400), 'URL_parsing_error', "Error when parsing URL - invalid syntax: %s" % (self.request.path_info,))
            return 

    def get_resources(self):
        pass