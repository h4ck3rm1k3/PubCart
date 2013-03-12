'''
Created on Mar 22, 2012

@author: visser
'''
import json
import logging
import re
import inspect
from models import records_models as model
from google.appengine.ext import ndb
from google.appengine.ext.ndb import metadata
from google.appengine.datastore.datastore_query import Cursor


CLASS_TYPE_STR = '__entity'
ID_STR = '__key'
REF_STR = '__ref'

WRITE_PROP_FUNC_NAME = '_write_properties_for_api'
READ_PROP_FUNC_NAME = '_read_properties_for_api'

MAX_FETCH_PAGE_SIZE = 1000
QUERY_CURSOR_PARAM = "cursor"
QUERY_PAGE_SIZE_PARAM = "page_size"
QUERY_ORDERING_PARAM = "ordering"
QUERY_TERM_PATTERN = re.compile(r"^(f.._)(.+)$")
QUERY_PREFIX = "WHERE "
QUERY_JOIN = " AND "
QUERY_ORDERBY = " ORDER BY "
QUERY_ORDER_SUFFIXES = [" ASC", " DESC"]
QUERY_ORDER_PREFIXES = ["", "-"]
QUERY_ORDER_ASC_IDX = 0
QUERY_ORDER_DSC_IDX = 1
QUERY_LIST_TYPE = "fin_"
QUERY_TYPE_PARAM = "type"
QUERY_TYPE_FULL = "full"
# deprecated value, (really means xml or json depending on headers, use
# "structured" instead)
QUERY_TYPE_XML = "xml"
QUERY_TYPE_STRUCTURED = "structured"

QUERY_BLOBINFO_PARAM = "blobinfo"
QUERY_BLOBINFO_TYPE_KEY = "key"
QUERY_BLOBINFO_TYPE_INFO = "info"

QUERY_CALLBACK_PARAM = "callback"

QUERY_INCLUDEPROPS_PARAM = "include_props"

EXTRA_QUERY_PARAMS = frozenset([QUERY_BLOBINFO_PARAM, QUERY_CALLBACK_PARAM,
                                QUERY_INCLUDEPROPS_PARAM])

QUERY_EXPRS = {
    "feq_": "%s = :%d",
    "flt_": "%s < :%d",
    "fgt_": "%s > :%d",
    "fle_": "%s <= :%d",
    "fge_": "%s >= :%d",
    "fne_": "%s != :%d",
    QUERY_LIST_TYPE: "%s IN :%d"}

def get_type_name(value_type):
    """Returns the name of the given type."""
    return value_type.__name__

def dict_from_key(key):
    return  {CLASS_TYPE_STR:key.kind(),ID_STR:key.id()}

