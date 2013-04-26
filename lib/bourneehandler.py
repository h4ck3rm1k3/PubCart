
import re
import webapp2
import logging
import datetime
import forms as forms
from webapp2_extras.i18n import gettext as _

from google.appengine.ext import ndb
from google.appengine.api import memcache

from boilerplate.lib.basehandler import BaseHandler
from models import shoppingModels, userModels, categoryModels
from lib import paypal_settings as settings
from lib import paypal
from lib import utils


def user_required(handler):
    """
         Decorator for checking if there's a user associated
         with the current session.
         Will also fail if there's no session present.
    """

    def check_login(self, *args, **kwargs):
        """
            If handler has no login_url specified invoke a 403 error
        """
        try:
            auth = self.auth.get_user_by_session()
            if not auth:
                try:
                    self.auth_config['login_url'] = self.uri_for('softRegister', continue_url=self.request.path)
                    self.redirect(self.auth_config['login_url'], abort=True)
                except (AttributeError, KeyError), e:
                    self.abort(403)
            else:
                address = userModels.Address.query(userModels.Address.is_default == True, ancestor=self.user_key).get()
                if not address:
                    try:
                        message = _('Sorry, we dont have a default address for you yet. Could you please fill in this form.')
                        self.add_message(message, 'error')
                        self.redirect_to('addressRegister', uk=self.user_key.urlsafe())
                    except (AttributeError, KeyError), e:
                        pass

                return handler(self, *args, **kwargs)
        except AttributeError, e:
            # avoid AttributeError when the session was delete from the server
            logging.error(e)
            self.auth.unset_session()
            self.redirect_to('home')

    return check_login


