# -*- coding: utf-8 -*-

"""
App Handlers
"""
# standard library imports
import logging, os
import urllib, urllib2, hashlib, json, httplib2
from lib.i18n import get_territory_from_ip

# related third party imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from google.appengine.api import taskqueue

# local application/library specific imports
import config
import web.forms as forms
import web.models.models as models
from lib import utils, httpagentparser, captcha
from web.basehandler import BaseHandler
from web.basehandler import user_required

# social login
from lib.github import github
from lib.twitter import twitter

class ShellHandler(BaseHandler):
    @user_required
    def get(self):
        logging.info("foo")
        if (self.user):
            params = {'username': self.user}
            return self.render_template('shell/shell.html', **params)
        else:
            self.redirect_to('login')

    def post(self):
        self.get()
