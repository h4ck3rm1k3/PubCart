"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""
from webapp2 import Route
from webapp2_extras.routes import RedirectRoute
from web import web_handlers
from web import cartHandlers
from web import oauth_handlers
from web import productHandlers
from api import rest_api

secure_scheme = 'https'

_prelaunch_routes = [
	RedirectRoute('/', web_handlers.PreLaunchSignupHandler, name='home', strict_slash=True),
	RedirectRoute('/', web_handlers.PreLaunchSignupHandler, name='preLaunchSignup', strict_slash=True),
	RedirectRoute('/thankyou', web_handlers.PreLaunchThankyouHandler, name='preLaunchThankyou', strict_slash=True),
	RedirectRoute('/login/', web_handlers.PreLaunchSignupHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', web_handlers.PreLaunchLogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/register/', web_handlers.PreLaunchSignupHandler, name='register', strict_slash=True),
    RedirectRoute('/about/', web_handlers.PreLaunchAboutHandler, name='about', strict_slash=True),
    RedirectRoute('/jobs/', web_handlers.PreLaunchJobsHandler, name='jobs', strict_slash=True),

]

_routes = [
	RedirectRoute('/', web_handlers.HomeRequestHandler, name='home', strict_slash=True),

	RedirectRoute('/addaddress', web_handlers.AddAddressHandler, name='addAddress', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/discoverProducts', productHandlers.DiscoverProductsHandler, name='discoverProducts', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/product/<urlsafeProductKey>', productHandlers.ProductRequestHandler, name='product', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/product/<sellerID>/<productNumber>', productHandlers.ProductRequestHandler, name='sellerProduct', handler_method='sellers_product', strict_slash=True),
	RedirectRoute(r'/getProduct', productHandlers.GetProductFormHandler, name='getProduct', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/clearLastProductsViewed', productHandlers.ClearLastProductsViewedHandler, name='clearLastProductsViewed', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/exchangeOrder/<pk>', web_handlers.ExchangeOrderHandler, name='exchangeOrder', strict_slash=True),
	RedirectRoute(r'/createLimitOrder/<pk>', web_handlers.CreateLimitOrderFormHandler, name='createLimitOrder', strict_slash=True),
	RedirectRoute(r'/createAlertForm/<pk>', web_handlers.CreateAlertFormHandler, name='createAlert', strict_slash=True),
	RedirectRoute(r'/watchlist/<urlsafeWatchlistKey>', web_handlers.FullPageWatchlistHandler, name='fullPageWatchlist', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/positions', web_handlers.FullPagePositionsHandler, name='fullPagePositions', methods=['GET'], strict_slash=True),

	RedirectRoute(r'/completeExchangeOrder', web_handlers.CompleteExchangeOrderHandler, name='completeExchangeOrder', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/addToWatchlist', web_handlers.AddToWatchlistHandler, name='addToWatchlist', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/deleteFromWatchlist', web_handlers.DeleteFromWatchlistHandler, name='deleteFromWatchlist', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/createAlert', web_handlers.CreateAlertHandler, name='createAlertPost', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/discoverCarts', cartHandlers.DiscoverCartsHandler, name='discoverCarts', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/myCarts', cartHandlers.MyCartsHandler, name='mycarts', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/createCart', cartHandlers.CreateCartInfoHandler, name='createCart', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute(r'/createCartSubmit', cartHandlers.CreateCartInfoHandler, name='createCartSubmit', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/cart/<urlsafeCartKey>', cartHandlers.FullPageCartHandler, name='fullPageCart', methods=['GET'], strict_slash=True),
	RedirectRoute(r'/cart/<userID>/<cartName>', cartHandlers.FullPageCartHandler, name='fullPublicCart', handler_method='public_cart',strict_slash=True),
	RedirectRoute(r'/makeCartPublic/<urlsafeCartKey>', cartHandlers.MakeCartPublicHandler, name='makeCartPublic', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute(r'/forkCart/<urlsafeCartKey>', cartHandlers.ForkCartHandler, name='forkCart', methods=['GET','POST'], strict_slash=True),
	RedirectRoute(r'/editCartDetails/<urlsafeCartKey>', cartHandlers.EditCartDetailsFormHandler, name='editCartDetails', methods=['GET','POST'], strict_slash=True),
	RedirectRoute(r'/makeCartDefault', cartHandlers.MakeCartDefaultFormHandler, name='makeCartDefault', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/addToCart', cartHandlers.AddToCartHandler, name='addToCart', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/selectCartForm/<urlsafeProductKey>', cartHandlers.AddToSelectedCartFormHandler, name='selectCartForm', methods=['GET', 'POST'], strict_slash=True),
	RedirectRoute(r'/removeFromCart', cartHandlers.DeleteOrderFromCartHandler, name='removeFromCart', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/changeQntOfOrder', cartHandlers.ChangeQuantityOfOrderHandler, name='changeQntOfOrder', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/copyOrderToCart', cartHandlers.CopyOrderBetweenCartsHandler, name='copyOrderToCart', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/deleteCart', cartHandlers.DeleteCartHandler, name='deleteCart', methods=['POST'], strict_slash=True),

	RedirectRoute(r'/paypal/<urlsafeCartKey>', web_handlers.PayPalPaymentHandler, name='paypalPayment', methods=['POST'], strict_slash=True),
	RedirectRoute(r'/paypal/<urlsafeCartKey>/return/<urlsafePurchaseKey>/<secret>', web_handlers.PaypalReturnHandler, name='paypalReturn', strict_slash=True),
	RedirectRoute(r'/paypal/<urlsafeCartKey>/cancel/<urlsafePurchaseKey>', web_handlers.PaypalCancelHandler, name='patpalCancel', strict_slash=True),
	RedirectRoute(r'/ipn/<urlsafePurchaseKey>/<secret>', web_handlers.PaypalIPNHandler, name='paypalIPN', methods=['POST'], strict_slash=True),


	RedirectRoute(r'/oauth/register/portal', web_handlers.RegisterOAuthClientHandler, name='reg_oauth_client', strict_slash=True),
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
	#for r in _routes:
	for r in _prelaunch_routes:
		app.router.add(r)