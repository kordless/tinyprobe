# -*- coding: utf-8 -*-

"""
Blog Handlers
"""
# standard library imports
import logging, os
import urllib, urllib2, hashlib, httplib2
import json
import datetime
import re

# related third party imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from web.basehandler import BaseHandler
from web.basehandler import user_required

# google shizzle
from google.appengine.api import taskqueue
from google.appengine.api import channel
from google.appengine.ext import db

# local application/library specific imports
import config
import web.forms as forms
import web.models.models as models
from lib import utils, httpagentparser, captcha
from lib.i18n import get_territory_from_ip
import bleach
import html5lib

# social login
from lib.github import github
from lib.twitter import twitter
from lib.markdown import markdown

##################
# Public Methods #
##################
class PublicBlogHandler(BaseHandler):
    def get(self):
        # load articles in from db and github, stuff them in an array
        date_format = "%a, %d %b %Y"
        articles = models.Article.get_all()
        blogposts = []
        
        # loop through all articles
        for article in articles:
            logging.info("value is: %s" % article)
            # if there's content on Github to serve
            raw_gist_content = github.get_raw_gist_content(article.gist_id)

            if raw_gist_content:
                # sanitize javascript
                article_html = bleach.clean(markdown.markdown(raw_gist_content), config.bleach_tags, config.bleach_attributes)
                article_title = bleach.clean(article.title)
                article_summary = bleach.clean(article.summary)

                # created and by whom
                created = article.created.strftime(date_format)
                owner_info = models.User.get_by_id(article.owner.id())
                
                # build entry
                entry = {
                    'created': created,
                    'article_id': article.key.id(),
                    'article_title': article_title,
                    'article_type': article.article_type, 
                    'article_html': article_html,
                    'article_summary': article_summary,
                    'article_slug': article.slug,
                    'article_owner': owner_info.username,
                    'article_host': self.request.host,
                }
                
                logging.info("value is: %s" % article.draft)
                # append article if it's a guide, it's public, and not a draft            
                if not article.draft:
                    blogposts.append(entry)
                
        # pack and stuff into template
        params = {'blogposts': blogposts}
        return self.render_template('blog/blog.html', **params)


# TODO: needs to be fixed to guarantee 10 items get spit out
class PublicBlogRSSHandler(BaseHandler):
    def get(self):
        # load articles in from db and github, stuff them in an array
        date_format = "%a, %d %b %Y"
        articles = models.Article.get_all()
        blog_title = "StackGeek Blog"
        epoch_start = datetime.datetime(1970, 1, 1)
        blog_last_updated = epoch_start

        entries = []
        for article in articles[0:10]:
            raw_gist_content = github.get_raw_gist_content(article.gist_id)

            if raw_gist_content:
                owner_info = models.User.get_by_id(article.owner.id())
                
                # sanitize javascript
                article_html = bleach.clean(markdown.markdown(raw_gist_content), config.bleach_tags, config.bleach_attributes)
                article_title = bleach.clean(article.title)
                article_summary = bleach.clean(article.summary)

                if article.updated > blog_last_updated:
                    blog_last_updated = article.updated
                entry = {
                    'slug': article.slug,
                    'user_slug': "%s/" % owner_info.username,
                    'created': article.created, 
                    'updated': article.updated, 
                    'title': article_title, 
                    'summary': article_summary, 
                    'html': article_html,
                    'article_host': self.request.host,
                }

                if not article.draft:
                    entries.append(entry)

        # didn't get any matches in our loop
        date_format = "%a, %d %b %Y %H:%M:%S GMT"
        if blog_last_updated == epoch_start:
            blog_last_updated = datetime.datetime.utcnow().strftime(date_format) 
        else:
            blog_last_updated = blog_last_updated.strftime(date_format)

        params = {
            'blog_title': blog_title, 
            'blog_last_updated': blog_last_updated,
            'author': 'StackGeek and Various Site Contributers',
            'slug': '',
            'bio': config.site_bio, 
            'entries': entries,
        }
        
        self.response.headers['Content-Type'] = 'application/xml'
        return self.render_template('blog/feed.xml', **params)


class BlogArticleSlugHandler(BaseHandler):
    def get(self, slug = None):
        # look up our article
        article = models.Article.get_by_slug(slug)
        
        if not article:
            return self.render_template('errors/default_error.html')

        raw_gist_content = github.get_raw_gist_content(article.gist_id)
        logging.info("value is: %s" % article.gist_id)
        # if there's content on Github to serve
        if raw_gist_content:
            owner_info = models.User.get_by_id(article.owner.id())
            
            # load name
            if not owner_info.name:
                name = owner_info.username
            else:
                name = "%s %s" % (owner_info.name, owner_info.last_name)

            # load github use
            try:
                github_username = social_user.uid
            except:
                github_username = None

            # load articles in from db and github, stuff them in an array
            date_format = "%a, %d %b %Y"

            # sanitize javascript
            article_html = bleach.clean(markdown.markdown(raw_gist_content), config.bleach_tags, config.bleach_attributes)
            article_title = bleach.clean(article.title)
            article_summary = bleach.clean(article.summary)
            article_host = self.request.host

            # serve page if we have contents
            created = article.created.strftime(date_format)
            entry = {
                'created': created, 
                'article_id': article.key.id(), 
                'article_title': article_title,
                'article_html': article_html, 
                'article_slug': article.slug,
                'article_owner': owner_info.username,
                'article_host': self.request.host,
            }
            # pack and stuff into template
            params = {
                'name': name,
                'github_username': github_username, 
                'menu_choice': 'blog', 
                'entry': entry,
            }
            return self.render_template('blog/blog_article_detail.html', **params)
        
        else:
            params = {}
            return self.render_template('errors/default_error.html', **params)


