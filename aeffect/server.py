#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""CarbonEffect Server"""

import os
import aeffect

#Tornadooo
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen

#Tornado based MongoDB connector
import motor

#Sessions and Cache
import redis
import tornadoredis
import pycket
import pycket.session
import pycket.notification


####################################
################################################################################
## ┏┓ ┏━┓┏━┓┏━╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣┻┓┣━┫┗━┓┣╸ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━┛╹ ╹┗━┛┗━╸╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class BaseHandler(tornado.web.RequestHandler, pycket.session.SessionMixin, pycket.notification.NotificationMixin):
    def get_current_user(self):
        return self.session.get('user')

    def get_current_user_full_name(self):
        try:
            full_name = u'%s %s' % (self.current_user['firstname'], self.current_user['lastname'])
        except:
            full_name = u'Anonynewb'
        return full_name.strip()

    def write_error(self, status_code, *args, **kwargs):
        import pprint
        pprint.pprint(args)
        pprint.pprint(kwargs)

        self.status_code = status_code
        self.exc_info = kwargs.get('exc_info')

        self.status_message = kwargs.get('msg')

        #self.render('base/error.html')
        self.write(status_code)
        return

################################################################################
## ┏┳┓┏━┓╻┏┓╻╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┃┃┃┣━┫┃┃┗┫┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ╹ ╹╹ ╹╹╹ ╹╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class MainHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        self.render('index.html')

################################################################################
## ┏━┓┏━┓┏━╸┏━╸┏━╸┏━┓┏━┓┏━┓┏━┓╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣━┛┣━┫┃╺┓┣╸ ┣╸ ┣┳┛┣┳┛┃ ┃┣┳┛┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ╹  ╹ ╹┗━┛┗━╸┗━╸╹┗╸╹┗╸┗━┛╹┗╸╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class PageErrorHandler(BaseHandler):
    def initialize(self, error):
        self.error = error

    def get(self, *args, **kwargs):
        self.send_error(self.error)

    def post(self, *args, **kwargs):
        self.send_error(self.error)


################################################################################
## ┏━┓┏━╸┏━┓╻ ╻┏━╸
## ┗━┓┣╸ ┣┳┛┃┏┛┣╸ 
## ┗━┛┗━╸╹┗╸┗┛ ┗━╸

def serve(listenuri, mongodburi):

    #TODO add RedisURI
    #TODO add Static Path setting
    static_path = os.path.join(os.path.dirname(__file__), "static")
    static_path_dict = dict(path=static_path)
    
    template_path = os.path.join(os.path.dirname(__file__), "templates")
        
    pycket_pool = redis.ConnectionPool(max_connections=1) #Find better session framework (With Async)

    mongodb = motor.MotorConnection(mongodburi).open_sync().test_database
    cachedb = tornadoredis.Client()

    application = tornado.web.Application(
        handlers = [
            tornado.web.URLSpec(r"/static/(.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(stylesheets/.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(images/.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(javascript/.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(favicon.ico)$", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(robots.txt)$", tornado.web.StaticFileHandler, static_path_dict),
            #tornado.web.URLSpec(r'/login$', AuthLoginHandler, name='login'),
            #tornado.web.URLSpec(r'/logout$', AuthLogoutHandler, name='logout'),
            #tornado.web.URLSpec(r'/dashboard/(?P<search_oid_str_or_request>\w{24})$', DashboardHandler, name='dashboard+search'),
            #tornado.web.URLSpec(r'/dashboard/(?P<search_oid_str_or_request>\w+)$', DashboardHandler, name='dashboard+newsearch'),
            #tornado.web.URLSpec(r'/dashboard$', DashboardHandler, name='dashboard'),
            #tornado.web.URLSpec(r'/search/(?P<search_oid_str>\w{24})/(?P<collection_oid_str>\w{24})$', SearchCollectionHandler, name='search+collection'),
            #tornado.web.URLSpec(r'/search/(?P<search_oid_str>\w{24})$', SearchAllHandler, name='search'),
            #tornado.web.URLSpec(r'/export/csv/(?P<search_oid_str>\w{24})/(?P<collection_oid_str>\w{24})$', ExportCSVSearchCollectionHandler, name='export+search+collection+csv'),
            #tornado.web.URLSpec(r'/api/document/batch$', APIDocumentBatchHandler),
            #tornado.web.URLSpec(r'/api/document/insert$', APIDocumentInsertHandler),
            #tornado.web.URLSpec(r'/api/document/link$', APIDocumentLinkHandler),
            #tornado.web.URLSpec(r"/$", tornado.web.RedirectHandler, kwargs=dict(url='/dashboard')), #Temporary pending main advert/news page
            tornado.web.URLSpec(r"/$", MainHandler, name='index'),
            tornado.web.URLSpec(r"/(.*)", PageErrorHandler, kwargs=dict(error=404)),
        ],          
        template_path = template_path,
        static_path = static_path,
        cookie_secret = 'cookiemonster',
        xsrf_cookies = True,
        debug = True, #FIXME
        login_url = '/login',
        pycket = {
                'engine': 'redis',
                'storage': {
                'connection_pool': pycket_pool,
                'db_sessions': 10,
                'db_notifications': 11,
            },
            'cookies': {
                'expires_days': 120,
            },
        },
        mongodb = mongodb,
        cachedb = cachedb,        
    )


    server = tornado.httpserver.HTTPServer(application, xheaders=True)
    server.listen(8080)

    tornado.ioloop.IOLoop.instance().start()


