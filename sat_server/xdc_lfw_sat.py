#!/usr/bin/python3
import argparse
import json

from sat_modules import config
from sat_modules import utils
from sat_modules import download_sentinel
from sat_modules import download_landsat

parser = argparse.ArgumentParser(description='Gets data from satellite')

parser.add_argument("-sat_args", action="store",
                    required=False, type=str)

parser.add_argument('-path',
                   help='output path',
                   required=True)

args = parser.parse_args()
sat_args = json.loads(args.sat_args)
path = args.path

#Check the format date and if end_date > start_date
sd, ed = utils.valid_date(sat_args['start_date'], sat_args['end_date'])

#configure the tree of datasets path
utils.configuration_path(sat_args['sat_path'], sat_args['region'])

if sat_args['sat_type'] == "Sentinel2":

    s2_credentials = config.sentinel_pass

    S2_args = {'inidate': sd,
               'enddate': ed,
               'region': sat_args['region'],
               'coordinates': sat_args['coordinates'],
               'platform': 'Sentinel-2',
               'producttype': 'S2MSI1C',
               'cloud': sat_args['cloud'],
               'username': s2_credentials['username'],
               'password': s2_credentials['password'],
               'path': path}

    #download sentinel files
    s = download_sentinel.download_sentinel(**S2_args)
    s.download()

elif sat_args['sat_type'] == "Landsat8":

    l8_credentials = config.landsat_pass

    l8_args = {'inidate': sd,
               'enddate': ed,
               'region': sat_args['region'],
               'coordinates': sat_args['coordinates'],
               'producttype': 'LANDSAT_8_C1',
               'cloud': sat_args['cloud'],
               'username': l8_credentials['username'],
               'password': l8_credentials['password'],
               'path': path}

    #download landsat files
    l = download_landsat.download_landsat(**l8_args)
    l.download()

elif sat_args['sat_type'] == 'All':

    #ESA credentials
    s2_credentials = config.sentinel_pass

    S2_args = {'inidate': sd,
               'enddate': ed,
               'region': sat_args['region'],
               'coordinates': sat_args['coordinates'],
               'platform': 'Sentinel-2',
               'producttype': 'S2MSI1C',
               'cloud': sat_args['cloud'],
               'username': s2_credentials['username'],
               'password': s2_credentials['password'],
               'path': path}

    #download sentinel files
    s = download_sentinel.download_sentinel(**S2_args)
    s.download()

    #NASA credentials
    l8_credentials = config.landsat_pass

    l8_args = {'inidate': sd,
               'enddate': ed,
               'region': sat_args['region'],
               'coordinates': sat_args['coordinates'],
               'producttype': 'LANDSAT_8_C1',
               'cloud': sat_args['cloud'],
               'username': l8_credentials['username'],
               'password': l8_credentials['password'],
               'path': path}

    #download landsat files
    l = download_landsat.download_landsat(**l8_args)
    l.download()
