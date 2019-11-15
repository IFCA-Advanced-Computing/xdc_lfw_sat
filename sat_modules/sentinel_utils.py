"""
This file intends to gather code specific to Sentinel 2
Original author: Ignacio Heredia
Date: February 2019

Adaptation
----------
Date: August 2019
Author: Daniel Garcia
Email: garciad@ifca.unican.es
Github: garciadd
"""

#APIs
import os, re
import numpy as np
import time

from osgeo import gdal, osr
from netCDF4 import Dataset


def GetExtent(gt,cols,rows):
    ''' Return list of corner coordinates from a geotransform

        @type gt:   C{tuple/list}
        @param gt: geotransform
        @type cols:   C{int}
        @param cols: number of columns in the dataset
        @type rows:   C{int}
        @param rows: number of rows in the dataset
        @rtype:    C{[float,...,float]}
        @return:   coordinates of each corner
    '''
    ext=[]
    xarr=[0,cols]
    yarr=[0,rows]

    for px in xarr:
        for py in yarr:
            x=gt[0]+(px*gt[1])+(py*gt[2])
            y=gt[3]+(px*gt[4])+(py*gt[5])
            ext.append([x,y])
        yarr.reverse()
    return ext


class sentinel():

    def __init__(self, tile_path, output_path):

        # Bands per resolution (bands should be load always in the same order)
        self.bands = {10: ['B4', 'B3', 'B2', 'B8'],
                      20: ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12'],
                      60: ['B1', 'B9', 'B10']}

        #Bands descriptions
        self.band_desc = {10: {'B4': 'B4 Red [665 nm]',
                               'B3': 'B3 Green [560 nm]',
                               'B2': 'B2 Blue [490 nm]',
                               'B8': 'B8 Near infrared [842 nm]'},
                          20: {'B5': 'B5 Vegetation classification [705 nm]',
                               'B6': 'B6 Vegetation classification [740 nm]',
                               'B7': 'B7 Vegetation classification [783 nm]',
                               'B8A': 'B8A Vegetation classification [865 nm]',
                               'B11': 'B11 Snow ice cloud discrimination [1610 nm]',
                               'B12': 'B12 Snow ice cloud discrimination [2190 nm]'},
                          60: {'B1': 'B1 Aerosol detection [443 nm]',
                               'B9': 'B9 Water vapour [945 nm]',
                               'B10': 'B10 Cirrus [1375 nm]'}}

        #paths
        self.tile_path = tile_path
        self.output_path = output_path

        
    def read_config_file(self):

        # Process input tile name
        r = re.compile("^MTD_(.*?)xml$")
        matches = list(filter(r.match, os.listdir(self.tile_path)))
        if matches:
            xml_path = os.path.join(self.tile_path, matches[0])
        else:
            raise ValueError('No .xml file found.')

        # Open XML file and read band descriptions
        if not os.path.isfile(xml_path):
            raise ValueError('XML path not found.')

        raster = gdal.Open(xml_path)
        if raster is None:
            raise Exception('GDAL does not seem to support this file.')

        return raster


    def get_latslons(self):
        
        xlow, ylow = (self.coord['Corner Coordinates'])[0][1], (self.coord['Corner Coordinates'])[0][0]
        xup, yup = (self.coord['Corner Coordinates'])[2][1], (self.coord['Corner Coordinates'])[2][0]
    
        lats = np.linspace(ylow, yup, num=self.coord['Ysize'])
        lons = np.linspace(xlow, xup, num=self.coord['Xsize'])
        
        return lats, lons


    def save_netCDF(self, dataset, arr_bands):
            
        #path
        nc_path = os.path.join(self.output_path, 'Bands_{}.nc'.format(dataset))
            
        #latitudes & longitudes arrays
        lats, lons = self.get_latslons()

        # create a file (Dataset object, also the root group).
        dsout = Dataset(nc_path, 'w', format='NETCDF4')
        dsout.description = 'Bands_{}.nc'.format(dataset)
        dsout.history = 'Created {}'.format(time.ctime(time.time()))
        dsout.source = 'netCDF4 python module'

        # dimensions.
        lat = dsout.createDimension('lat', len(lats))
        lon = dsout.createDimension('lon', len(lons))

        # variables.
        latitudes = dsout.createVariable('lat','f4',('lat',))
        longitudes = dsout.createVariable('lon','f4',('lon',))

        latitudes.standard_name = 'latitude'
        latitudes.units = 'm north'
        latitudes.axis = "Y"
        latitudes[:] = lats

        longitudes.standard_name = 'longitude'
        longitudes.units = 'm east'
        longitudes.axis = "X"
        longitudes[:] = lons

        for b in arr_bands:

            print ('Saving {} ...'.format(self.band_desc[dataset][b]))

            band = dsout.createVariable(self.band_desc[dataset][b],
                                        'f4',
                                        ('lat', 'lon'),
                                        least_significant_digit=4,
                                        fill_value=np.nan
                                        )

            band[:] = arr_bands[b]
            band.standard_name = self.band_desc[dataset][b]
            band.units = 'rad'
            band.setncattr('grid_mapping', 'spatial_ref')

        crs = dsout.createVariable('spatial_ref', 'i4')
        crs.spatial_ref = self.coord['geoprojection']

        dsout.close()

    
    def load_bands(self):

        raster = self.read_config_file()
        datasets = raster.GetSubDatasets()

    	# Getting the bands shortnames and descriptions
        for dsname, dsdesc in datasets:

	    self.coord = {}
            data_bands = {}
            self.arr_bands = {}

            for res in self.bands.keys():
                if '{}m resolution'.format(res) in dsdesc:
                    
                    print('Loading bands of Resolution {}'.format(res))

                    ds_bands = gdal.Open(dsname)
                    data_bands = ds_bands.ReadAsArray()
                    self.coord['geotransform'] = ds_bands.GetGeoTransform()
                    self.coord['geoprojection'] = ds_bands.GetProjection()
                    self.coord['Xsize'] = ds_bands.RasterXSize
                    self.coord['Ysize'] = ds_bands.RasterYSize
                    self.coord['Corner Coordinates'] = GetExtent(ds_bands.GetGeoTransform(), ds_bands.RasterXSize, ds_bands.RasterYSize)

                    for i, band in enumerate(self.bands[res]):
                        self.arr_bands[band] = data_bands[i] / 10000

		    self.save_netCDF(res, self.arr_bands)
                    
                    break
