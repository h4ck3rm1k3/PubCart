config = {

# environment this app is running on: localhost, testing, production
'environment': "production",

# ----> ADD MORE CONFIGURATION OPTIONS HERE <----
# webapp2 sessions
'webapp2_extras.sessions' : {'secret_key': 'QOV2NLJ7654FcXuneZmIFXuV3WU4z8JEfZp7lIto9'},

# webapp2 authentication
'webapp2_extras.auth' : {'user_model': 'boilerplate.models.User',
                         'cookie_name': 'session_name'},

# jinja2 templates
'webapp2_extras.jinja2' : {'template_path': ['templates','boilerplate/templates', 'admin/templates'],
                           'environment_args': {'extensions': ['jinja2.ext.i18n']}},

# application name
'app_name' : "PubCart.",

# the default language code for the application.
# should match whatever language the site uses when i18n is disabled
'app_lang' : 'en',

# Locale code = <language>_<territory> (ie 'en_US')
# to pick locale codes see http://cldr.unicode.org/index/cldr-spec/picking-the-right-language-code
# also see http://www.sil.org/iso639-3/codes.asp
# Language codes defined under iso 639-1 http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# Territory codes defined under iso 3166-1 alpha-2 http://en.wikipedia.org/wiki/ISO_3166-1
# disable i18n if locales array is empty or None
'locales' : ['en_US', 'es_ES', 'it_IT', 'zh_CN', 'id_ID', 'fr_FR', 'de_DE', 'ru_RU', 'pt_BR', 'cs_CZ'],

# contact page email settings
'contact_sender' : "Jay Elbourne",
'contact_recipient' : "jayelbourne@gmail.com",

# Password AES Encryption Parameters
'aes_key' : "th6hk3e6k3f7k0l4d9gj64k88FcXuneZ",
'salt' : "DONOTCRACKMYPASSWORDSORYOUWILLDIE",

# get your own consumer key and consumer secret by registering at https://dev.twitter.com/apps
# callback url must be: http://[YOUR DOMAIN]/login/twitter/complete
'twitter_consumer_key' : 'nmkfdS6WaPwcJBZA2RyNNA',
'twitter_consumer_secret' : 'QOV2NLJ2188FcXuneZmIFXuV3WU6z2JEfZp7lIto8',

#Facebook Login
# get your own consumer key and consumer secret by registering at https://developers.facebook.com/apps
#Very Important: set the site_url= your domain in the application settings in the facebook app settings page
# callback url must be: http://[YOUR DOMAIN]/login/facebook/complete
'fb_api_key' : '636727389676617',
'fb_secret' : '49e3b37431a65ca6aaaf00c3f069661b',

#Linkedin Login
#Get you own api key and secret from https://www.linkedin.com/secure/developer
'linkedin_api' : 'sem8ipobxci3',
'linkedin_secret' : 'MZlMPucOwxi9nmUo',

# Github login
# Register apps here: https://github.com/settings/applications/new
'github_server' : 'github.com',
'github_redirect_uri' : 'http://www.pubcart.com/social_login/github/complete',
'github_client_id' : 'd4088d3a1b1dda77922c',
'github_client_secret' : '39d52c2f0ae6e87f41f5a37049ffa2ca71059af9',

# get your own recaptcha keys by registering at http://www.google.com/recaptcha/
'captcha_public_key' : "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE",
'captcha_private_key' : "PUT_YOUR_RECAPCHA_PRIVATE_KEY_HERE",

# Leave blank "google_analytics_domain" if you only want Analytics code
'google_analytics_domain' : "pubcart.com",
'google_analytics_code' : "UA-XXXXX-X",

# add status codes and templates used to catch and display errors
# if a status code is not listed here it will use the default app engine
# stacktrace error page or browser error page
'error_templates' : {
    403: 'errors/default_error.html',
    404: 'errors/default_error.html',
    500: 'errors/default_error.html',
},

# Enable Federated login (OpenID and OAuth)
# Google App Engine Settings must be set to Authentication Options: Federated Login
'enable_federated_login' : True,

# jinja2 base layout template
'base_layout' : 'base.html',

# send error emails to developers
'send_mail_developer' : True,

# fellas' list
'developers' : (
    ('Jason Andrew Elbourne', 'jayelbourne@gmail.com'),
),


} # end config