def put_model_obj(json_string, client_id):
    '''
    Converts a string to the requisite Model object. Returns the object that
    was created from the string. NOTE that the objects (they may be nested) are
    all stored implicitly and there is no way to turn this off for now. The
    reason for this behavior is to make parsing these objects faster.
    '''
    portal_id = client_id
    list_of_objects = []
    def _hook_to_object(dct):
        '''
        This is the method that is called every time we are decoding a JSON
        object. The difference between key objects and regular objects is that
        key objects will have the __ref property set to true. If the __ref attribute
        is not present, we create brand new objects if the __key isn't set or overwrite
        if the __key IS set.
        '''
        try:
            logging.debug(dct)

            logging.getLogger().info('Evaluating: %s' % str(dct))

            #Retrieves the class type and Key which are special tags
            #WILL THROW KeyError if '__type' tag doesn't exist.
            #This is an ellegal state.
            clsType = dct[CLASS_TYPE_STR]
            #Using get() here means we won't get a KeyError (just None)
            encoded_key = dct.get(ID_STR)
            #We now support a more robust way of defining references in our
            #code. Any JSON object that contains __ref=true will be
            #evaluated as such.
            clsReference = dct.get(REF_STR)
        
            if clsReference:
                try:
                    return ndb.Key(urlsafe=encoded_key)
                except:
                    return{'error': 'key_error', 'error_description': "The Key supplied in the URI was not valid",}

            #Keys in JSON object that start with '__' are reserved.
            dictCopy = dict((key, value) for key, value in dct.iteritems() if not key.startswith('__'))

            try:
                if dictCopy.has_key('portal_id') and portal_id:
                    if portal_id != dictCopy['portal_id']:
                        list_of_objects.append({'error': 'oauth_error', 'error_description': 'Portal Id in POST data does not match OAuth Token Client'})
                        return

                #We verify is all model properties are included in the dictCopy
                model_cls = getattr(model, clsType)

                if hasattr(model_cls, WRITE_PROP_FUNC_NAME):
                    dict_keys = set(dictCopy.keys())
                    api_properties = set(getattr(model_cls, WRITE_PROP_FUNC_NAME)())
                    differences = len(dict_keys^api_properties)
                    if int(differences)>0:
                        list_of_objects.append({'error': 'property_error', 'error_description': 'Invalid Property Names were supplied to POST request.'})
                        return
                else:
                    logging.debug('Model Class has no - %s' % str(WRITE_PROP_FUNC_NAME))

            except Exception, e:
                list_of_objects.append({'error': 'api_error', 'error_description': "An Error occured with the API during you last request",})
                return


            # #If there is an __id property, we should set the key of the
            # #object too in the next line. This can only be set in the
            # #constructor
            # dictCopy['id'] = clsId

            #This line is slightly confusing. It will look up the desired
            #class in the list of global names and create an object with all
            #instance variables initialized using the dictionary values
            
            logging.getLogger().info('The objects are: %s' % str(dictCopy))
            
            try:                
                newObj = getattr(model, clsType)(**dictCopy)
                logging.getLogger().info('Done creating obj')

                #We are keeping track of all the objects we are implicitly
                #adding to the DB. This is the only way I could find to keep
                #track of the actual objects so that we could return objects
                #rather than keys; the nature of the recursive parsing will
                #guarantee that the last object appended to this list will 
                #be the root object
                list_of_objects.append(newObj)
                return newObj.put()
            except:
                #if the model class doesn't contain the relevant class
                list_of_objects.append({'error': 'syntax_error', 'error_description': 'We don\'t support class type: %s' % clsType})
                return
        except:
            #if the object dict doesn't contain the __type property
            list_of_objects.append({'error': 'syntax_error', 'error_description': 'The __type property isn\'t present'})
            return
    
    try:
        json.loads(json_string, object_hook=_hook_to_object)
    except:
        list_of_objects.append({'error': 'json_error', 'error_description': 'The JSON supplied in your POST request was not valid'})
        return
    #Return the last object in the list. This will be the root
    return list_of_objects[-1]

def get_json_string(objects, property_name=None):
    '''
    Uses a Model object KEY to retrieve the actual object and then return
    its string value.
    '''
    if property_name:
        obj = objects
        logging.debug("Property Name = " + str(property_name))
        if hasattr(obj, READ_PROP_FUNC_NAME):
            api_properties = set(getattr(obj, READ_PROP_FUNC_NAME)())
        else:
            logging.debug('Model Class has no - %s' % str(READ_PROP_FUNC_NAME))
            api_properties = obj.to_dict().keys()
        if property_name in api_properties:
            prop = getattr(obj, property_name)
            logging.debug("Property = " + str(prop))
            return json.dumps(prop)
    else:
        return json.dumps(objects, cls=_ExtendedJSONEncoder)
#
class ModelHandler(object):
    """Handler for a Model (or Expando) type which manages converting
    instances to and from xml."""

    def __init__(self, model_name, model_type):
        self.model_name = model_name
        self.model_type = model_type

