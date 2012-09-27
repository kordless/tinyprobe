__version__ = "0.1"

"""
Provides a Pure Python Github API Interface.
"""
try:
    import sha
except DeprecationWarning, derr:
    import hashlib
    sha = hashlib.sha1

import urllib, time, random, httplib, hmac, binascii, cgi, string
from HTMLParser import HTMLParser

import logging

class OAuthError(Exception):
    """
    General OAuth exception, nothing special.
    """
    def __init__(self, value):
        self.parameter = value
        
    def __str__(self):
        return repr(self.parameter)


class Stripper(HTMLParser):
    """
    Stripper class that strips HTML entity.
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)
    
    def getAlteredData(self):
        return ''.join(self.fed)


class ConnectionError(Exception):
    pass

class Github(object):
    def __init__(self, api_key, api_secret, callback_url, gae = False):
        # Credientials
        self.API_ENDPOINT      = "api.github.com"
        self.BASE_URL          = "https://%s" % self.API_ENDPOINT
        self.VERSION           = "1.0"
        
        self._api_key       = api_key
        self._api_secret    = api_secret
        self._callback_url  = callback_url
        self._gae = gae # Is it google app engine
        self._request_token = None # that comes later
        self._access_token  = None # that comes later and later
        
        self._request_token_secret = None
        self._access_token_secret  = None
        
        self._verifier = None
        self._error    = None

    def request_token(self):
        """
        Performs the corresponding API which returns the request token in a query string
        The POST Querydict must include the following:
         * oauth_callback
         * oauth_consumer_key
         * oauth_nonce
         * oauth_signature_method
         * oauth_timestamp
         * oauth_version
        """
        self.clear()

        method = "GET"
        relative_url = "/uas/oauth/requestToken"
        
        query_dict = self._query_dict({"oauth_callback" : self._callback_url})
        
        self._calc_signature(self._get_url(relative_url), query_dict, self._request_token_secret, method)

        try:
            response = self._https_connection(method, relative_url, query_dict)
            logging.info(relative_url)
        except ConnectionError:
            return False
        
        oauth_problem = self._get_value_from_raw_qs("oauth_problem", response)
        if oauth_problem:
            self._error = oauth_problem
            return False

        self._request_token = self._get_value_from_raw_qs("oauth_token", response)
        self._request_token_secret = self._get_value_from_raw_qs("oauth_token_secret", response)
        return True

    def access_token(self, request_token = None, request_token_secret = None, verifier = None):
        """
        Performs the corresponding API which returns the access token in a query string
        According to the link (http://developer.linkedin.com/docs/DOC-1008), POST Querydict must include the following:
        * oauth_consumer_key
        * oauth_nonce
        * oauth_signature_method
        * oauth_timestamp
        * oauth_token (request token)
        * oauth_version
        """
        self._request_token = request_token and request_token or self._request_token
        self._request_token_secret = request_token_secret and request_token_secret or self._request_token_secret
        self._verifier = verifier and verifier or self._verifier
        # if there is no request token, fail immediately
        if self._request_token is None:
            raise OAuthError("There is no Request Token. Please perform 'request_token' method and obtain that token first.")

        if self._request_token_secret is None:
            raise OAuthError("There is no Request Token Secret. Please perform 'request_token' method and obtain that token first.")

        if self._verifier is None:
            raise OAuthError("There is no Verifier Key. Please perform 'request_token' method, redirect user to API authorize page and get the _verifier.")
        
        method = "GET"
        relative_url = "/uas/oauth/accessToken"
        query_dict = self._query_dict({
                    "oauth_token" : self._request_token,
                    "oauth_verifier" : self._verifier
                    })

        self._calc_signature(self._get_url(relative_url), query_dict, self._request_token_secret, method)

        try:
            response = self._https_connection(method, relative_url, query_dict)
        except ConnectionError:
            return False

        oauth_problem = self._get_value_from_raw_qs("oauth_problem", response)
        if oauth_problem:
            self._error = oauth_problem
            return False

        self._access_token = self._get_value_from_raw_qs("oauth_token", response)
        self._access_token_secret = self._get_value_from_raw_qs("oauth_token_secret", response)
        return True

    def get_authorize_url(self, request_token = None):
        self._request_token = request_token and request_token or self._request_token
        if self._request_token is None:
            raise OAuthError("OAuth Request Token is NULL. Please acquire this first.")
        return "%s%s?oauth_token=%s" % (self.BASE_URL, "/uas/oauth/authorize", self._request_token)

    def get_error(self):
        return self._error
    
    def clear(self):
        self._request_token = None
        self._access_token  = None
        self._verifier      = None

        self._request_token_secret = None
        self._access_token_secret = None
        
        self._error                   = None
        
    #################################################
    # HELPER FUNCTIONS                              #
    # You do not explicitly use those methods below #
    #################################################
    
    def _generate_nonce(self, length = 20):
        return ''.join([string.letters[random.randint(0, len(string.letters) - 1)] for i in range(length)])

    def _get_url(self, relative_path):
        return self.BASE_URL + relative_path
    
    def _generate_timestamp(self):
        return str(int(time.time()))
    
    def _quote(self, st):
        return urllib.quote(st, safe='~')

    def _utf8(self, st):
        return isinstance(st, unicode) and st.encode("utf-8") or str(st)

    def _urlencode(self, query_dict):
        keys_and_values = [(self._quote(self._utf8(k)), self._quote(self._utf8(v))) for k,v in query_dict.items()]
        keys_and_values.sort()
        return '&'.join(['%s=%s' % (k, v) for k, v in keys_and_values])

    def _get_value_from_raw_qs(self, key, qs):
        raw_qs = cgi.parse_qs(qs, keep_blank_values = False)
        rs = raw_qs.get(key)
        if type(rs) == list:
            return rs[0]
        else:
            return rs

    def _signature_base_string(self, method, uri, query_dict):
        return "&".join([self._quote(method), self._quote(uri), self._quote(self._urlencode(query_dict))])
        
    def _parse_error(self, str_as_xml):
        """
        Helper function in order to get error message from an xml string.
        In coming xml can be like this:
        <?xml VERSION='1.0' encoding='UTF-8' standalone='yes'?>
        <error>
         <status>404</status>
         <timestamp>1262186271064</timestamp>
         <error-code>0000</error-code>
         <message>[invalid.property.name]. Couldn't find property with name: first_name</message>
        </_error>
        """
        try:
            xmlDocument = minidom.parseString(str_as_xml)
            if len(xmlDocument.getElementsByTagName("error")) > 0: 
                error = xmlDocument.getElementsByTagName("message")
                if error:
                    error = error[0]
                    return error.childNodes[0].nodeValue
            return None
        except OAuthError, detail:
#            raise detail
            raise OAuthError("Invalid XML String given: error: %s" % repr(detail))
        
    def _create_oauth_header(self, query_dict):
        header = 'OAuth realm="http://api.github.com", '
        header += ", ".join(['%s="%s"' % (k, self._quote(query_dict[k]))
                           for k in sorted(query_dict)])
        return header
    
    def _query_dict(self, additional = {}):
        query_dict = {"oauth_consumer_key": self._api_key,
                      "oauth_nonce": self._generate_nonce(),
                      "oauth_signature_method": "HMAC-SHA1",
                      "oauth_timestamp": self._generate_timestamp(),
                      "oauth_version": self.VERSION
        }
        query_dict.update(additional)
        return query_dict
    
    def _do_normal_query(self, relative_url, body=None, method="GET", params=None):
        method = method
        query_dict = self._query_dict({"oauth_token" : self._access_token})
        signature_dict = dict(query_dict)
        
        if (params):
            signature_dict.update(params)
            
        query_dict["oauth_signature"] = self._calc_signature(self._get_url(relative_url),
                                    signature_dict, self._access_token_secret, method, update=False)
        
        if (params):
            relative_url = "%s?%s" % (relative_url, self._urlencode(params))
        
        response = self._https_connection(method, relative_url, query_dict, body)
        
        if (response):
            error = self._parse_error(response)
            if error:
                self._error = error
                raise ConnectionError()
        
        return response

    def _check_tokens(self):
        if self._access_token is None:
            self._error = "There is no Access Token. Please perform 'access_token' method and obtain that token first."
            raise OAuthError(self._error)
        if self._access_token_secret is None:
            self._error = "There is no Access Token Secret. Please perform 'access_token' method and obtain that token first."
            raise OAuthError(self._error)

    def _calc_key(self, token_secret):
        key = self._quote(self._api_secret) + "&"
        if (token_secret):
            key += self._quote(token_secret)
        return key

    def _calc_signature(self, url, query_dict, token_secret, method = "GET", update=True):
        query_string = self._quote(self._urlencode(query_dict))
        signature_base_string = "&".join([self._quote(method), self._quote(url), query_string])
        hashed = hmac.new(self._calc_key(token_secret), signature_base_string, sha)
        signature = binascii.b2a_base64(hashed.digest())[:-1]
        if (update):
            query_dict["oauth_signature"] = signature
        return signature
        
    def _https_connection(self, method, relative_url, query_dict, body=None):
        if (self._gae):
            return self._https_connection_gae(method, relative_url, query_dict, body)
        else:
            return self._https_connection_regular(method, relative_url, query_dict, body)
    
    def _https_connection_regular(self, method, relative_url, query_dict, body = None):
        header = self._create_oauth_header(query_dict)
        connection = None
        try:
            connection = httplib.HTTPSConnection(self.API_ENDPOINT)
            connection.request(method, relative_url, body = body,
                               headers={'Authorization':header})
            response = connection.getresponse()
            
            if response is None:
                self._error = "No HTTP response received."
                raise ConnectionError()
            return response.read()
        finally:
            if (connection):
                connection.close()
    
    def _https_connection_gae(self, method, relative_url, query_dict, body = None):
        from google.appengine.api import urlfetch
        if (method == "GET"):
            method = urlfetch.GET
        elif (method == "POST"):
            method = urlfetch.POST
        elif (method == "PUT"):
            method = urlfetch.PUT
        elif (method == "DELETE"):
            method = urlfetch.DELETE
        
        header = self._create_oauth_header(query_dict)
        headers = {'Authorization':header}
        if (body):
            headers["Content-Type"] = "text/xml"
        
        url = self._get_url(relative_url)

        rpc = urlfetch.create_rpc(deadline=10.0)
        urlfetch.make_fetch_call(rpc, url, method=method, headers=headers,
                             payload=body)
        
        return rpc.get_result().content
    
    ########################
    # END HELPER FUNCTIONS #
    ########################
