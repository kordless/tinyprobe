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
    admin = ndb.BooleanProperty(default=False)
    
    @classmethod
    def get_by_email(cls, email):
        return cls.query(cls.email == email).get()

    @classmethod
    def update_schema(cls):
        users = cls.query().fetch()
        for user in users:
            # put new schema objects in here to update all rows
            user.admin = False
            user.put()

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


# blog articles for admins only
class Article(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    owner = ndb.KeyProperty(kind=User)
    title = ndb.StringProperty()
    summary = ndb.StringProperty()
    url = ndb.StringProperty()
    slug = ndb.StringProperty()
    article_type = ndb.StringProperty()
    gist_id = ndb.StringProperty()
    draft = ndb.BooleanProperty(default=True)
    
    @classmethod
    def delete_by_user(cls, user):
        article_query = cls.query().filter(cls.owner == user)
        articles = article_query.fetch()
        keys = []
        for x in articles:
            keys.append(x.key)
        return ndb.delete_multi(keys)
    

    @classmethod
    def get_by_user_and_gist_id(cls, user, gist_id):
        # get() a single article by user/gist_id
        gist = cls.query(cls.owner == user, cls.gist_id == gist_id).get()
        logging.info("value is: %s" % gist)
        return gist


    @classmethod
    def get_all(cls):
        article_query = cls.query().filter().order(-Article.created)
        gists = article_query.fetch()
        return gists


    @classmethod
    def get_by_user(cls, user):
        article_query = cls.query().filter(cls.owner == user).order(-Article.created)
        gists = article_query.fetch()
        return gists

    @classmethod
    def get_by_user_and_type(cls, user, article_type):
        article_query = cls.query().filter(cls.owner == user, cls.article_type == article_type).order(-Article.created)
        gists = article_query.fetch()
        return gists

    @classmethod
    def get_by_slug(cls, slug):
        article_query = cls.query().filter(cls.slug == slug)
        gist = article_query.get()
        return gist


class App(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    name = ndb.StringProperty()
    command = ndb.StringProperty()
    description = ndb.StringProperty()
    thumb_url = ndb.StringProperty()
    gist_id = ndb.StringProperty()
    owner = ndb.KeyProperty(kind=User)
    author = ndb.KeyProperty(kind=User)
    github_author = ndb.StringProperty()
    activated = ndb.BooleanProperty(default=True)
    public = ndb.BooleanProperty(default=True)

    @classmethod
    def delete_by_user(cls, user):
        app_query = cls.query().filter(cls.owner == user)
        apps = app_query.fetch()
        keys = []
        for x in apps:
            keys.append(x.key)
        return ndb.delete_multi(keys)


    @classmethod
    def get_by_user_and_command(cls, user, command):
        # get() a single app by user/command
        gist = cls.query(cls.owner == user, cls.command == command).get()
        return gist


    @classmethod
    def get_by_user_and_gist_id(cls, user, gist_id):
        # get() a single app by user/gist_id
        gist = cls.query(cls.owner == user, cls.gist_id == gist_id).get()
        return gist

    @classmethod
    def get_by_user(cls, user):
        app_query = cls.query().filter(cls.owner == user).order(App.command)
        gists = app_query.fetch()
        return gists

    @classmethod
    def get_public(cls):
        app_query = cls.query().filter(cls.public == True).order(App.updated)
        gists = app_query.fetch()
        return gists

        
