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

#JSON
import json

#Tornado based MongoDB connector
import motor
import bson.json_util

#Sessions and Cache
import redis
import tornadoredis
import pycket
import pycket.session
import pycket.notification


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
        self.session.set('foo', ['bar', 'baz'])
        self.render('index.html', all_regions={'Testing': []}, state = "Alaska" , region_slug = "", region_name = "")

################################################################################
## ┏━┓┏━╸┏━╸╻┏━┓┏┓╻╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣┳┛┣╸ ┃╺┓┃┃ ┃┃┗┫┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ╹┗╸┗━╸┗━┛╹┗━┛╹ ╹╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class RegionHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, region_slug):
        db = self.settings['mongodb']

        self.session.set('foo', ['bar', 'baz'])

        query = {'slug': region_slug}

        region = yield motor.Op(db.regions.find_one, query)

        self.render('region.html', all_regions={'Testing': []}, state = "Alaska", envelope=region['geom']['envelope'] , region_slug = region_slug, region_name = region['name'])

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
        db = self.settings['mongodb']
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

        end_precision = (view_zoom / 3) - 1 #perfect
        if end_precision > PRECISION:
            end_precision = PRECISION
        if end_precision < 0:
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
        cursor = db.lots.find(query)
        print query
        while (yield cursor.fetch_next):
            lot = cursor.next_object()
            lot['lot'] = True
            lot['bbox'] = geohash.bbox(lot['hash'])
            region_set.add(lot['region']['_id'])
            lots.append(lot)

        query = {'_id': {'$in': list(region_set)}}
        cursor = db.regions.find(query)

        while (yield cursor.fetch_next):
            region = cursor.next_object()
            region['region'] = True
            ###print region
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
        
    mongodb = motor.MotorConnection(mongodburi).open_sync().ace
    cachedb = tornadoredis.Client()

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
            'cookie_secret': 'cookiemonster',
            'xsrf_cookies': True,
            'debug': True, #FIXME
            'login_url': '/login',
            'mongodb': mongodb,
            'cachedb': cachedb,
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


