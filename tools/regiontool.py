#!/usr/bin/python

import argparse
import logging
import progressbar

import pymongo
import bson
import json

import osgeo.osr
import osgeo.ogr

import geohash

#LEVELS = [1,2,3,4,5,6,7,8]
LEVELS = [1,2,3,4,5,6,7]
LEVELCOLLNAME = {
    1: 'lots.level_1',
    2: 'lots.level_2',
    3: 'lots.level_3',
    4: 'lots.level_4',
    5: 'lots.level_5',
    6: 'lots.level_6',
    7: 'lots',
}
PRECISION = LEVELS[-1]

WGS_84 = osgeo.osr.SpatialReference()
WGS_84.ImportFromEPSG(4326)

NAD83_Alaska_Albers = osgeo.osr.SpatialReference()
NAD83_Alaska_Albers.ImportFromEPSG(3338)

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

    coll = conn.carboneffect

    coll.regions.create_index([('name', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])
    coll.regions.create_index([('patrion._id', pymongo.ASCENDING), ('name', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)])

    for level in LEVELS:
        coll[LEVELCOLLNAME[level]].create_index([('hash', pymongo.ASCENDING), ('region._id', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)], unique=True)
        coll[LEVELCOLLNAME[level]].create_index([('parent', pymongo.ASCENDING), ('region._id', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)], unique=True)
        coll[LEVELCOLLNAME[level]].create_index([('region._id', pymongo.ASCENDING), ('_id', pymongo.ASCENDING)], unique=True)

    for layer in osgeo.ogr.Open(args.shapefile):
        for feature in layer:
            region_name = feature[args.region_name_field]
            
            geom = feature.GetGeometryRef()
            geom.TransformTo(WGS_84)

            region_oid = coll.regions.insert(
                {
                    'name': region_name,
                    'json': json.loads(geom.ExportToJson()),
                    'srid': {
                        'storage': 4326,
                        'calculation': 3338,
                    },
                    'client': {
                        '_id': client_oid,
                    }
                }
            )

            region_oid_str = str(region_oid)
            
            new_geom = geom.Clone()
            #get area estimate
            new_geom.TransformTo(NAD83_Alaska_Albers)
            estimated_area = new_geom.Area()

            geom_west, geom_east, geom_south, geom_north = geom.GetEnvelope()

            north_west_geohash = geohash.encode(geom_north, geom_west, precision=PRECISION)
            south_east_geohash = geohash.encode(geom_south, geom_east, precision=PRECISION)

            north_west_bbox = geohash.bbox(north_west_geohash)
            south_east_bbox = geohash.bbox(south_east_geohash)

            #Start here.. read like a book
            current_geohash = north_west_geohash

            logger.info('Working on Region ' + region_name)

            #REMOVEME
            if estimated_area > 50000000:
                estimated_area = 50000000

            widgets = ['Calculating: ', progressbar.Percentage(), ' ', progressbar.Bar()]
            progress = progressbar.ProgressBar(widgets=widgets, maxval=estimated_area).start()

            progress_area = 0

            while True: #Danger Will Robinson FIXME

                current_lat, current_long, current_width, current_height = geohash.decode_exactly(current_geohash)

                current_bbox = geohash.bbox(current_geohash)

                #If we pass by the eastern most point of our bounding box.. wrap back to west and down one
                if current_long + current_width > south_east_bbox['e']:                    
                    current_geohash = geohash.encode(current_bbox['s'] - (current_height / 2.0), geom_west, precision=PRECISION)
                    continue

                #If we are below our geoms bbox.. then break the loop cause we are done.
                if current_lat - current_height < south_east_bbox['s']:
                    break

                #Create a ring for a polygon defining the bounding box so we can check for overlap with the geom
                bbox_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
                bbox_ring.AssignSpatialReference(WGS_84)
                bbox_ring.AddPoint(current_bbox['w'], current_bbox['n'])
                bbox_ring.AddPoint(current_bbox['e'], current_bbox['n'])
                bbox_ring.AddPoint(current_bbox['e'], current_bbox['s'])
                bbox_ring.AddPoint(current_bbox['w'], current_bbox['s'])
                bbox_ring.AddPoint(current_bbox['w'], current_bbox['n'])

                bbox_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon) #create a polygon
                bbox_geom.AssignSpatialReference(WGS_84)

                bbox_geom.AddGeometry(bbox_ring)

                overlapped = geom.Overlaps(bbox_geom)
                contained = geom.Contains(bbox_geom)

                if contained or overlapped:    

                    if overlapped:
                        bbox_geom = geom.Union(bbox_geom)

                    new_bbox_geom = bbox_geom.Clone()
                    new_bbox_geom.TransformTo(NAD83_Alaska_Albers)
                    area = new_bbox_geom.Area()

                    progress_area += area

                    coll.regions.update(
                        {'_id': region_oid},
                        {
                            '$inc': {
                                'count': 1,
                                'area.allocated': area if contained and not overlapped else 0,
                                'area.buffered': area if overlapped and not contained else 0,
                            },                                
                        }
                    )

                    for level in LEVELS:
                        _lat, _long, _width, _height = geohash.decode_exactly(current_geohash[0:level])

                        _bbox = geohash.bbox(current_geohash[0:level])

                        _bbox_ring = osgeo.ogr.Geometry(osgeo.ogr.wkbLinearRing)
                        _bbox_ring.AssignSpatialReference(WGS_84)
                        _bbox_ring.AddPoint(_bbox['w'], _bbox['n'])
                        _bbox_ring.AddPoint(_bbox['e'], _bbox['n'])
                        _bbox_ring.AddPoint(_bbox['e'], _bbox['s'])
                        _bbox_ring.AddPoint(_bbox['w'], _bbox['s'])
                        _bbox_ring.AddPoint(_bbox['w'], _bbox['n'])
        
                        _bbox_geom = osgeo.ogr.Geometry(osgeo.ogr.wkbPolygon) #create a polygon
                        _bbox_geom.AssignSpatialReference(WGS_84)
        
                        _bbox_geom.AddGeometry(_bbox_ring)

                        _overlapped = geom.Overlaps(bbox_geom)
                        _contained = geom.Contains(bbox_geom)

                        if _overlapped:
                            _bbox_geom = geom.Union(_bbox_geom)
        
                        _doc = coll[LEVELCOLLNAME[level]].find_and_modify(
                            {
                                'hash': current_geohash[0:level],
                                'region._id': region_oid
                            },
                            {
                                '$set': {
                                    'hash': current_geohash[0:level],
                                    'region': {
                                        '_id': region_oid,
                                        'name': region_name,
                                    },
                                    'parent': current_geohash[0:level-1] or None,
                                    'buffered': True if (_overlapped and not _contained) and level == PRECISION else False,
                                },
                                '$inc': {
                                    'area.allocated': area if _contained and not _overlapped else 0,
                                    'area.buffered': area if _overlapped and not _contained else 0,
                                },
                                '$addToSet': {
                                    'children': current_geohash[0:level+1]
                                },
                            },
                            upsert = True,
                        )

                        #Add the big ugly stuff if'n it's new
                        if not _doc: #New document
                            coll[LEVELCOLLNAME[level]].update(
                                {
                                    'hash': current_geohash[0:level],
                                    'region._id': region_oid
                                },
                                {
                                    '$set': {
                                        #'wkb': bson.Binary(bbox_geom.ExportToWkb())
                                        'json': json.loads(bbox_geom.ExportToJson()),
                                    },
                                },
                            )    
                                
                #One step to the right... probably faster if we use neighbors correctly.
                current_geohash = geohash.encode(current_lat, current_bbox['e'] + (current_width/2), precision=PRECISION)
                if progress_area <= estimated_area:
                    progress.update(progress_area)
                
                #REMOVEME
                if progress_area >= estimated_area:
                    break
            
            progress.finish()        
