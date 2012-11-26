#!/usr/bin/env python
##
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'Kord Campbell'
__website__ = 'http://www.tinyprobe.com'

import config
import urllib, httplib2, simplejson, yaml
import lib.github.oauth_client as oauth2
from google.appengine.api import memcache
import logging

# Github OAuth Implementation
class GithubAuth(object):
    
    def __init__(self, scope, next_page=''):

        # load github shizzle from config.py
        self.oauth_settings = {
            'client_id': config.github_client_id,
            'client_secret': config.github_client_secret,
            'access_token_url': 'https://%s/login/oauth/access_token' % config.github_server,
            'authorization_url': 'https://%s/login/oauth/authorize' % config.github_server,
            'redirect_url': '%s' % config.github_redirect_uri,
            'scope': '%s' % scope,
        }

    # get our auth url and return to login handler
    def get_authorize_url(self):
        oauth_client = oauth2.Client2( 
            self.oauth_settings['client_id'], 
            self.oauth_settings['client_secret'], 
            self.oauth_settings['authorization_url'] 
        )
        
        authorization_url = oauth_client.authorization_url( 
            redirect_uri=self.oauth_settings['redirect_url'],  
            params={'scope': self.oauth_settings['scope']}
        )

        return authorization_url

    def get_access_token(self, code):
        oauth_client = oauth2.Client2(
            self.oauth_settings['client_id'],
            self.oauth_settings['client_secret'],
            self.oauth_settings['access_token_url']
        )
        
        data = oauth_client.access_token(code, self.oauth_settings['redirect_url'])
        
        access_token = data.get('access_token')

        return access_token


    def get_user_info(self, access_token):

        oauth_client = oauth2.Client2(
            self.oauth_settings['client_id'],
            self.oauth_settings['client_secret'],
            self.oauth_settings['access_token_url']
        )

        (headers, body) = oauth_client.request(
            'https://api.github.com/user',
            access_token=access_token,
            token_param='access_token'
        )
        
        return simplejson.loads(body)


def get_user_gists(github_user, access_token):
    params = {'access_token': access_token}
    base_uri = 'https://api.github.com/users/%s/gists' % github_user
    uri = '%s?%s' % (base_uri, urllib.urlencode(params))
    
    try:
        # request data from github gist API
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='GET', body=None, headers=None)
        gists = simplejson.loads(content)

        # transform gists into apps
        apps = []
        for gist in gists:
            try:
                # grab the raw file and parse it for yaml bits
                if gist['files'][config.gist_manifest_name]['raw_url']:
                    headers, content = http.request(gist['files'][config.gist_manifest_name]['raw_url'])
                    manifest = yaml.load(content)
                    logging.info("value is: %s" % manifest)
                logging.info("value is: %s" % gist)
                # stuff it onto apps list
                apps.append({
                    'name': manifest['name'],
                    'command': manifest['command'],
                    'preview': manifest['preview'],
                    'gist_id': gist['id'],
                    'description': manifest['description'],
                    'url': gist['html_url'],
                })
            
            except:
                # gist didn't have a tinyprobe.manifest file - so sad
                pass

        return apps

    except:
        pass
        # TODO do somthing if getting the gists fails


def get_article_gists(github_user, access_token):
    params = {'access_token': access_token}
    base_uri = 'https://api.github.com/users/%s/gists' % github_user
    uri = '%s?%s' % (base_uri, urllib.urlencode(params))
    
    try:
        # request data from github gist API
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='GET', body=None, headers=None)
        gists = simplejson.loads(content)

        # transform gists into articles
        articles = []
        for gist in gists:
            try:
                # grab the raw file and parse it for yaml bits
                if gist['files'][config.gist_article_manifest_name]['raw_url']:
                    headers, content = http.request(gist['files'][config.gist_article_manifest_name]['raw_url'])
                    manifest = yaml.load(content)

                # stuff it onto article list
                articles.append({
                    'title': manifest['title'], 
                    'summary': manifest['summary'], 
                    'published': manifest['published'],
                    'article_type': manifest['type'],
                    'gist_id': gist['id'],
                })
            
            except:
                # gist didn't have a .manifest file - so sad
                pass

        return articles

    except:
        pass
        # TODO do somthing if getting the gists fails


def get_raw_gist_content(gist_id):
    markdown = memcache.get('%s:markdown' % gist_id)
    if markdown is not None:
        return markdown
    else:
        # go fetch the current raw url from the gist_id
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request('https://api.github.com/gists/%s' % gist_id, method='GET', body=None, headers=None)
        gist = simplejson.loads(content)

        # if we find files, great!
        if True:
            gist_markdown_url = gist['files'][config.gist_article_markdown_name]['raw_url']
            # use that raw url to load the content and stuff it into memcache for an hour
            http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
            headers, markdown = http.request(gist_markdown_url, method='GET', headers=None)
            if not memcache.add('%s:markdown' % gist_id, markdown, config.memcache_expire_time):
                markdown = ""
                logging.info("memcache add of content from gist %s failed." % gist_id)

            return markdown
        if False:
            logging.info("value is: %s" % "yeah, we're here alright")
            return False


def flush_raw_gist_content(gist_id):
    if memcache.delete('%s:markdown' % gist_id):
        logging.info("flushed cache!")
        return True
    else:
        logging.info("didn't flush cache!")
        return False


def put_user_gist(access_token, body):
    try:
        # stuff that sucker to github
        params = {'access_token': access_token}
        base_uri = 'https://api.github.com/gists'
        uri = '%s?%s' % (base_uri, urllib.urlencode(params))
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='POST', body=body, headers=None)

        # check github said it made it ok
        return simplejson.loads(content)
    except:
        return False


def delete_user_gist(access_token, gist_id):
    try:
        # stuff that sucker to github
        params = {'access_token': access_token}
        base_uri = 'https://api.github.com/gists/%s' % gist_id
        uri = '%s?%s' % (base_uri, urllib.urlencode(params))
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='DELETE', headers=None)        
    except:
        return False



