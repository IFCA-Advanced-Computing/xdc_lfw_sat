#!/usr/bin/python3
import argparse

from sat_modules import config
from sat_modules import utils
from sat_modules import sentinel
from sat_modules import landsat

parser = argparse.ArgumentParser(description='Gets data from satellite')

parser.add_argument("-sd",
                    "--startdate",
                    help="The Start Date - format DD-MM-YYYY",
                    required=True,
                    dest='start_date')

parser.add_argument("-ed",
                    "--enddate",
                    help="The Start Date - format DD-MM-YYYY",
                    required=True,
                    dest='end_date')

parser.add_argument('--region',
                    dest='region',
                    required=True,
                    choices=['CdP','Sanabria','Cogotas'],
                    help='Valid values: CdP, Sanabria, Cogotas')

parser.add_argument('-sat',
		    help="Sentinel2 or Landsat8",
		    required=True,
		    choices=['Sentinel2', 'Landsat8'])

args = parser.parse_args()

#Check the format date and if end_date > start_date
sd, ed = utils.valid_date(args.start_date, args.end_date)

#chek the region to attach coordinates
utils.valid_region(args.region)

#configure the tree of datasets path
utils.path()

if args.sat == "Sentinel2":
    #download sentinel files
    s = sentinel.Sentinel(sd, ed, args.region)
    s.download()
elif args.sat == "Landsat8":
    #download landsat files
    l = landsat.Landsat(sd, ed, args.region)
    l.download()
