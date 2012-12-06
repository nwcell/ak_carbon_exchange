#!/usr/bin/python

import re

import datetime

import argparse
import logging
import progressbar

import pymongo
import bson
import bson.json_util
import json

import osgeo.osr
import osgeo.ogr

import geohash

PRECISION = 7 #.. Yeah.. that happen.
SEGMENT_PRECISION = 0.0001 #not good enough for 8
BUFFER_PRECISION = 0.0001 # not good enough for 8
WGS_84 = osgeo.osr.SpatialReference()
WGS_84.ImportFromEPSG(4326)

NAD83_Alaska_Albers = osgeo.osr.SpatialReference()
NAD83_Alaska_Albers.ImportFromEPSG(3338)

NOW = datetime.datetime.utcnow()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                formatter_class=argparse.RawTextHelpFormatter
            )

    parser.add_argument('-v',
        dest='verbose',
        action='count',
        help='add multiple times for increased verbosity')

    parser.add_argument('shapefile',
        action='store',
        metavar='SHAPEFILE')

    parser.add_argument('region_name_field',
        action='store',
        metavar='REGION_NAME_FIELD')

    parser.add_argument('region_slug_field',
        action='store',
        metavar='REGION_SLUG_FIELD')

    parser.add_argument('state',
        action='store',
        metavar='STATE')

    parser.add_argument('client_oid',
        action='store',
        metavar='CLIENT_OID')

    args = parser.parse_args()

    loglevel = logging.CRITICAL

    if args.verbose >= 4:
        loglevel = logging.DEBUG
    elif args.verbose == 3:
        loglevel = logging.INFO
    elif args.verbose == 2:
        loglevel = logging.WARNING
    elif args.verbose == 1:
        loglevel = logging.ERROR

    logging.basicConfig(level=loglevel)

    logger = logging.getLogger('arguments')

    for arg, value in vars(args).iteritems():
        logger.debug('%s:%s' % (arg, value))

    logger = logging.getLogger('general')

    # Set ObjectID for client
    client_oid = bson.ObjectId(args.client_oid)

    conn = pymongo.Connection()

    coll = conn.ace

    coll.regions.create_index([('name', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])
    coll.regions.create_index([('slug', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])
    coll.regions.create_index([('patrion._id', pymongo.ASCENDING), ('name', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])

    coll.lots.create_index([('hash', pymongo.ASCENDING), ('region._id', pymongo.ASCENDING), ('precision', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])
    coll.lots.create_index([('parent', pymongo.ASCENDING), ('region._id', pymongo.ASCENDING), ('precision', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])
    coll.lots.create_index([('region._id', pymongo.ASCENDING), ('precision', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])
    coll.lots.create_index([('precision', pymongo.ASCENDING), ('region._id', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)]) #make this a uniquely sparse solution

    for layer in osgeo.ogr.Open(args.shapefile):
        for feature in layer:
            lots = {}

            hashes = set([])
            region_name = feature[args.region_name_field]
            region_slug = re.sub('\W', '', feature[args.region_slug_field])
            region_logger = logging.getLogger(region_name)
            feature_geom = feature.GetGeometryRef()
            feature_geom.TransformTo(WGS_84)

            if region_name == "ELIM NATIVE CORPORATION":
                continue

            #print feature.ExportToJson(as_object=True) ##Very handy for later

            #insert this after you've calculated and added to it
            region_oid = bson.ObjectId()

            region = {
                    '_id': region_oid,
                    'name': region_name,
                    'slug': region_slug,
                    'state': args.state,
                    'precisions': PRECISION,
                    'srid': {
                        'storage': 4326,
                        'calculation': 3338,
                    },
                    'client': {
                        '_id': client_oid,
                    },
                    'srid': {
                        'storage': 4326,
                        'calculation': 3338,
                    },
                    'area': {
                        'normal': {
                            'allocated': 0,
                            'available': 0,
                        },
                        'buffer': {
                            'allocated': 0,
                            'available': 0,
                        }
                    },
                    'dates': {
                        'imported': NOW,
                        'estimated': None,
                    },
                }

            buffered_feature_geom = feature_geom.Clone()
            buffered_feature_geom.Segmentize(SEGMENT_PRECISION)
            buffer_offset = 1

            while buffered_feature_geom.Area():
                #do stuff pre-buffer
                #for g in range(buffered_feature_geom.Getfeature_geometryCount()):
                #    sub_feature_geom = buffered_feature_geom.Getfeature_geometryRef(g)
                #    region_logger.info(sub_feature_geom.GetPointCount())

                for coords in [c.split() for c in buffered_feature_geom.ExportToWkt().replace('MULTI', '').replace('POLYGON', '').replace('(', '').replace(')', '').strip().split(',')]:
                    hash = geohash.encode(float(coords[1]), float(coords[0]), precision=PRECISION)
                    hashes.update([hash[0:i] for i in range(1, len(hash)+1)])

                buffered_feature_geom = feature_geom.Buffer(buffer_offset * -BUFFER_PRECISION)

                buffered_feature_geom.Segmentize(SEGMENT_PRECISION)
                region_logger.info(repr([buffer_offset, '%.64f' % buffered_feature_geom.Area()]))
                buffer_offset += 1

            #region_logger.info(hashes)


            widgets = ['Setting Defaults: ', progressbar.Percentage(), ' ', progressbar.Bar()]
            progress = progressbar.ProgressBar(widgets=widgets).start()

            sorted_hashes = sorted(hashes)

            for hash in progress(sorted_hashes):

                lot_oid = bson.ObjectId()

                default_lot_dict = {
                    '_id': lot_oid,
                    'hash': hash,
                    'state': args.state, #Convert to FIPS code #FIXME
                    'parent': hash[0:len(hash)-1] or None,
                    'precision': len(hash),
                    'children': [],
                    'geom': {
                        'centroid': None,
                        'bounds': None,
                        'outline': None,
                    },
                    'area': {
                        'unit': 'meters',
                        'normal': {
                            'allocated': 0,
                            'available': 0,
                        },
                        'buffer': {
                            'allocated': 0,
                            'available': 0,
                        }
                    },
                    'flags': {
                        'buffer': False,
                        'normal': False,
                    },
                    'dates': {
                        'imported': NOW,
                        'estimated': None,
                    },
                    'region': {
                        '_id': region_oid,
                        'name': region_name,
                        'slug': region_slug,
                    },
                    
                }

                lots[hash] = default_lot_dict


            widgets = ['Calculating Area: ', progressbar.Percentage(), ' ', progressbar.Bar()]
            progress = progressbar.ProgressBar(widgets=widgets).start()

            for hash in progress(sorted_hashes):

                hash_bbox = geohash.bbox(hash)

                hash_bbox_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
                hash_bbox_ring.AssignSpatialReference(WGS_84)
                hash_bbox_ring.AddPoint(hash_bbox['w'], hash_bbox['n'])
                hash_bbox_ring.AddPoint(hash_bbox['e'], hash_bbox['n'])
                hash_bbox_ring.AddPoint(hash_bbox['e'], hash_bbox['s'])
                hash_bbox_ring.AddPoint(hash_bbox['w'], hash_bbox['s'])
                hash_bbox_ring.AddPoint(hash_bbox['w'], hash_bbox['n'])

                hash_bbox_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon)
                hash_bbox_geom.AssignSpatialReference(WGS_84)

                hash_bbox_geom.AddGeometry(hash_bbox_ring)

                hash_geom = feature_geom.Intersection(hash_bbox_geom)
                hash_geom.AssignSpatialReference(WGS_84) #Mucho Importanto

                lots[hash]['geom']['centroid'] = bson.Binary(hash_geom.Centroid().ExportToWkb())
                lots[hash]['geom']['bounds'] = bson.Binary(hash_bbox_geom.ConvexHull().ExportToWkb())
                lots[hash]['geom']['outline'] = bson.Binary(hash_geom.ConvexHull().ExportToWkb())

                ### Add Children to Parents
                hash_parent = lots[hash]['parent']
                if hash_parent:
                    if not hash in lots[hash_parent]['children']:
                        lots[hash_parent]['children'].append(hash)

                ##### FROM THIS POINT ON.. ONLY HIGH PRECISION LOTS WILL BE USED FOR CALCULATIONS

                if not len(hash) == PRECISION:
                    continue

                #do some buffering tests here.

                hash_bbox_area = hash_bbox_geom.Area()
                hash_geom_area = hash_geom.Area()

                is_buffer_lot = (hash_bbox_area != hash_geom_area) and len(hash) == PRECISION

                #convert to appropriate meter projection
                
                hash_geom_xform = hash_geom.Clone()
                hash_geom_xform.TransformTo(NAD83_Alaska_Albers)
                area_square_meters = hash_geom_xform.Area()

                ###### Now it's time to make the database parts work out well.
                
                for parent in [hash[0:p] for p in range(1, len(hash))]: #dynamic precision
                    specific_area = 'buffer' if is_buffer_lot else 'normal'
                    lots[parent]['area'][specific_area]['allocated'] += area_square_meters
                    lots[parent]['area'][specific_area]['available'] += area_square_meters
                    region['area'][specific_area]['allocated'] += area_square_meters
                    region['area'][specific_area]['available'] += area_square_meters

            coll.regions.insert(region)
            coll.lots.insert(lots.itervalues())
