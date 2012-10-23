from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb
import urllib, httplib2, simplejson
import config
import logging
import yaml

class User(User):
    """
    Universal user model. Can be used with App Engine's default users API,
    own auth or third party authentication methods (OpenID, OAuth etc).
    based on https://gist.github.com/kylefinley
    """

    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    username = ndb.StringProperty()
    name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    email = ndb.StringProperty()
    company = ndb.StringProperty()
    password = ndb.StringProperty()
    country = ndb.StringProperty()
    gravatar_url = ndb.StringProperty()
    activated = ndb.BooleanProperty(default=False)
    
    @classmethod
    def get_by_email(cls, email):
        """Returns a user object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A user object.
        """
        return cls.query(cls.email == email).get()

    def get_social_providers_names(self):
        social_user_objects = SocialUser.get_by_user(self.key)
        result = []
        for social_user_object in social_user_objects:
            result.append(social_user_object.provider)
        return result

    def get_social_providers_info(self):
        providers = self.get_social_providers_names()
        result = {'used': [], 'unused': []}
        for k,v in SocialUser.PROVIDERS_INFO.items():
            if k in providers:
                result['used'].append(v)
            else:
                result['unused'].append(v)
        return result


class LogVisit(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    uastring = ndb.StringProperty()
    ip = ndb.StringProperty()
    timestamp = ndb.StringProperty()


class LogEmail(ndb.Model):
    sender = ndb.StringProperty(
        required=True)
    to = ndb.StringProperty(
        required=True)
    subject = ndb.StringProperty(
        required=True)
    body = ndb.TextProperty()
    when = ndb.DateTimeProperty()


class SocialUser(ndb.Model):
    PROVIDERS_INFO = { # uri is for OpenID only (not OAuth)
        'google': {'name': 'google', 'label': 'Google', 'uri': 'gmail.com'},
        'github': {'name': 'github', 'label': 'Github', 'uri': ''},
        'twitter': {'name': 'twitter', 'label': 'Twitter', 'uri': ''},
    }

    user = ndb.KeyProperty(kind=User)
    provider = ndb.StringProperty()
    uid = ndb.StringProperty()
    access_token = ndb.StringProperty()
    extra_data = ndb.JsonProperty()

    @classmethod
    def get_by_user(cls, user):
        return cls.query(cls.user == user).fetch()

    @classmethod
    def get_by_user_and_provider(cls, user, provider):
        return cls.query(cls.user == user, cls.provider == provider).get()

    @classmethod
    def get_by_provider_and_uid(cls, provider, uid):
        return cls.query(cls.provider == provider, cls.uid == uid).get()

    @classmethod
    def check_unique_uid(cls, provider, uid):
        # pair (provider, uid) should be unique
        test_unique_provider = cls.get_by_provider_and_uid(provider, uid)
        if test_unique_provider is not None:
            return False
        else:
            return True
    
    @classmethod
    def check_unique_user(cls, provider, user):
        # pair (user, provider) should be unique
        test_unique_user = cls.get_by_user_and_provider(user, provider)
        if test_unique_user is not None:
            return False
        else:
            return True

    @classmethod
    def check_unique(cls, user, provider, uid):
        # pair (provider, uid) should be unique and pair (user, provider) should be unique    
        return cls.check_unique_uid(provider, uid) and cls.check_unique_user(provider, user)
    
    @staticmethod
    def open_id_providers():
        return [k for k,v in SocialUser.PROVIDERS_INFO.items() if v['uri']]

class App(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    owner = ndb.KeyProperty(kind=User)
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    preview = ndb.StringProperty()
    command = ndb.StringProperty()
    gist_id = ndb.StringProperty()
    activated = ndb.BooleanProperty(default=True)
    public = ndb.BooleanProperty(default=True)

    @classmethod
    def get_public(cls):
        pass


    @classmethod
    def get_by_user_and_command(cls, user, command):
        return cls.query(cls.owner == user, cls.command == command).get()


    @classmethod
    def put_user_app(self, access_token, body):
        try:
            # stuff that sucker to github
            params = {'access_token': access_token}
            base_uri = 'https://api.github.com/gists'
            uri = '%s?%s' % (base_uri, urllib.urlencode(params))
            http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
            headers, content = http.request(uri, method='POST', body=body, headers=None)

            # check github said it made it ok
            logging.info("value is: %s" % content)
            return simplejson.loads(content)
        except:
            return False


    @classmethod
    def get_user_apps(self, github_user, access_token):
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

                    # stuff it onto apps list
                    apps.append({'name': manifest['name'], 'description': manifest['description'], 'url': gist['html_url']})
                
                except:
                    # gist didn't have a tinyprobe.manifest file - so sad
                    pass

            return apps
 
        except:
            pass
            # TODO do somthing if getting the gists fails
            