class GetMetaData(object):


    def add_models_from_module(cls, model_module):
        """Adds all models from the given module to this request handler.
        The name of the Model class (with invalid characters converted to the
        '_' character) will be used as the REST path for Models of that type
        (optionally including the module name).

        REST paths which conflict with previously added paths will cause a
        KeyError.

        Args:

          model_module: a module instance or the name of a module instance
                        (e.g. use __name__ to add models from the current
                        module instance)
          use_module_name: True to include the name of the module as part of
                           the REST path for the Model, False to use the
                           Model name alone (this may be necessary if Models
                           with conflicting names are used from different
                           modules).
          exclude_model_types: optional list of Model types to be excluded
                               from the REST handler.
          model_methods: optional methods supported for the given model (one
                          or more of ['GET', 'POST', 'PUT',
                         'DELETE', 'GET_METADATA']), defaults to all methods

        """
        responce_dict = {}
        responce_dict['apiVersion'] = "v1"
        responce_dict['basePath'] = "https://api.TRUSTFnd.com/"
        
        api_list = []

        logging.info("adding models from module %s", model_module)

        if(isinstance(model_module, basestring)):
            model_module = __import__(model_module)
        for obj_name in dir(model_module):
            obj = getattr(model_module, obj_name)
            if(isinstance(obj, type) and issubclass(obj, ndb.Model)):
                model_name = get_type_name(obj)
                model_handlers = {}
                model_handlers['path'] = '/'+str(model_name)+'/{entity_key}/{optional_resource}'
                api_list.append(model_handlers)
        
        responce_dict['apis'] = api_list
        return responce_dict


    def get_resources_json_string(cls):
        entities = cls.add_models_from_module(model)
        logging.debug(entities)
        return entities


class _ExtendedJSONEncoder(json.JSONEncoder):
    '''Custom Encoder that can handle Model objects'''
    def default(self, obj):
        '''The method called first when encoding'''
        logging.getLogger().info(repr(obj))
        if isinstance(obj, ndb.Key):
            #When the instance is a Key, just include the type and id
            return {CLASS_TYPE_STR:obj.kind(), ID_STR:obj.urlsafe(), REF_STR:True}
        elif isinstance(obj, ndb.Model):
            #When we have a Model object, we simply grab all properties 
            properties = obj.to_dict()

            dictCopy = {CLASS_TYPE_STR:obj.key.kind(), ID_STR: obj.key.urlsafe()}

            if hasattr(obj, READ_PROP_FUNC_NAME):
                api_properties = set(getattr(obj, READ_PROP_FUNC_NAME)())
            else:
                logging.debug('Model Class has no - %s' % str(READ_PROP_FUNC_NAME))
                api_properties = properties.keys()

            for key,value in properties.iteritems():
                if key in api_properties:
                    #Ignore values that are null or are empty arrays
                    if value  or (isinstance(value, list) and len(value) > 0):
                        dictCopy[key] = value
            return dictCopy
        elif isinstance(obj, object):
            logging.getLogger().info('Interpreting: %s as an object',(obj,))
            return str(obj)
        
        #If we haven't yet found an exact match, use the default
        return json.JSONEncoder.default(self, obj)

