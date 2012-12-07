#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Aeffect Server"""

import os
import aeffect

#Tornadooo
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.gen

#JSON
import json


#El Mongo
import pymongo
import bson
import bson.json_util

#Tornado based MongoDB connector
import motor

#Sessions and Cache
import redis
import tornadoredis
import pycket
import pycket.session
import pycket.notification

#Markdown
import markdown

#The fun stuff
import geohash
from osgeo import gdal
import osgeo.ogr
import osgeo.osr

WGS_84 = osgeo.osr.SpatialReference()
WGS_84.ImportFromEPSG(4326)

PRECISION = 7 #.. Yeah.. that happen.
SEGMENT_PRECISION = 0.0001 #not good enough for 8
BUFFER_PRECISION = 0.0001 # not good enough for 8
################################################################################
## CACHES

# These are above and beyond redis..  Objects that need to be super fast

REGION_CACHE = []
REGION_ID_MAP = {}
REGION_SLUG_MAP = {}
REGION_INC = 0

################################################################################
## ┏┓ ┏━┓┏━┓┏━╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣┻┓┣━┫┗━┓┣╸ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━┛╹ ╹┗━┛┗━╸╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class BaseHandler(tornado.web.RequestHandler, pycket.session.SessionMixin, pycket.notification.NotificationMixin):

    def update_pages(self, inbounder, oid):
        mongodb = self.settings['mongodb']
        inbound_dir = os.path.join(self.settings['inbound_path'], inbounder, 'pages')

        try:
            os.makedirs(inbound_dir)
        except:
            pass

        if not os.path.exists(os.path.join(inbound_dir, 'DELETE_TO_UPDATE')):

            open(os.path.join(inbound_dir, 'DELETE_TO_UPDATE'), 'w').write('')

            try:
                files = os.listdir(inbound_dir)
            except:
                files = []
            for f in files:
                try:
                    content = open(os.path.join(inbound_dir, f)).read()
                except:
                    content = ''

                if content:
                    mongodb.pages.update(
                        {'user._id': oid, 'type': f},
                        {'$set': {'data': markdown.markdown(content)}}
                    )
            
    def update_region_cache(self):
        global REGION_CACHE
        global REGION_ID_MAP
        global REGION_SLUG_MAP
        global REGION_INC
        import time
        mongodb = self.settings['mongodb']
        redisdb = self.settings['redisdb']
        regionkey = self.settings['regionkey']
        #redisdb.setnx(regionkey, 0)
        cacheinc = redisdb.get(regionkey)
        setted = cacheinc > REGION_INC

        if setted:
            REGION_INC = cacheinc
            #make thread safe FIXME
            REGION_CACHE = []
            REGION_ID_MAP = {}
            REGION_SLUG_MAP = {}
            for region in mongodb.regions.find():
                REGION_CACHE.append(region)
                REGION_ID_MAP[region['_id']] = region
                REGION_SLUG_MAP[region['slug']] = region

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
        self.write(unicode(status_code))
        return

################################################################################
## ┏┳┓┏━┓╻┏┓╻╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┃┃┃┣━┫┃┃┗┫┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ╹ ╹╹ ╹╹╹ ╹╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class MainHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        motordb = self.settings['motordb']
        self.session.set('foo', ['bar', 'baz'])
        self.update_pages(self.settings['siteuserinbounder'], self.settings['siteuser'])

        content_html = yield motor.Op(motordb.pages.find_one, {
                            'user._id': self.settings['siteuser'],
                            'type': 'site',
                        })
        
        self.render('index.html', content_html = content_html['data'], all_regions={'Testing': []}, state = "Alaska" , region_slug = "", region_name = "")

################################################################################
## ┏━┓┏━╸┏━╸╻┏━┓┏┓╻╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣┳┛┣╸ ┃╺┓┃┃ ┃┃┗┫┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ╹┗╸┗━╸┗━┛╹┗━┛╹ ╹╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class RegionHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, region_slug):
        global REGION_CACHE
        global REGION_ID_MAP
        global REGION_SLUG_MAP
        global REGION_INC
        motordb = self.settings['motordb']

        self.session.set('foo', ['bar', 'baz'])

        self.update_region_cache()

        region = REGION_SLUG_MAP[region_slug]

        self.update_pages(region['slug'], region['_id'])

        content_html = ''

        self.render('region.html', content_html = content_html, all_regions={'Testing': []}, state = "Alaska", envelope=region['geom']['envelope'] , region_slug = region_slug, region = region, pretty_region = bson.json_util.dumps(region, indent=2))

