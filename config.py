import os, logging

app_name = "Tiny Probe"

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '14758f1afd44c09b7992073ccf00b43d',
}
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'web.models.models.User',
    'cookie_name': 'session_name'
}
webapp2_config['webapp2_extras.jinja2'] = {
    'template_path': 'templates',
    'environment_args': {'extensions': ['jinja2.ext.i18n']},
}

# jinja2 base layout templates
base_layout = 'base.html'

# locale settings
app_lang = 'en'
locales = ['en_US']

# me bitches
contact_sender = "kordless@gmail.com"
contact_recipient = "kordless@gmail.com"

# Password AES Encryption Parameters
aes_key = "9c85e9bbb92735362d1d59143ea9d50c"
salt = "5758c08d38fe9ff725033600429cde55"

# get your own consumer key and consumer secret by registering at https://dev.twitter.com/apps
# callback url must be: http://[YOUR DOMAIN]/login/twitter/complete
twitter_consumer_key = 'sBhPXfyvmZzKzeGEPKVg'
twitter_consumer_secret = 'KxFRgg0SaCyKk9p6iJOLue4M0uVoAfJc3v4MGicK7fs'

if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
	# github login for TinyProbe dev
	logging.info("yo, i'm using dev version of app on github.com!")
	github_server = 'github.com'
	github_redirect_uri = 'http://localhost:8101/social_login/github/complete'
	github_client_id = '5a3124e4d71e2ce8741c'
	github_client_secret = '1b8488e2022e214f9c2bb2c20ac1f007201d5986'
else:
	# going production level
	github_server = 'github.com'
	github_redirect_uri = 'http://www.tinyprobe.com/social_login/github/complete'
	github_client_id = 'd43f79b4e7c21fa43454'
	github_client_secret = 'a64ddfdc29dcf0c7590147476014950bf160883f'

# gist settings for apps
gist_template_id = '4185065'
gist_html_name = 'tinyprobe.html'
gist_manifest_name = 'tinyprobe.manifest'
gist_javascript_name = 'tinyprobe.js'
gist_thumbnail_name = 'tinyprobe.png'
gist_thumbnail_default_url = '/img/gist_thumbnail.png'
gist_markdown_name = 'README.md'

# gist settings for blog
gist_article_manifest_name = 'tinyprobe-article.manifest'
gist_article_markdown_name = 'tinyprobe-article.md'
memcache_expire_time = 604800

# issue a job token to prevent others from running our tasks by knowing URL
job_token = '917c1f5a7640239c43d52c56061c73a2'

# html whitelist for bleached articles
bleach_tags = ['p', 'em', 'strong', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'td', 'li', 'ul', 'ol', 'table', 'tbody', 'thead', 'iframe', 'tr', 'th', 'span',  'pre', 'i', 'button', 'img', 'a']
bleach_attributes = {'i': ['class'], 'a': ['href', 'rel'], 'table': ['class'], 'img': ['src', 'alt'], 'iframe': ['src', 'width', 'height', 'frameborder'], 'pre': ['class']}

# get your own recaptcha keys by registering at www.google.com/recaptcha
captcha_public_key = "6LeZidUSAAAAAH4URz_h0kKl-NDciRnE3Nw8ajJd"
captcha_private_key = "6LeZidUSAAAAAI1L48D6X2YKToFCmCpXf8VyCHvK"

# tracking shizzle
google_analytics_code = "UA-34233674-1"

# reserved commands for shell to help prevent apps from using them
reserved_commands = ['graph', 'search', 'clear', 'quit', 'close', 'exit', 'help', 'logout', 'curl', 'wget', 'irc', 'status', 'theme']

error_templates = {
    403: 'errors/default_error.html',
    404: 'errors/default_error.html',
    500: 'errors/default_error.html',
}

# Enable Federated login (OpenID and OAuth)
# Google App Engine Settings must be set to Authentication Options: Federated Login
enable_federated_login = True

# jinja2 base layout templates
base_layout = 'base.html'

# terminal commands URI path 
command_path = "/js/commands/"