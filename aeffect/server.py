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
import bson.json_util

#Sessions and Cache
import redis
import tornadoredis
import pycket
import pycket.session
import pycket.notification

import json

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
        self.render('index.html')

################################################################################

class JSONTestHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        db = self.settings['mongodb']

        ### Process Bounds and Center arguments

        view_bounds_str = self.get_argument("bounds")
        view_center_str = self.get_argument("center")

        if not view_bounds_str or not view_center_str:
            self.write([])
            self.finish()
            return

        view_bounds_south, view_bounds_west, view_bounds_north, view_bounds_east = [float(x) for x in view_bounds_str.split(',')]

        view_center_lat, view_center_long = [float(x) for x in view_center_str.split(',')]

        view_bounds_width = abs(view_bounds_north - view_bounds_south)
        view_bounds_height = abs(view_bounds_east - view_bounds_west)

        #So not use spacial reference system
        view_bounds_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_north)
        view_bounds_ring.AddPoint(view_bounds_east, view_bounds_north)
        view_bounds_ring.AddPoint(view_bounds_east, view_bounds_south)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_south)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_north)

        view_bounds_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)

        view_bounds_geom.AddGeometry(view_bounds_ring)
        view_bounds_area = view_bounds_geom.Area()
        print "VIEW %.64f" % view_bounds_area

        #Nibble method.  Iterate over all geohashes for t

        view_center_hash = geohash.encode(view_center_lat, view_center_long, precision=PRECISION+2)

        print view_center_hash
        hash_parents = set([])
        hash_parents_area = 0

        for precision in range(PRECISION,0,-1):

            if hash_parents_area >= view_bounds_area:
                print "YIIBA"
                break

            hash_at_precision = view_center_hash[0:precision]

            hash_parents = set([hash_at_precision])
            hash_parents_area = 0

            for hps in range(8): #iterate out 4 times.. possibly need to move view bounds to match with hash centroid
                for hash_parent in list(hash_parents):
                    hash_parents.update(geohash.expand(hash_parent))

            for hash_parent in list(hash_parents):
                hash_parent_bbox = geohash.bbox(hash_parent)

                #So not use spacial reference system
                hash_parent_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
                hash_parent_ring.AddPoint(hash_parent_bbox['w'], hash_parent_bbox['n'])
                hash_parent_ring.AddPoint(hash_parent_bbox['e'], hash_parent_bbox['n'])
                hash_parent_ring.AddPoint(hash_parent_bbox['e'], hash_parent_bbox['s'])
                hash_parent_ring.AddPoint(hash_parent_bbox['w'], hash_parent_bbox['s'])
                hash_parent_ring.AddPoint(hash_parent_bbox['w'], hash_parent_bbox['n'])
            
                hash_parent_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
            
                hash_parent_geom.AddGeometry(hash_parent_ring)

                hash_parent_geom_intersection = view_bounds_geom.Intersection(hash_parent_geom)
                hash_parent_area = hash_parent_geom_intersection.Area()

                if hash_parent_area:
                    print "EAT", hash_parent
                    hash_parents_area += hash_parent_area
                    hash_parents.add(hash_parent)
                #else:
                #    hash_parents.discard(hash_parent)

            print "HASH %.64f" % hash_parents_area, view_bounds_area - 0.001, precision

        hash_parents = set([hp[0:PRECISION-1] for hp in list(hash_parents)])
        print hash_parents           
        centroids = []
     
        for hash in hash_parents:
            _lat, _long = geohash.decode(hash)
            centroids.append({
                'hash': hash,
                'arg': True,
                'lat': _lat,
                'long': _long,                
            })

        centroids = []
        #self.write(bson.json_util.dumps(centroids))
        #self.finish()
        #return

        #print lat, long
        #for precision in range(1, ): #Calculate up to 10th precision if needed
        #
        #    _lat, _long, _lat_delta, _long_delta = geohash.decode_exactly(geohash.encode(lat, long, precision=precision))
        #
        #    geohash_center = geohash.encode(lat, long, precision=precision)
        #
        #    #If the area of the center geohash at this precision is greater than the boundary area?... If so we can do evil.
        #    if ((_lat_delta * 2) * (_long_delta * 2)) < width * height:
        #        break            

        query = {'parent': {'$in': list(hash_parents)}}
        print query
        cursor = db.lots.find(query)

        lots = []

        region_set = set([])

        while (yield cursor.fetch_next):
            lot = cursor.next_object()
            lot['lot'] = True
            lot['bbox'] = geohash.bbox(lot['hash'])
            lot['geom']['outline'] = json.loads(osgeo.ogr.Geometry(wkb=lot['geom']['outline']).ExportToJson())
            region_set.add(lot['region']['_id'])
            lots.append(lot)
            print lot['region']['_id'], lot['hash'], lot['geom']['outline']['type']

        print len(lots), region_set

        self.write(bson.json_util.dumps(lots + centroids))
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


