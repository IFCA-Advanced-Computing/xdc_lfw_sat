#!/usr/bin/python3
import argparse

from sat_modules import utils
from sat_modules import download_sentinel
from sat_modules import download_landsat

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

parser.add_argument("-reg",
                   "--region",
                   help = "Name of the region selected",
                   required=True,
                   choices=['CdP', 'Cogotas', 'Sanabria'])


parser.add_argument('--coord',
                    dest='coord',
                    required=False,
                    help='list of coordinates')

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
coord = utils.valid_region(args.region, args.coord)

#configure the tree of datasets path
utils.path(args.path, args.region)

if args.sat == "Sentinel2":
    #download sentinel files
    s = download_sentinel.download_sentinel(sd, ed, args.region, coord, path=args.path)
    s.download()
elif args.sat == "Landsat8":
    #download landsat files
    l = download_landsat.download_landsat(sd, ed, args.region, coord, path=args.path)
    l.download()
elif args.sat == None:
    #download sentinel and landsat files
    s = download_sentinel.download_sentinel(sd, ed, args.region, coord, path=args.path)
    s.download()

    l = download_landsat.download_landsat(sd, ed, args.region, coord, path=args.path)
    l.download()

