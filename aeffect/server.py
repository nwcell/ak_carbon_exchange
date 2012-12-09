#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Aeffect Server"""

import os
import copy

import aeffect

import pprint

import urllib

#Tornadooo
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.httpclient
import tornado.gen

tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

import bcrypt
import wtforms

import stripe
stripe.api_key = "sk_test_7KLJuxL8t9huAIDkKROOxT8C"

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

################################################################################
## ┏┓ ┏━┓┏━┓┏━╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣┻┓┣━┫┗━┓┣╸ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━┛╹ ╹┗━┛┗━╸╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class BaseHandler(tornado.web.RequestHandler, pycket.session.SessionMixin, pycket.notification.NotificationMixin):

    def authorize_user(self, username, password):
        mongodb = self.settings['mongodb']
        result = mongodb.users.find_one(
            spec_or_id = {
                '$query': {
                    'email': username,
                    },
                '$returnKey': True
                },
            fields = {'email': 1, 'password': 1, '_id': 1}
            )

        if not result:
            return None

        if bcrypt.hashpw(password, result['password']) == result['password']:
            return result['_id']

        return None
    
    def update_pages(self, oid, extratouch=None):
        mongodb = self.settings['mongodb']
        inbound_dir = os.path.join(self.settings['inbound_path'], str(oid), 'pages')

        try:
            os.makedirs(inbound_dir)
        except:
            pass
        try:
            if extratouch:
                open(os.path.join(inbound_dir, extratouch), 'a')
        except:
            pass

        if not os.path.exists(os.path.join(inbound_dir, 'DELETE_TO_UPDATE')):

            ## open(os.path.join(inbound_dir, 'DELETE_TO_UPDATE'), 'w').write('') FIXME.. REMOVED FOR NOW

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
                    print mongodb.pages.update(
                        {'user._id': oid, 'type': f},
                        {'$set': {
                                'data': content,
                                #'data': markdown.markdown(content), #avoid for now
                                'type': f,
                                'user._id': oid,
                            }
                        },
                        upsert=True,
                    )
            
    def update_region_cache(self):
        import time
        mongodb = self.settings['mongodb']
        redisdb = self.settings['redisdb']
        regionkey = self.settings['cache']['region']['key']
        #redisdb.setnx(regionkey, 0)
        cacheinc = redisdb.get(regionkey)
        setted = cacheinc != self.settings['cache']['region']['stamp']

        sections = {
            'a-j': ('a','j'),
            'k': ('k','k'),
            'm-z': ('m','z'),
        }

        if setted:
            self.settings['cache']['region']['stamp'] = cacheinc
            #make thread safe FIXME
            self.settings['cache']['region']['array'] = []
            self.settings['cache']['region']['sectioned'] = {}
            self.settings['cache']['region']['map']['_id'] = {}
            self.settings['cache']['region']['map']['slug'] = {}
            for region in mongodb.regions.find():
                region['_section'] = 'misc'
                for s, r in sections.iteritems():
                    if region['name'][0].lower() >= r[0]:
                        if region['name'][0].lower() <= r[1]:
                            region['_section'] = s    

                self.settings['cache']['region']['array'].append(region)
                self.settings['cache']['region']['sectioned'].setdefault(region['_section'], []).append(region)
                self.settings['cache']['region']['map']['_id'][region['_id']] = region
                self.settings['cache']['region']['map']['slug'][region['slug']] = region

    def get_current_user(self):
        return self.session.get('user')

    def get_current_user_full_name(self):
        try:
            full_name = u'%s %s' % (self.current_user['firstname'], self.current_user['lastname'])
        except:
            full_name = u'Anonynewb'
        return full_name.strip()

    def write_error(self, status_code, *args, **kwargs):
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
        self.update_region_cache()
        self.update_pages(self.settings['siteuser'], 'site')

        content_html = yield motor.Op(motordb.pages.find_one, {
                            'user._id': self.settings['siteuser'],
                            'type': 'site',
                        })

        self.render('index.html',
            content_html = content_html['data'],
            all_regions=self.settings['cache']['region']['sectioned'],
            state = "Alaska",
            form=LoginForm(),
        )

################################################################################
## ┏━┓┏━╸┏━╸╻┏━┓┏┓╻╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┣┳┛┣╸ ┃╺┓┃┃ ┃┃┗┫┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ╹┗╸┗━╸┗━┛╹┗━┛╹ ╹╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class RegionHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, region_slug):
        motordb = self.settings['motordb']

        self.session.set('foo', ['bar', 'baz'])

        self.update_region_cache()

        region = self.settings['cache']['region']['map']['slug'][region_slug]

        self.update_pages(region['client']['_id'], region['slug'])

        content_html = yield motor.Op(motordb.pages.find_one, {
                            'user._id': region['client']['_id'],
                            'type': region['slug'],
                        })
        if not content_html:
            content_html = {'data': 'Coming Soon...'}
        pprint.pprint(self.settings['cache'])
        self.render('region.html',
            content_html = content_html['data'],
            all_regions=self.settings['cache']['region']['sectioned'],
            state = "Alaska",
            envelope=region['geom']['envelope'],
            region_slug = region_slug,
            region = region,
            form=LoginForm(),
        )

