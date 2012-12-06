# -*- coding: utf-8 -*-

"""
App Handlers
"""
# standard library imports
import logging, os
import urllib, urllib2, hashlib, json, httplib2
import datetime
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


# setup user's repository by forking ours
class AppsInitializeHandler(BaseHandler):
    @user_required
    def get(self):
        # get current user info, then fork tinyprobe repo into their github account
        # user call to Github wants case-sensitive usernames
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
        response = github.fork_new_user_repo('tinyprobe', 'tinyprobe-apps', social_user.access_token)
        return


###################
# Utility Methods #
###################
class AppsClearCacheHandler(BaseHandler):
    @user_required
    def get(self, app_id = None):
        user_info = models.User.get_by_id(long(self.user_id))
        app = models.App.get_by_id(long(app_id))

        if app.owner == user_info.key and github.flush_raw_gist_content(app.gist_id):
            message = 'Article was flushed from cache.'
        else:
            message = 'Something went wrong flushing from cache!'
        
        return message


class AppsDetailHandler(BaseHandler):
    @user_required
    def get(self, app_id = None):
        # check this user owns this app OR it's public and can be viewed
        user_info = models.User.get_by_id(long(self.user_id))
        app = models.App.get_by_id(long(app_id))

        # show it if current user is the owner or it's been made public
        if app.owner == user_info.key or app.public == True:
            params = {'app': app}
            return self.render_template('app/app_detail.html', **params)
        else:
            params = { }
            return self.render_template('app/app_list.html', **params)

    def delete(self, app_id = None):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
        
        # delete the app from the db
        app = models.App.get_by_id(long(app_id))

        if app:
            app.key.delete()
            github.delete_user_gist(social_user.access_token, app.gist_id)
            self.add_message(_('App successfully deleted!'), 'success')
        else:
            self.add_message(_('App was not deleted.  Something went horribly wrong somewhere!'), 'warning')
        
        # notify browser through channel
        channel_token = self.request.get('channel_token')
        channel.send_message(channel_token, 'reload')
        return

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


# JOB SCHEDULER
# schedule a job request for rebuilding user's apps from github gists
class AppsRefreshHandler(BaseHandler):
    def task(self, user=None, channel_token=None):
        # use both token and user to schedule job for updating user's apps from github gists
        params = {'channel_token': channel_token, 'user': user, 'job_token': config.job_token}
        t = taskqueue.add(method='GET', url='/apps/buildlist/', params=params, transactional=True)
        return

    # user pushed apps refresh/rebuild button on apps list page
    @user_required
    def get(self):
        # refresh_token gets passed in URL and we use the current logged in user to start a job
        channel_token = self.request.get('channel_token')
        user = self.user_id
        db.run_in_transaction(self.task, user, channel_token)
        return


# JOB HANDLER
# handle a job request for rebuilding a user's apps from their github gists
class AppsBuildListHandler(BaseHandler):
    def get(self):
        # pull the github token out of the social user db and grab gists from github
        if self.request.get('job_token') != config.job_token:
            logging.info("Hacker attack on jobs!")
            return
        else: 
            user_info = models.User.get_by_id(long(self.request.get('user')))
            social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
            apps = github.get_user_gists(social_user.uid, social_user.access_token)

            # update with the apps we get back from github
            for app in apps:
                app2 = models.App.get_by_user_and_gist_id(user_info.key, app['gist_id'])

                if app2:
                    # update existing app with new data
                    app2.name = app['name']
                    app2.command = app['command']
                    app2.description = app['description']
                    app2.thumb_url = app['thumb_url']
                    app2.gist_id = app['gist_id']
                    app2.public = app['public']
                else:
                    # we have a new app on our hands - insert
                    app2 = models.App(
                        name = app['name'],
                        command = app['command'],
                        description = app['description'],
                        thumb_url = app['thumb_url'],
                        gist_id = app['gist_id'],
                        owner = user_info.key,
                        author = user_info.key,
                        github_author = app['github_author'],
                        public = app['public'],
                    )
                
                # update
                app2.put()

                # flush memcache copy just in case we had it
                github.flush_raw_gist_content(app2.gist_id)
                                
            # use the channel to tell the browser we are done
            channel_token = self.request.get('channel_token')
            channel.send_message(channel_token, 'reload')
            return


