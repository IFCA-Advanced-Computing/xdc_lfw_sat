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
		    required=False,
		    choices=['Sentinel2', 'Landsat8', None])

parser.add_argument('-path',
		   help='output path',
		   required=True)

args = parser.parse_args()

#Check the format date and if end_date > start_date
sd, ed = utils.valid_date(args.start_date, args.end_date)

#chek the region to attach coordinates
utils.valid_region(args.region)

#configure the tree of datasets path
utils.path(args.path)

if args.sat == "Sentinel2":
    #download sentinel files
    s = sentinel.Sentinel(sd, ed, args.region, path=args.path)
    s.download()
elif args.sat == "Landsat8":
    #download landsat files
    l = landsat.Landsat(sd, ed, args.region, path=args.path)
    l.download()
elif args.sat == None:
    #download sentinel and landsat files
    s = sentinel.Sentinel(sd, ed, args.region, path=args.path)
    s.download()

    l = landsat.Landsat(sd, ed, args.region, path=args.path)
    l.download()

