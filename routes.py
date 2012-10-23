"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""

from webapp2_extras.routes import RedirectRoute
from web import handlers
from web.users import userhandlers
from web.apps import apphandlers
from web.shell import shellhandlers

secure_scheme = 'https'

_routes = [
    # apps
    RedirectRoute('/apps/new/', apphandlers.AppsCreateHandler, name='apps-new', strict_slash=True),
    RedirectRoute('/apps/', apphandlers.AppsListHandler, name='apps', strict_slash=True),
    RedirectRoute('/apps/refresh/', apphandlers.AppsRefreshHandler, name='apps-refresh', strict_slash=True),
    RedirectRoute('/apps/<app_id>/', apphandlers.AppsDetailHandler, name='apps-detail', strict_slash=True),
    RedirectRoute('/apps/public/', apphandlers.AppsPublicHandler, name='apps-public', strict_slash=True),

    # shell
    RedirectRoute('/shell/', shellhandlers.ShellHandler, name='shell', strict_slash=True),

    # mail processing
    RedirectRoute('/taskqueue-send-email/', handlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    # user logins
    RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/social_login/<provider_name>', userhandlers.SocialLoginHandler, name='social-login', strict_slash=True),
    RedirectRoute('/social_login/<provider_name>/complete', userhandlers.CallbackSocialLoginHandler, name='social-login-complete', strict_slash=True),
    RedirectRoute('/social_login/<provider_name>/delete', userhandlers.DeleteSocialProviderHandler, name='delete-social-provider', strict_slash=True),

    # user registration
    RedirectRoute('/preregister/', userhandlers.PreRegisterHandler, name='preregister', strict_slash=True),
    RedirectRoute('/register/<encoded_email>/', userhandlers.RegisterHandler, name='register', strict_slash=True),

    # user settings
    RedirectRoute('/settings/profile', userhandlers.EditProfileHandler, name='edit-profile', strict_slash=True),
    RedirectRoute('/settings/password', userhandlers.EditPasswordHandler, name='edit-password', strict_slash=True),
    RedirectRoute('/settings/email', userhandlers.EditEmailHandler, name='edit-email', strict_slash=True),
    RedirectRoute('/password-reset/', userhandlers.PasswordResetHandler, name='password-reset', strict_slash=True),
    RedirectRoute('/password-reset/<user_id>/<token>', userhandlers.PasswordResetCompleteHandler, name='password-reset-check', strict_slash=True),
    RedirectRoute('/change-email/<user_id>/<encoded_email>/<token>/', userhandlers.EmailChangedCompleteHandler, name='email-changed-check', strict_slash=True),
    RedirectRoute('/secure/', userhandlers.SecureRequestHandler, name='secure', strict_slash=True),

    # website pages
    RedirectRoute('/', handlers.HomeRequestHandler, name='home', strict_slash=True),
    RedirectRoute('/product/', handlers.ProductHandler, name='product', strict_slash=True),
    RedirectRoute('/product/<product_page>/', handlers.ProductHandler, name='product-pages', strict_slash=True),
    RedirectRoute('/company/', handlers.ProductHandler, name='company', strict_slash=True),
    RedirectRoute('/company/<company_page>/', handlers.CompanyHandler, name='company-pages', strict_slash=True),
    RedirectRoute('/contact/', handlers.ContactHandler, name='contact', strict_slash=True),
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