class AppsListHandler(BaseHandler):
    @user_required
    def get(self):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
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
            apps = models.App.get_by_user(user_info.key)

            if not apps:
            	# no apps, no problem, make one
            	params = {}
            	return self.redirect_to('apps-new', **params)
            else:
            	# setup channel to do page refresh in case they sync
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
        
        # load values out of the form, including whether the gist should be public or not
        name = self.form.appname.data.strip()
        command = self.form.appcommand.data.strip()
        description = self.form.appdescription.data.strip()
        if self.form.apppublic.data.strip() == 'public':
            public = True
        else:
            public = False

        # check to see if there is an app in this account with this command name, or used globally 
        if command in config.reserved_commands or models.App.get_by_user_and_command(user_info.key, command):
            self.add_message(_("The command '%s' is already in use.  Try picking another command name for your app." % command), 'warning')
            return self.get()
        
        # if the gist is going to be public, fork an existing gist to include thumbnail
        if public:
            # fork our base gist in config.py to the user's github account
            gist = github.fork_gist(social_user.access_token, config.gist_template_id)
            if not gist:
                # if we can't fork or something went wrong let's just force a creation of a private gist
                public = False
            else:
                gist_id = gist['id']

        # either way, we build values for templates now
        template_val = {
            "name": name,
            "command": command,
            "description": description,
            "github_user": social_user.uid,
        }

        # ...and build a dict of files we want to push into the gist
        files = {
            config.gist_manifest_name: self.jinja2.render_template("app/gist_manifest_stub.txt", **template_val),
            config.gist_javascript_name: self.jinja2.render_template("app/gist_javascript_stub.txt", **template_val),
            config.gist_html_name: self.jinja2.render_template("app/gist_html_stub.txt", **template_val),
            config.gist_markdown_name: self.jinja2.render_template("app/gist_markdown_stub.txt", **template_val)
        }

        # now we loop through the files and add them to the other JSON values for github
        file_data = dict((filename, {'content': text}) for filename, text in files.items())
        
        # patch the gist if app/gist is public
        if public:
            data = json.dumps({'description': "%s for TinyProbe" % name, 'files': file_data})
            patch = github.patch_user_gist(social_user.access_token, gist_id, data)
            thumb_url = gist['files'][config.gist_thumbnail_name]['raw_url']

            if not patch:
                self.add_message(_('App was not created.  No gist returned from Github.'), 'warning')
                return self.get()  
        else:
            # if app/gist is to be private, we just make a new gist
            data = json.dumps({'description': "%s for TinyProbe" % name, 'public': public, 'files': file_data})
            gist = github.put_user_gist(social_user.access_token, data)
            
            # private gists get a holder thumbnail we host
            if gist:
                gist_id = gist['id']
                thumb_url = config.gist_thumbnail_default_url
            else:
                self.add_message(_('App was not created.  No gist returned from Github.'), 'warning')
                return self.get()

        # make sure it's not already in the database (unlikely)
        if not models.App.get_by_user_and_gist_id(user_info.key, gist_id):
            # save the app in our database            
            app = models.App(
                name = name,
                command = command,
                description = description,
                thumb_url = thumb_url,
                gist_id = gist_id,
                owner = user_info.key,
                author = user_info.key,
                github_author = social_user.uid,
                public = public,
            )

            app.put()

            self.add_message(_('App %s successfully created!' % name), 'success')
            params = {"app_id": app.key.id()}
            return self.redirect_to('apps-detail', **params)
        else:
            # something went wrong with the App.put_user_app call in models.py
            self.add_message(_("An app gist was created, but we didn't get it in the database!"), 'warning')
            return self.get()


    @webapp2.cached_property
    def form(self):
        return forms.AppForm(self)