################################################################################
## ╻  ┏━┓┏━╸╻┏┓╻┏━╸┏━┓┏━┓┏┳┓
## ┃  ┃ ┃┃╺┓┃┃┗┫┣╸ ┃ ┃┣┳┛┃┃┃
## ┗━╸┗━┛┗━┛╹╹ ╹╹  ┗━┛╹┗╸╹ ╹

class LoginHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        self.session.set('foo', ['bar', 'baz'])
        self.render('login.html')

################################################################################
## ╻  ┏━┓┏━╸┏━┓╻ ╻╺┳╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┃  ┃ ┃┃╺┓┃ ┃┃ ┃ ┃ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━╸┗━┛┗━┛┗━┛┗━┛ ╹ ╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class LogoutHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        self.session.set('foo', ['bar', 'baz'])
        self.render('login.html')

################################################################################
##  ┏┓┏━┓┏━┓┏┓╻╺┳╸┏━╸┏━┓╺┳╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
##   ┃┗━┓┃ ┃┃┗┫ ┃ ┣╸ ┗━┓ ┃ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━┛┗━┛┗━┛╹ ╹ ╹ ┗━╸┗━┛ ╹ ╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class JSONTestHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        global REGION_CACHE
        global REGION_ID_MAP
        global REGION_SLUG_MAP
        global REGION_INC
        motordb = self.settings['motordb']
        print 'processing request'
        ### Process Bounds and Center arguments

        view_bounds_str = self.get_argument("bounds")
        view_center_str = self.get_argument("center")
        view_zoom_str = self.get_argument("zoom")
        view_zoom = int(view_zoom_str)

        if not view_bounds_str or not view_center_str:
            self.write([])
            self.finish()
            return

        view_bounds_south, view_bounds_west, view_bounds_north, view_bounds_east = [float(x) for x in view_bounds_str.split(',')]

        view_center_lat, view_center_long = [float(x) for x in view_center_str.split(',')]

        view_bounds_width = abs(view_bounds_north - view_bounds_south)
        view_bounds_height = abs(view_bounds_east - view_bounds_west)

        #Do not use spacial reference system so that calculations are faster.. not needed 
        view_bounds_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_north)
        view_bounds_ring.AddPoint(view_bounds_east, view_bounds_north)
        view_bounds_ring.AddPoint(view_bounds_east, view_bounds_south)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_south)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_north)

        view_bounds_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)

        view_bounds_geom.AddGeometry(view_bounds_ring)
        view_bounds_area = view_bounds_geom.Area()
        
        view_center_hash = geohash.encode(view_center_lat, view_center_long, precision=32)

        ###print "VIEW %.64f" % view_bounds_area

        possible_hashes = set(list('0123456789bcdefghjkmnpqrstuvwxyz'))

        if view_zoom == 5: end_precision = 0
        if view_zoom == 6: end_precision = 0
        if view_zoom == 7: end_precision = 1
        if view_zoom == 8: end_precision = 2
        if view_zoom == 9: end_precision = 2
        if view_zoom == 10: end_precision = 3
        if view_zoom == 11: end_precision = 4
        if view_zoom == 12: end_precision = 5
        if view_zoom == 13: end_precision = 6
        if view_zoom == 14: end_precision = 6
        if view_zoom == 15: end_precision = 7

        end_precision = (view_zoom / 3) #perfect
        if end_precision > PRECISION:
            end_precision = PRECISION
        if end_precision < 0:
            end_precision = 0

        if view_zoom < 8:
            end_precision = 0
        ##print end_precision, '!!!'

        for precision in range(1,end_precision+1):
            new_possible_hashes = set([])

            for possible_hash in possible_hashes:
                possible_hash_bbox = geohash.bbox(possible_hash)
                #Do not use spacial reference system
                possible_hash_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
                possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
                possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['n'])
                possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['s'])
                possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['s'])
                possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
            
                possible_hash_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
            
                possible_hash_geom.AddGeometry(possible_hash_ring)

                possible_hash_geom_intersection = view_bounds_geom.Intersection(possible_hash_geom)
                possible_hash_area = possible_hash_geom_intersection.Area()

                if possible_hash_area or view_center_hash.startswith(possible_hash):
                    ##print "!!!!", possible_hash, view_center_hash
                    for hash_char in '0123456789bcdefghjkmnpqrstuvwxyz':
                        new_possible_hashes.add(possible_hash + hash_char)

            possible_hashes = new_possible_hashes


        new_possible_hashes = set([])
        new_possible_grandparent_hashes = set([])

        for possible_hash in possible_hashes:
            possible_hash_bbox = geohash.bbox(possible_hash)
            #Do not use spacial reference system
            possible_hash_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
            possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
            possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['n'])
            possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['s'])
            possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['s'])
            possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
        
            possible_hash_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
        
            possible_hash_geom.AddGeometry(possible_hash_ring)

            possible_hash_geom_intersection = view_bounds_geom.Intersection(possible_hash_geom)
            possible_hash_area = possible_hash_geom_intersection.Area()

            if possible_hash_area or view_center_hash.startswith(possible_hash):
                new_possible_hashes.update(geohash.expand(possible_hash))
                new_possible_grandparent_hashes.add(possible_hash[0:-1])

        possible_hashes = new_possible_hashes


        centroids = []

        for hash in sorted(list(possible_hashes)):
            _lat, _long = geohash.decode(hash)
            centroids.append({
                'hash': hash,
                'arg': True,
                'lat': _lat,
                'long': _long,
            })

        lots = []
        regions = []
        region_set = set([])

        query = {'parent': {'$in': list(possible_hashes)}}
        cursor = motordb.lots.find(query)
        print query

        self.update_region_cache()

        while (yield cursor.fetch_next):
            lot = cursor.next_object()
            lot['lot'] = True
            lot['bbox'] = geohash.bbox(lot['hash'])
            region_set.add(lot['region']['_id'])
            lots.append(lot)

        for region_oid in region_set:
            region = REGION_ID_MAP[region_oid]
            region['region'] = True
            regions.append(region)

        #print len(lots), region_set

        self.write(bson.json_util.dumps(regions + lots))
        self.finish()
        return

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

    inbound_path = os.path.join(os.path.dirname(__file__), "../inbound")
        
    motordb = motor.MotorConnection(mongodburi).open_sync().ace
    mongodb = pymongo.Connection(mongodburi).ace
    tornadoredisdb = tornadoredis.Client()
    redisdb = redis.Redis()
    
    application = tornado.web.Application(
        handlers = [
            tornado.web.URLSpec(r"/static/(.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(stylesheets/.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(images/.*)", tornado.web.StaticFileHandler, static_path_dict),
            tornado.web.URLSpec(r"/(javascripts/.*)", tornado.web.StaticFileHandler, static_path_dict),
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
            tornado.web.URLSpec(r"/jsontest$", JSONTestHandler),
            tornado.web.URLSpec(r"/region/(.*)", RegionHandler),
            tornado.web.URLSpec(r"/login$", LoginHandler),
            tornado.web.URLSpec(r"/logout$", LogoutHandler),
            tornado.web.URLSpec(r"/$", MainHandler, name='index'),
            tornado.web.URLSpec(r"/(.*)", PageErrorHandler, kwargs=dict(error=404)),
        ],
        **{          
            'template_path': template_path,
            'static_path': static_path,
            'inbound_path': inbound_path,
            'cookie_secret': 'cookiemonster',
            'xsrf_cookies': True,
            'debug': True, #FIXME
            'login_url': '/login',
            'mongodb': mongodb,
            'motordb': motordb,
            'tornadoredisdb': tornadoredisdb,
            'redisdb': redisdb,
            'siteuser': bson.ObjectId('50bb047f17a78f9c422b45da'),
            'siteuserinbounder': 'webmaster',
            'regionkey': 'aceregion', #Removed when a region is modified so that each and every instance of Tornado replenishes its region cache.
            'pycket': {
                'engine': 'redis',
                'storage': {
                    'host': 'localhost',
                    'port': 6379,
                    'db_sessions': 10,
                    'db_notifications': 11,
                },
                'cookies': {
                    'expires_days': 120,
                },
            },
        }
    )


    server = tornado.httpserver.HTTPServer(application, xheaders=True)
    server.listen(8080)

    tornado.ioloop.IOLoop.instance().start()


