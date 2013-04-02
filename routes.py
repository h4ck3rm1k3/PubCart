"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""
from webapp2 import Route
from webapp2_extras.routes import RedirectRoute
from web import webHandlers
from web import cartHandlers
from web import oauth_handlers
from web import productHandlers
from web import paypalHandlers
from web import searchHandlers
from web import registrationHandlers
from web import tabHandlers
from api import rest_api
from lib.livecount import counter as countHandlers

secure_scheme = 'https'

_routes = [
	RedirectRoute('/', webHandlers.HomeRequestHandler, name='home', strict_slash=True),
	RedirectRoute('/login/', webHandlers.LoginRequestHandler, name='login', methods=['GET','POST'], strict_slash=True),
	RedirectRoute('/logout/', webHandlers.LogoutRequestHandler, name='logout', methods=['GET'], strict_slash=True),

	RedirectRoute('/r', registrationHandlers.SoftRegisterRequestHandler, name='softRegister', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute('/id/<ek>', registrationHandlers.IntimateRegisterRequestHandler, name='intimateRegister', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute('/adr/<uk>', registrationHandlers.AddressRegisterRequestHandler, name='addressRegister', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute('/sh', registrationHandlers.ShareRegisterRequestHandler, name='shareRegister', methods=['GET'], strict_slash=True),
	RedirectRoute('/ap', registrationHandlers.AppsRegisterRequestHandler, name='appRecommendRegister', methods=['GET'], strict_slash=True),
	
	
	
	RedirectRoute('/addaddress', webHandlers.AddAddressHandler, name='addAddress', methods=['POST'], strict_slash=True),

	RedirectRoute('/search', searchHandlers.ProductSearchHandler, name='mainSearch', strict_slash=True),

	RedirectRoute(r'/discoverProducts', productHandlers.DiscoverProductsHandler, name='discoverProducts', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/product/<urlsafeProductKey>', productHandlers.ProductRequestHandler, name='product', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/product/<sellerID>/<productNumber>', productHandlers.ProductRequestHandler, name='sellerProduct', handler_method='sellers_product', strict_slash=True),
	RedirectRoute(r'/getProduct', productHandlers.GetProductFormHandler, name='getProduct', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/clearLastProductsViewed', productHandlers.ClearLastProductsViewedHandler, name='clearLastProductsViewed', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/paidTabs', tabHandlers.PaidTabsRequestHandler, name='paidTabsList', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/viewTab/<urlsafeTabKey>', tabHandlers.ViewTabRequestHandler, name='viewTab', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/addToTab', tabHandlers.AddToTabHandler, name='addToTab', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/exchangeOrder/<pk>', webHandlers.ExchangeOrderHandler, name='exchangeOrder', strict_slash=True),
	RedirectRoute(r'/createLimitOrder/<pk>', webHandlers.CreateLimitOrderFormHandler, name='createLimitOrder', strict_slash=True),
	RedirectRoute(r'/createAlertForm/<pk>', webHandlers.CreateAlertFormHandler, name='createAlert', strict_slash=True),
	RedirectRoute(r'/watchlist/<urlsafeWatchlistKey>', webHandlers.FullPageWatchlistHandler, name='fullPageWatchlist', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/positions', webHandlers.FullPagePositionsHandler, name='fullPagePositions', methods=['GET'], strict_slash=True),

	RedirectRoute(r'/completeExchangeOrder', webHandlers.CompleteExchangeOrderHandler, name='completeExchangeOrder', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/addToWatchlist', webHandlers.AddToWatchlistHandler, name='addToWatchlist', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/deleteFromWatchlist', webHandlers.DeleteFromWatchlistHandler, name='deleteFromWatchlist', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/createAlert', webHandlers.CreateAlertHandler, name='createAlertPost', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/discoverCarts', cartHandlers.DiscoverCartsHandler, name='discoverCarts', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/myCarts', cartHandlers.MyCartsHandler, name='mycarts', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/createCart', cartHandlers.CreateCartInfoHandler, name='createCart', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute(r'/createCartSubmit', cartHandlers.CreateCartInfoHandler, name='createCartSubmit', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/cart/<urlsafeCartKey>', cartHandlers.FullPageCartHandler, name='fullPageCart', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/cart/<userID>/<cartName>', cartHandlers.FullPageCartHandler, name='fullPublicCart', handler_method='public_cart',strict_slash=True),
	RedirectRoute(r'/makeCartPublic/<urlsafeCartKey>', cartHandlers.MakeCartPublicHandler, name='makeCartPublic', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute(r'/forkCart/<urlsafeCartKey>', cartHandlers.ForkCartHandler, name='forkCart', methods=['GET','POST'], strict_slash=True),
	RedirectRoute(r'/editCartDetails/<urlsafeCartKey>', cartHandlers.EditCartDetailsFormHandler, name='editCartDetails', methods=['GET','POST'], strict_slash=True),
	RedirectRoute(r'/addToCart', cartHandlers.AddToCartHandler, name='addToCart', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/selectCartForm/<urlsafeProductKey>', cartHandlers.AddToSelectedCartFormHandler, name='selectCartForm', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute(r'/removeFromCart', cartHandlers.DeleteOrderFromCartHandler, name='removeFromCart', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/changeQntOfOrder', cartHandlers.ChangeQuantityOfOrderHandler, name='changeQntOfOrder', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/copyOrderToCart', cartHandlers.CopyOrderBetweenCartsHandler, name='copyOrderToCart', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/deleteCart', cartHandlers.DeleteCartHandler, name='deleteCart', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/paypal/<urlsafeCartKey>', paypalHandlers.PayPalPaymentHandler, name='paypalPayment', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/paypal/<urlsafeCartKey>/return/<urlsafePurchaseKey>/<secret>', paypalHandlers.PaypalReturnHandler, name='paypalReturn', strict_slash=True),
	RedirectRoute(r'/paypal/<urlsafeCartKey>/cancel/<urlsafePurchaseKey>', paypalHandlers.PaypalCancelHandler, name='patpalCancel', strict_slash=True),
	RedirectRoute(r'/ipn/<urlsafePurchaseKey>/<secret>', paypalHandlers.PaypalIPNHandler, name='paypalIPN', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/oauth/register/portal', webHandlers.RegisterOAuthClientHandler, name='reg_oauth_client', strict_slash=True),
	RedirectRoute(r'/oauth/authorize', oauth_handlers.AuthorizationHandler, name='oauth_authorize', strict_slash=True),
	RedirectRoute(r'/oauth/token', oauth_handlers.AccessTokenHandler, name='oauth_token', strict_slash=True),

	## Simple Cathcall API Route
	('/api/v1.*', rest_api.Rest),
]

def get_routes():
	return _routes

def add_routes(app):
	if app.debug:
		secure_scheme = 'http'
	for r in _routes:
		app.router.add(r)