class ModelQuery(object):
    """Utility class for holding parameters for a model query."""

    def __init__(self):
        self.fetch_page_size = MAX_FETCH_PAGE_SIZE
        self.fetch_cursor = None
        self.ordering = None
        self.order_type_idx = QUERY_ORDER_ASC_IDX
        self.query_expr = None
        self.query_params = []
        self.error = False
        self.error_description = None
        self.error_code = None

    def perform_filter(self, dispatcher, model_type, model_query):
        '''Performs a search for all items in a filter'''
        #=======================================================================
        # Create local variables for all the request variables
        #=======================================================================
        isLoadKeysOnly = dispatcher.request.get('load') != 'all'

        if(model_query.query_expr is None):
            logging.debug('Fetch with NO query_expr')
            query = model_type.query()
            if(model_query.ordering):
                query.order(QUERY_ORDER_PREFIXES[model_query.order_type_idx] +
                            model_query.ordering)
        else:
            logging.debug('Fetch with query_expr')
            if(model_query.ordering):
                model_query.query_expr += (
                    QUERY_ORDERBY + model_query.ordering +
                    QUERY_ORDER_SUFFIXES[model_query.order_type_idx])
            query = model_type.gql(model_query.query_expr,
                                        *model_query.query_params)

        if model_query.fetch_cursor:
            curs = Cursor(urlsafe=model_query.fetch_cursor)
            page_size = self.fetch_page_size
            models, curr, more = query.fetch_page(page_size, start_cursor=curs)
        else:
            models, curr, more = query.fetch_page(self.fetch_page_size)

        if more:
            model_query.fetch_cursor = curr.urlsafe()
        else:
            model_query.fetch_cursor = None

        return models


    def parse(self, dispatcher, model_handler):
        """Parses the current request into a query."""

        for arg in dispatcher.request.arguments():
            if(arg == QUERY_CURSOR_PARAM):
                try:
                    self.fetch_cursor=dispatcher.request.get(QUERY_CURSOR_PARAM)
                    continue
                except:
                    self.error_code = 400
                    self.error = 'invalid_cursor'
                    self.error_description = 'URI contains invalid cursor (%s)' % str(dispatcher.request.get(QUERY_CURSOR_PARAM))
                    break

            if(arg == QUERY_PAGE_SIZE_PARAM):
                try:
                    self.fetch_page_size=int(dispatcher.request.get(QUERY_PAGE_SIZE_PARAM))
                    continue
                except:
                    self.error_code = 400
                    self.error = 'invalid_page_size'
                    self.error_description = 'URI contains invalid page_size (%s)' % str(dispatcher.request.get(QUERY_PAGE_SIZE_PARAM))
                    break


            if(arg == QUERY_ORDERING_PARAM):
                ordering_field = dispatcher.request.get(QUERY_ORDERING_PARAM)
                if(ordering_field[0] == "-"):
                    ordering_field = ordering_field[1:]
                    self.order_type_idx = QUERY_ORDER_DSC_IDX

                self.ordering = ordering_field
                continue

            if(arg in EXTRA_QUERY_PARAMS):
                #ignore
                continue

            match = QUERY_TERM_PATTERN.match(arg)
            if(match is None):
                logging.warning("ignoring unexpected query param %s", arg)
                continue

            query_type = match.group(1)
            query_field = match.group(2)
            query_sub_expr = QUERY_EXPRS[query_type]

            # Check if query_field is with the _read_properties_for_api list
            if hasattr(model_handler, READ_PROP_FUNC_NAME):
                api_properties = set(getattr(model_handler, READ_PROP_FUNC_NAME)())
            else:
                logging.debug('Model Class has no - %s' % str(READ_PROP_FUNC_NAME))
                properties = model_handler.to_dict()
                api_properties = properties.keys()

            if not query_field in api_properties:
                self.error_code = 400
                self.error = 'URI_Query_Field_Error'
                self.error_description = 'Query Field Not Available (%s)' % query_field
                break

            query_values = dispatcher.request.get_all(arg)
            if(query_type == QUERY_LIST_TYPE):
                query_values = [v.split(",") for v in query_values]

            # query_field, query_values = model_handler.read_query_values(
            #     query_field, query_values)
            logging.debug(query_field)
            logging.debug(query_values)

            for value in query_values:
                self.query_params.append(value)
                query_sub_expr = query_sub_expr % (query_field,
                                                   len(self.query_params))
                if(not self.query_expr):
                    self.query_expr = QUERY_PREFIX + query_sub_expr
                else:
                    self.query_expr += QUERY_JOIN + query_sub_expr

        self.fetch_page_size = max(min(self.fetch_page_size,
                                       self.fetch_page_size,
                                       MAX_FETCH_PAGE_SIZE), 1)