################################################################################

class PurchaseHandler(BaseHandler):

    @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        mongodb = self.settings['mongodb']

        self.update_region_cache()

        if self.session.get('purchase'):
            purchase = self.session.get('purchase')
            self.session.delete('purchase')
            user = self.get_current_user()
            amount = int(float(purchase['amount'].strip('$').strip().replace(',','')))
            print amount

            print "Iterating through regions"

            purchase_id = bson.ObjectId()
            purchase_potential = 0
            potential_lots = []
            fulfulled = False

            for region in self.settings['cache']['region']['array']:
                print region['name']
                #don't bother checking if the region has any available positions.. lets just start working on lots.
                while True:
                    potential_lot = mongodb.lots.find_and_modify(
                                    query = {
                                        'region._id': region['_id'],
                                        'precision': region['precision'],
                                        'value.normal.available': {"$ne": 0, "$gte": 0, "$lte": amount - purchase_potential},
                                        'purchase._id': None,
                                    },
                                    update = {
                                        '$set': {
                                            'purchase._id': purchase_id,
                                        }
                                    },
                                    sort = [('region._id', 1), ('order', 1)],
                                    upsert=False,
                                    new=False
                                )
                    if not potential_lot:
                        break
                    potential_lots.append((potential_lot['_id'], potential_lot['hash'], potential_lot['value']['normal']['available'], region['_id']))
                    purchase_potential += potential_lot['value']['normal']['available']
                    print potential_lot['_id'], potential_lot['value']['normal']['available'], purchase_potential, amount - purchase_potential, amount

            pprint.pprint(potential_lots)
            
            charge = stripe.Charge.create(
                amount=int(purchase_potential * 100),
                currency="usd",
                card=purchase['token'], # obtained with Stripe.js
                description="Charge for %s (%s)" % (user['name']['preferred'], str(user['_id']))
            )

            if charge['paid']:
                for lot_oid, lot_hash, lot_value, lot_region_oid in potential_lots:
                    for parent_hash in [lot_hash[0:p] for p in range(1, len(lot_hash)+1)]: #dynamic precision
                        mongodb.lots.update(
                            {
                                'hash': parent_hash,
                                'region._id': lot_region_oid,                    
                            },
                            {
                                '$inc': {
                                    'value.normal.available': -lot_value,
                                }                               
                            }
                        )

                        #lol.. just do this once per region later FIXME
                        mongodb.regions.update(
                            {
                                'region._id': lot_region_oid,                    
                            },
                            {
                                '$inc': {
                                    'value.normal.available': -lot_value,
                                }                               
                            }
                        )
        
            else:            
                for lot_oid, lot_hash, lot_value, lot_region_oid in potential_lots:
                    mongodb.lots.update(
                        {
                           '_id', lot_oid,
                        },
                        {
                            '$set': {
                                'purchase._id': None,
                            }                               
                        }
                    )

            self.render('purchased.html', charge = charge)
            mailgun = tornado.httpclient.AsyncHTTPClient()
            response = yield tornado.gen.Task(mailgun.fetch, "https://api.mailgun.net/v2/akcarbonexchange.mailgun.org/messages",
                auth_username='api',
                auth_password='key-5lux8y538yix4ch5m4yzcurrk8pxs6m0',
                method='POST',
                body=urllib.urlencode({
                    "from": "AK Carbon Exchange <postmaster@akcarbonexchange.mailgun.org>",
                    "to": "shane@bogomip.com",
                    "subject": "Purchase Receipt",
                    "text": "Testing ...."
                }),
            )
            print response.body


        else:
            print [j['name'] for j in sorted(self.settings['cache']['region']['array'], key=lambda x: x['order'])]
            self.render('purchase.html')
        

    @tornado.web.authenticated
    def post(self):
        self.session.set(
                'purchase', {
                    'amount': self.get_argument('amount', strip=True),
                    'token': self.get_argument('stripeToken', strip=True),
                    }
                )

        self.redirect(self.request.uri)
################################################################################
## ╻  ┏━┓┏━╸╻┏┓╻┏━╸┏━┓┏━┓┏┳┓
## ┃  ┃ ┃┃╺┓┃┃┗┫┣╸ ┃ ┃┣┳┛┃┃┃
## ┗━╸┗━┛┗━┛╹╹ ╹╹  ┗━┛╹┗╸╹ ╹

class LoginForm(wtforms.Form):
    username = wtforms.TextField('Username', [wtforms.validators.Length(min=4, max=25)])
    password = wtforms.PasswordField('Password', [wtforms.validators.Length(min=4, max=25), ])

class LoginHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        
        motordb = self.settings['motordb']
        auth = self.session.get('auth', {})
        self.session.delete('auth')

        next_uri = self.get_argument('next', None)

        form = LoginForm(**auth)

        if form.validate():
            self.session.delete('user')

            authorized_oid = self.authorize_user(form.username.data, form.password.data)

            if authorized_oid:
                user = yield motor.Op(motordb.users.find_one, {
                            '_id': authorized_oid,
                        })

                self.session.set('user', user)

                self.redirect(next_uri or self.reverse_url('index'))
                return

        else:
            print form
        self.render('login.html', form=form)

    def post(self):

        self.session.set(
                'auth', {
                    'username': self.get_argument('username', strip=True),
                    'password': self.get_argument('password'),
                    }
                )

        self.redirect(self.request.uri)


################################################################################
## ╻  ┏━┓┏━╸┏━┓╻ ╻╺┳╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
## ┃  ┃ ┃┃╺┓┃ ┃┃ ┃ ┃ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━╸┗━┛┗━┛┗━┛┗━┛ ╹ ╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class LogoutHandler(BaseHandler):
    def get(self):
        self.session.delete('user')
        self.redirect(self.reverse_url('index'))

################################################################################
##  ┏┓┏━┓┏━┓┏┓╻╺┳╸┏━╸┏━┓╺┳╸╻ ╻┏━┓┏┓╻╺┳┓╻  ┏━╸┏━┓
##   ┃┗━┓┃ ┃┃┗┫ ┃ ┣╸ ┗━┓ ┃ ┣━┫┣━┫┃┗┫ ┃┃┃  ┣╸ ┣┳┛
## ┗━┛┗━┛┗━┛╹ ╹ ╹ ┗━╸┗━┛ ╹ ╹ ╹╹ ╹╹ ╹╺┻┛┗━╸┗━╸╹┗╸

class JSONTestHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
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
        view_bounds_ring.TransformTo(WGS_84)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_north)
        view_bounds_ring.AddPoint(view_bounds_east, view_bounds_north)
        view_bounds_ring.AddPoint(view_bounds_east, view_bounds_south)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_south)
        view_bounds_ring.AddPoint(view_bounds_west, view_bounds_north)

        view_bounds_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
        view_bounds_geom.TransformTo(WGS_84)
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
                possible_hash_ring.TransformTo(WGS_84)
                possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
                possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['n'])
                possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['s'])
                possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['s'])
                possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
            
                possible_hash_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
                possible_hash_geom.TransformTo(WGS_84)
            
                possible_hash_geom.AddGeometry(possible_hash_ring)

                possible_hash_geom_intersection = view_bounds_geom.Intersection(possible_hash_geom)
                possible_hash_geom_intersection.TransformTo(WGS_84)
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
            possible_hash_ring.TransformTo(WGS_84)
            possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
            possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['n'])
            possible_hash_ring.AddPoint(possible_hash_bbox['e'], possible_hash_bbox['s'])
            possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['s'])
            possible_hash_ring.AddPoint(possible_hash_bbox['w'], possible_hash_bbox['n'])
        
            possible_hash_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
            possible_hash_geom.TransformTo(WGS_84)
        
            possible_hash_geom.AddGeometry(possible_hash_ring)

            possible_hash_geom_intersection = view_bounds_geom.Intersection(possible_hash_geom)
            possible_hash_geom_intersection.TransformTo(WGS_84)
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
            outline = osgeo.ogr.Geometry(wkb=str(lot['geom']['outline']))
            outline.TransformTo(WGS_84)
            lot['geom']['outline'] = json.loads(osgeo.ogr.ForceToPolygon(outline).ExportToJson())
            #geom = osgeo.ogr.ForceToPolygon(osgeo.ogr.Geometry(json.dumps(lot['geom']['outline'])).ConvexHull())
            geom = outline.ConvexHull()

            if view_bounds_geom.Contains(geom) or view_bounds_geom.Intersects(geom) or view_zoom == 5:
                region_set.add(lot['region']['_id'])
                if view_zoom != 5:
                    lots.append(lot)

        for region_oid in region_set:
            region = copy.deepcopy(self.settings['cache']['region']['map']['_id'][region_oid])
            region['region'] = True
            outline = osgeo.ogr.Geometry(wkb=str(region['geom']['outline']))
            outline.TransformTo(WGS_84)
            region['geom']['outline'] = json.loads(osgeo.ogr.ForceToPolygon(outline).ExportToJson())
            regions.append(region)
        

        self.write(bson.json_util.dumps(sorted(regions, key=lambda x: x['order']) + lots))
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
            tornado.web.URLSpec(r"/purchase$", PurchaseHandler),
            tornado.web.URLSpec(r"/login$", LoginHandler, name='login'),
            tornado.web.URLSpec(r"/logout$", LogoutHandler, name='logout'),
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
            'cache': {
                'region': {
                    'key': 'aceregion',
                    'stamp': None,
                    'array': [],
                    'sectioned': {},
                    'map': {
                        '_id': {},
                        'slug': {},
                    },
                },
            },
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