##################
# Auth'd Methods #
##################
# class dealing with github actions for article including delete, draft update, forking
class BlogArticleActionsHandler(BaseHandler):
    @user_required
    def get(self, article_id = None):
        # pull the github token out of the social user db and then fork it
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
        article = models.Article.get_by_id(long(article_id))

        # lame because we don't do anything if we fail here
        if article:
            gist = github.fork_gist(social_user.access_token, article.gist_id)
            # we have a new article on our hands after the fork - fetch the data and insert
            if gist:
                # prep the slug
                slug = utils.slugify(gist['title'])
                
                # stuff into entry
                article = models.Article(
                    title = gist['title'],
                    summary = gist['summary'],
                    created = datetime.datetime.fromtimestamp(gist['published']),
                    gist_id = gist['gist_id'],
                    owner = user_info.key,
                    slug = slug,
                    article_type = gist['article_type'],
                )
            
                # update db
                article.put()
        return

    @user_required
    def delete(self, article_id = None):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')

        # delete the entry from the db
        article = models.Article.get_by_id(long(article_id))

        if article:
            article.key.delete()
            github.delete_user_gist(social_user.access_token, article.gist_id)
            self.add_message(_('Article successfully deleted!'), 'success')
        else:
            self.add_message(_('Article was not deleted.  Something went horribly wrong somewhere!'), 'warning')

        # use the channel to tell the browser we are done and reload
        channel_token = self.request.get('channel_token')
        channel.send_message(channel_token, 'reload')
        return

    # deal with draft or published status changes from slider
    @user_required
    def put(self, article_id = None):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')

        # what's the draft status set to?
        # note: slider returns 'true' for published and 'false' for draft :(
        draft = self.request.get('draft')

        if draft == 'false':
            draft = False
        else:
            draft = True

        # update the entry
        article = models.Article.get_by_id(long(article_id))
        if article:
            article.draft = draft
            article.put()
        return


class BlogArticleCreateHandler(BaseHandler):
    @user_required
    def get(self):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')

        # what do we do if we don't have a token or association?  auth 'em!
        if not social_user:
            scope = 'gist'
            # drop a short lived cookie so we know where to come back to when we're done auth'ing
            utils.write_cookie(self, 'oauth_return_url', 'blog-article-create', '/', 15)
            github_helper = github.GithubAuth(scope)
            self.redirect( github_helper.get_authorize_url() )
            return
        else:
            params = {}
            return self.render_template('blog/blog_article_create.html', **params)

    @user_required
    def post(self):
        if not self.form.validate():
            return self.get()

        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
        
        # load values out of the form
        title = self.form.title.data.strip()
        summary = self.form.summary.data.strip()
        article_type = self.form.article_type.data.strip()
        
        # when written?
        published_epoch_gmt = int(datetime.datetime.now().strftime("%s"))

        # push the sample article to the user's gist on github (published in this context means date published)
        template_val = {
            "username": social_user.uid,
            "title": title,
            "summary": summary,
            "published": published_epoch_gmt,
            "type": article_type,
        }

        # build a dict of files we want to push into the gist
        files = {
            config.gist_article_manifest_name: self.jinja2.render_template("blog/gist_manifest_stub.txt", **template_val),
            config.gist_article_markdown_name: self.jinja2.render_template("blog/gist_markdown_stub.txt", **template_val)
        }

        # loop through them and add them to the other JSON values for github
        file_data = dict((filename, {'content': text}) for filename, text in files.items())
        data = json.dumps({'description': "%s for TinyProbe" % title, 'files': file_data})

        # stuff it to github and then grab our gist_id
        gist = github.put_user_gist(social_user.access_token, data)
        gist_id = gist['id']

        # prep the slug
        slug = utils.slugify(title)
        
        # make sure it's not already in the database (unlikely)
        if not models.Article.get_by_user_and_gist_id(user_info.key, gist_id):
            # save the article in our database            
            article = models.Article(
                title = title,
                summary = summary,
                created = datetime.datetime.fromtimestamp(published_epoch_gmt),
                gist_id = gist_id,
                owner = user_info.key,
                slug = slug,
                article_type = article_type,
            )
            article.put()

            self.add_message(_('Article "%s" successfully created!' % title), 'success')
            return self.redirect_to('blog-article-list')
        else:
            # put_user_article call in models.py
            self.add_message(_('Article was not created.  Something went horribly wrong somewhere!' % name), 'warning')
            return self.get()
	
    @webapp2.cached_property
    def form(self):
        return forms.BlogArticleForm(self)


