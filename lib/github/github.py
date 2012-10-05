import config
from lib.rauth.service import OAuth2Service
from urllib2 import  urlopen
import json
import logging

# Github OAuth Implementation
class GithubAuth(object):
    
    def __init__(self, scope):
        self.scope = scope
        self.access_token_url = 'https://%s/login/oauth/access_token' % config.github_server
        self.authorization_url = 'https://%s/login/oauth/authorize' % config.github_server
        self.client_key = config.github_client_id
        self.client_secret = config.github_client_secret

        self.auth = OAuth2Service(
            name = 'github',
            authorize_url = self.authorization_url,
            access_token_url = self.access_token_url,
            consumer_key = self.client_key,
            consumer_secret = self.client_secret
        )

    # wrap get_authorize_url()
    def get_authorize_url(self):
        auth_url = self.auth.get_authorize_url()
        logging.info("auth url is: %s" % auth_url)
        return auth_url