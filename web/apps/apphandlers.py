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
from google.appengine.ext import db
from google.appengine.api import channel

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


class AppsDetailHandler(BaseHandler):
    @user_required
    def get(self, app_id = None):
        # check this user owns this app OR it's public and can be viewed
        user_info = models.User.get_by_id(long(self.user_id))
        app = models.App.get_by_id(long(app_id))
        logging.info("value is: %s" % app)

        # show it if current user is the owner or it's been made public
        if app.owner == self.user_id or app.public == True:
            params = {'app': app}
            return self.render_template('app/app_detail.html', **params)
        else:
            params = { }
            return self.render_template('app/app_list.html', **params)

    @webapp2.cached_property
    def form(self):
        return forms.AppForm(self)


class AppsPublicHandler(BaseHandler):
    @user_required
    def get(self):
        # serve all public apps
        return
        # test yanking a gist
        # gist = models.App.get_by_user_and_gist_id(user_info.key, '3902522')
        # logging.info("value is: %s" % gist)


class AppsRefreshHandler(BaseHandler):
	def task(self, user=None, channel_token=None):
		# use both token and user to schedule job for updating user's apps from github gists
		t = taskqueue.add(method='GET', url='/apps/buildlist/', params={'channel_token': channel_token, 'user': user}, transactional=True)
		return

	# user pushed apps refresh/rebuild button on apps list page
	@user_required
	def get(self):
		# refresh_token gets passed in URL and we use the current logged in user to start a job
		channel_token = self.request.get('channel_token')
		user = self.user_id
		db.run_in_transaction(self.task, user, channel_token)
		return


class AppsBuildListHandler(BaseHandler):
	# handle a job request for rebuilding a user's apps from their github gists
	def get(self):
		import time
		time.sleep(5)
		channel_token = self.request.get('channel_token')
		user = self.request.get('user')
		channel.send_message(channel_token, 'reload')
		return

	def post(self):
		self.get()


class AppsListHandler(BaseHandler):
    @user_required
    def get(self):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        # logging.info("value is: %s" % user_info)
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')

        # what do we do if we don't have a token or association?  auth 'em!
        if not social_user:
            scope = 'gist'
            # drop a short lived cookie so we know where to come back to when we're done auth'ing
            utils.write_cookie(self, 'oauth_return_url', 'apps', '/', 15)
            github_helper = github.GithubAuth(scope)
            self.redirect( github_helper.get_authorize_url() )
            return
        else:
            # return our list of apps we grab from github - TODO push into database?
            # apps = github.get_user_gists(social_user.uid, social_user.access_token)
            apps = models.App.get_by_user(user_info.key)
            channel_token = user_info.key.urlsafe()
            refresh_channel = channel.create_channel(channel_token)
            params = {'apps': apps, 'refresh_channel': refresh_channel, 'channel_token': channel_token}
            return self.render_template('app/app_list.html', **params)


class AppsCreateHandler(BaseHandler):
    @user_required
    def get(self):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')

        # what do we do if we don't have a token or association?  auth 'em!
        if not social_user:
            scope = 'gist'
            # drop a short lived cookie so we know where to come back to when we're done auth'ing
            utils.write_cookie(self, 'oauth_return_url', 'apps-create', '/', 15)
            github_helper = github.GithubAuth(scope)
            self.redirect( github_helper.get_authorize_url() )
            return
        else:
            params = {}
            return self.render_template('app/app_create.html', **params)
        
    @user_required
    def post(self):
        if not self.form.validate():
            return self.get()

        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
        
        # load values out of the form
        name = self.form.appname.data.strip()
        command = self.form.appcommand.data.strip()
        description = self.form.appdescription.data.strip()
        preview = config.gist_preview_image

        # check to see if there is an app in this account with this command name, or used globally 
        if command in config.reserved_commands or models.App.get_by_user_and_command(user_info.key, command):
            self.add_message(_("The command '%s' is already in use.  Try picking another command name for your app." % command), 'warning')
            # return self.get()
        
        # push the sample app to the user's gist on github
        template_val = {
            "name": name,
            "command": command,
            "description": description,
            "username": social_user.uid,
            "preview": preview,
        }

        # build a dict of files we want to push into the gist
        files = {
            config.gist_manifest_name: self.jinja2.render_template("app/gist_manifest_stub.txt", **template_val),
            config.gist_javascript_name: self.jinja2.render_template("app/gist_javascript_stub.txt", **template_val),
            config.gist_markdown_name: self.jinja2.render_template("app/gist_markdown_stub.txt", **template_val)
        }

        # loop through them and add them to the other JSON values for github
        file_data = dict((filename, {'content': text}) for filename, text in files.items())
        data = json.dumps({'description': "%s for TinyProbe" % name, 'public': True, 'files': file_data})

        # stuff it to github and then grab our gist_id
        gist = github.put_user_gist(social_user.access_token, data)
        logging.info("value is: %s" % gist)
        gist_id = gist['id']

        # make sure it's not already in the database (unlikely)
        if not models.App.get_by_user_and_gist_id(user_info.key, gist_id):
            # save the app in our database            
            app = models.App(
                name = name,
                command = command,
                description = description,
                preview = preview,
                gist_id = gist_id,
                owner = user_info.key,
            )
            app.put()

            self.add_message(_('App %s successfully created!' % name), 'success')
            params = {"app_id": app.key.id()}
            return self.redirect_to('apps-detail', **params)
        else:
            # something went wrong with the App.put_user_app call in models.py
            self.add_message(_('App was not created.  Something went horribly wrong somewhere!' % name), 'warning')
            return self.get()


    @webapp2.cached_property
    def form(self):
        return forms.AppForm(self)