class BournEEHandler(BaseHandler):
    """
        BaseHandler for all requests created by BournEE Exchange Code (not boilerplate code)
    """
    @webapp2.cached_property
    def usersTab(self):
        try:
            if self.user:
                ##: Get or create the Cart
                tab = shoppingModels.Tab.get_or_create_tab(self.user_key)
                if not tab:
                    raise Exception('No Tab returned, error creating Tab, in function POST of AddToTabHandler')
                return tab
            return None
        except Exception as e:
            logging.error("Error in function <cartInfo> within BournEEHandler : -- {}".format(e))
            return None

    @webapp2.cached_property
    def tabItems(self):
        try:
            if self.usersTab:
                ##: Get or create the Cart
                tabItems = shoppingModels.Order.get_for_parentKey(self.usersTab.key)
                return tabItems
            return None
        except Exception as e:
            logging.error("Error in function <cartInfo> within BournEEHandler : -- {}".format(e))
            return None

    @webapp2.cached_property
    def usersCartCount(self):
        try:
            if self.user:
                allCartsCount = shoppingModels.Cart.query(shoppingModels.Cart.garbage==False, ancestor=self.user_key).count()
                return allCartsCount
            return 0
        except Exception as e:
            logging.error("Error in function <cartInfo> within BournEEHandler : -- {}".format(e))
            return 0

    @webapp2.cached_property
    def userWatchlistCount(self):
        try:
            if self.user:
                watchlistCount = shoppingModels.Watchlist.query(shoppingModels.Watchlist.kl != None, ancestor=self.user_key).count()
                return watchlistCount
            return 0
        except Exception as e:
            logging.error("Error in function <watchlistProducts> : -- %s" % str(e))
            return 0

    # @webapp2.cached_property
    # def marketMakerList(self):
    #     try:
    #         logging.info('Called marketMakerList function')
    #         if self.user:
    #             logging.info('Going to call Query on MarketMaker Model from BournEEHandler')
    #             return shoppingModels.MarketMaker.get_for_UserKey(self.user_key, pn=None, sup=None, quantity=3)
    #         return None
    #     except:
    #         logging.error('Error calling : - shoppingModels.MarketMaker.get_for_UserKey(self.user_key)')
    #         return None

    # @webapp2.cached_property
    # def alerts(self):
    #     try:
    #         logging.info('Called alerts function')
    #         if self.user:
    #             alerts = shoppingModels.Alert.get_for_UserKey(self.user_key, pn=None, quantity=3)
    #             return alerts
    #         return None
    #     except:
    #         logging.error("Error calling : - shoppingModels.Alert.get_for_UserKey(self.user_key, pn=None)")
    #         return None

    @webapp2.cached_property
    def user_real_name(self):
        try:
            if self.user:
                try:
                    user_info = userModels.User.get_by_id(long(self.user_id))
                    return "{} {}".format(str(user_info.name), str(user_info.last_name))
                except AttributeError, e:
                    # avoid AttributeError when the session was delete from the server
                    logging.error(e)
                    self.auth.unset_session()
                    self.redirect_to('home')
            else:
                return 'Not Logged In'
        except Exception as e:
            logging.error("Error determining user_real_name: -- {}".format(e))
            return None

    @webapp2.cached_property
    def user_key(self):
        if self.user:
            user_info = userModels.User.get_by_id(long(self.user_id))
            return user_info.key
        return None

    @webapp2.cached_property
    def user_info(self):
        if self.user:
            user_info = userModels.User.get_by_id(long(self.user_id))
            return user_info
        return None

    @webapp2.cached_property
    def urlsafeUserKey(self):
        if self.user:
            key = self.user_key
            if key:
                return key.urlsafe()
        return None

    @webapp2.cached_property
    def userAddresses(self):
        try:
            if self.user:
                return userModels.Address.get_for_UserKey(self.user_key, quantity=10)
            else:
                return None
        except Exception as e:
            logging.error("Error determining userAddresses: -- {}".format(e))
            return None

    @webapp2.cached_property
    def lastProductsViewed(self):
        return memcache.get('%s:lastProductsViewed' % str(self.request.remote_addr))

    @webapp2.cached_property
    def productSearch_form(self):
        return forms.ProductSearchForm(self)

    @webapp2.cached_property
    def get_parent_search_categories(self):
        CATEGORIES = []
        cats = categoryModels.Category.getCategoryInfo()
        if not cats:
            CATEGORIES = [('ELECTRONICS', 'electronics')]
        else:
            CATEGORIES.extend(cats)
        return CATEGORIES

    def paypal_purchase(self, cart):
        dt = datetime.datetime.now().isoformat()
        keyname = re.sub('\D', '', dt)
        purchaseKey = ndb.Key(shoppingModels.PurchaseRecord, keyname)
        purchase = shoppingModels.PurchaseRecord(
            key=purchaseKey,
            ck=cart.key,
            cuk=cart.uk,
            puk=self.user_key,
            st='NEW',
            s=utils.random_alnum(16)
        )
        if settings.USE_IPN:
            ipn_url = "%s/ipn/%s/%s" % (self.request.host_url, purchaseKey.urlsafe(), purchase.s)
        else:
            ipn_url = None
        if settings.USE_CHAIN:
            seller = cart.uk.get()
            seller_paypal_email = seller.paypal_email
        else:
            seller_paypal_email = None

        pay = paypal.Pay(
            (float(cart.gt)/100),
            "%s/paypal/%s/return/%s/%s" % (self.request.host_url, cart.key.urlsafe(), purchaseKey.urlsafe(), purchase.s),
            "%s/paypal/%s/cancel/%s" % (self.request.host_url, cart.key.urlsafe(), purchaseKey.urlsafe()),
            self.request.remote_addr,
            seller_paypal_email,
            ipn_url,
            shipping=settings.SHIPPING
        )

        purchase.dreq = pay.raw_request
        purchase.dres = pay.raw_response
        purchase.pk = pay.paykey()

        if pay.status() == 'CREATED':
            purchase.st = 'CREATED'
            ok = True
        else:
            purchase.st = 'ERROR'
            ok = False

        purchaseKey = purchase.put()

        return (ok, pay)

    def bournee_template(self, filename, **params):
        logging.info('user: {}'.format(self.user_info))
        params.update({
            'tab': self.usersTab,
            'tab_items': self.tabItems,
            'urlsafeUserKey': self.urlsafeUserKey,
            'usersCartCount': self.usersCartCount,
            'userWatchlistCount': self.userWatchlistCount,
            # 'marketMakerPos': self.marketMakerList,
            # 'alerts': self.alerts,
            'lastProductsViewed': self.lastProductsViewed,
            'categories': utils.SEARCH_CATEGORIES,
            'productSearchForm': self.productSearch_form,
            'cat_info': self.get_parent_search_categories,
        })
        if settings.USE_EMBEDDED and self.user:
            params['endpoint'] = settings.EMBEDDED_ENDPOINT
            # if cart:
            #     (ok, pay) = self.paypal_purchase( cart )
            #     paykey = 'paykey_{}'.format(cart.n)
            #     parms[repr(paykey)] = pay.paykey()
            # if self.belists:
            #     for cart in self.belists:
            #         (ok, pay) = self.paypal_purchase( cart )
            #         paykey = 'paykey_{}'.format(cart.n)
            #         parms[repr(paykey)] = pay.paykey()

        logging.info('Done Updating Params')
        self.render_template(filename, **params)


class RegisterBaseHandler(BournEEHandler):
    """
    Base class for handlers with registration and login forms.
    """
    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.RegisterMobileForm(self)
        else:
            return forms.RegisterForm(self)