class BlogArticleListHandler(BaseHandler):
    @user_required
    def get(self):
        # pull the github token out of the social user db
        user_info = models.User.get_by_id(long(self.user_id))
        social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')

        # what do we do if we don't have a token or association?  auth 'em!
        if not social_user:
            scope = 'gist'
            # drop a short lived cookie so we know where to come back to when we're done auth'ing
            utils.write_cookie(self, 'oauth_return_url', 'user-profile', '/', 15)
            github_helper = github.GithubAuth(scope)
            self.redirect( github_helper.get_authorize_url() )
            return
        else:
            articles = models.Article.get_by_user(user_info.key)

            if not articles:
                # no articles, no problem, make one
                params = {}
                return self.redirect_to('blog-article-create', **params)
            else:
                # setup channel to do page refresh in case they sync
                channel_token = user_info.key.urlsafe()
                refresh_channel = channel.create_channel(channel_token)
                params = {
                    'articles': articles, 
                    'refresh_channel': refresh_channel, 
                    'channel_token': channel_token, 
                }
                return self.render_template('blog/blog_article_list.html', **params)


###################
# Utility Methods #
###################
class BlogClearCacheHandler(BaseHandler):
    @user_required
    def get(self, article_id=None):
        user_info = models.User.get_by_id(long(self.user_id))
        article = models.Article.get_by_id(long(article_id))

        if article.owner == user_info.key and github.flush_raw_gist_content(article.gist_id):
            message = 'Article was flushed from cache.'
        else:
            message = 'Something went wrong flushing from cache!'
        
        return message


# special class for routing menu in base.html template when user is logged in or logged out
# apparently using non-existant variables in uri_for() call (even when in a template if statement)
# causes some sort of appengine bug to manifest itself, causes it to crash hard, and leave
# a half-running zombie dev webserver process in place which has to be manually killed
class BlogUserMenuHandler(BaseHandler):
    @user_required
    def get(self, menu_id=None):
        user_info = models.User.get_by_id(long(self.user_id))

        if menu_id == 'newarticle':
            return self.redirect_to('blog-article-create')
        elif menu_id == 'myarticles':
            return self.redirect_to('blog-article-list')
        elif menu_id == 'mystack':
            return self.redirect_to('blog-user')
        else:
            return self.redirect_to('home')


# JOB SCHEDULER
# schedule a job request for rebuilding user's articles from their github gists
class BlogRefreshHandler(BaseHandler):
    # this function is called below, in the GET method for this handler
    def task(self, user=None, channel_token=None):
        # use both token and user to schedule job for updating user's articles from github gists
        params = {'channel_token': channel_token, 'user': user, 'job_token': config.job_token}
        t = taskqueue.add(method='GET', url='/blog/buildlist/', params=params, transactional=True)
        return

    # user pushed article refresh/rebuild button on article list page
    @user_required
    def get(self):
        # refresh_token gets passed in URL and we use the current logged in user to start a job
        channel_token = self.request.get('channel_token')
        user = self.user_id
        logging.info(user)
        db.run_in_transaction(self.task, user, channel_token)
        return


# JOB HANDLER
# handle a job request for rebuilding a user's articles from their github gists
class BlogBuildListHandler(BaseHandler):
    def get(self):
        # pull the github token out of the social user db and grab gists from github
        if self.request.get('job_token') != config.job_token:
            logging.info("Hacker attack on jobs!")
            return
        else: 
            user_info = models.User.get_by_id(long(self.request.get('user')))
            social_user = models.SocialUser.get_by_user_and_provider(user_info.key, 'github')
            gists = github.get_article_gists(social_user.uid, social_user.access_token)

            # update with the gists
            for gist in gists:
                article = models.Article.get_by_user_and_gist_id(user_info.key, gist['gist_id'])

                if article:
                    # update existing article with new data
                    article.title = gist['title']
                    article.summary = gist['summary']
                    article.gist_id = gist['gist_id']
                    article.article_type = gist['article_type']
                    article.updated = datetime.datetime.fromtimestamp(gist['published'])
                else:
                    # we have a new article on our hands - insert
                    # prep the slug
                    slug = utils.slugify(gist['title'])
                    article = models.Article(
                        title = gist['title'],
                        summary = gist['summary'],
                        created = datetime.datetime.fromtimestamp(gist['published']),
                        gist_id = gist['gist_id'],
                        owner = user_info.key,
                        slug = slug,
                        article_type = gist['article_type'],
                    )
                
                # update
                article.put()

                # flush memcache copy just in case we had it
                github.flush_raw_gist_content(article.gist_id)
                                
            # use the channel to tell the browser we are done
            channel_token = self.request.get('channel_token')
            channel.send_message(channel_token, 'reload')
            return

    def post(self):
        self.get()
