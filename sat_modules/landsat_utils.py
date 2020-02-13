"""
This file intends to gather code specific to LandSat 8
Original author: Ignacio Heredia
Date: February 2019

Adaptation
----------
Date: August 2019
Author: Daniel Garcia
Email: garciad@ifca.unican.es
Github: garciadd
"""

from functools import reduce
import operator
import os, re
import numpy as np
import json
import time

from osgeo import gdal, osr
from netCDF4 import Dataset


#Sub-functions of read_config_file
def get_by_path(root, items):
    """
    Access a nested object in root by item sequence.
    ref: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    return reduce(operator.getitem, items, root)


def set_by_path(root, items, value):
    """
    Set a value in a nested object in root by item sequence.
    ref: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    get_by_path(root, items[:-1])[items[-1]] = value


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


class DOS(object):

    def __init__(self, metadata, band, arr_band):
        """
        initialize the variables used to preprocess landsat images
        and apply DOS1 atmospheric correction
        """

        self.band = band
        self.arr_band = arr_band
        self.name_bands = {'B1': 'BAND_1', 'B2': 'BAND_2', 'B3': 'BAND_3', 'B4': 'BAND_4', 'B5': 'BAND_5', 'B6': 'BAND_6', 'B7': 'BAND_7', 'B8': 'BAND_8', 'B9': 'BAND_9', 'B10': 'BAND_10', 'B11': 'BAND_11'}

        self.metadata = metadata

        self.Tz = 1
        self.Ed = 0
        self.Tv = 1

    def sr_radiance(self, arr, min_value):

        Lmin = self.Ml * min_value + self.Al
        L1 = 0.01 * ((self.Esun * np.cos(self.z * np.pi / 180.) * self.Tz) + self.Ed) * self.Tv / (np.pi * self.d**2)
        Lp = Lmin - L1

        L = self.Ml * arr + self.Al
        Lsr = L - Lp

        return Lsr

    def sr_thermal(self, arr):

        L = self.Ml * arr + self.Al
        Tb = self.k2 / np.log((self.k1 / L) + 1)

        return Tb

    def sr_reflectance(self):

        name = self.name_bands[self.band]

        if self.band=='B10' or self.band=='B11':

            self.Ml = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_MULT_{}'.format(name)])
            self.Al = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_ADD_{}'.format(name)])
            self.k1 = float(self.metadata['TIRS_THERMAL_CONSTANTS']['K1_CONSTANT_{}'.format(name)])
            self.k2 = float(self.metadata['TIRS_THERMAL_CONSTANTS']['K2_CONSTANT_{}'.format(name)])

            T = self.sr_thermal(self.arr_band)

            return T

        else:

            self.Ml = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_MULT_{}'.format(name)])
            self.Al = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_ADD_{}'.format(name)])
            self.rad_max = float(self.metadata['MIN_MAX_RADIANCE']['RADIANCE_MAXIMUM_{}'.format(name)])
            self.ref_max = float(self.metadata['MIN_MAX_REFLECTANCE']['REFLECTANCE_MAXIMUM_{}'.format(name)])
            self.d = float(self.metadata['IMAGE_ATTRIBUTES']['EARTH_SUN_DISTANCE'])
            self.z = 90 - float(self.metadata['IMAGE_ATTRIBUTES']['SUN_ELEVATION'])
            self.Esun = (np.pi * self.d**2) * self.rad_max / self.ref_max

            min_value = np.amin(self.arr_band)
            Lsr = self.sr_radiance(self.arr_band, min_value)
            sr = (np.pi * self.d**2 * Lsr) / (((self.Esun * np.cos(self.z * np.pi / 180.) * self.Tz) + self.Ed) * self.Tv)
            sr[sr>=1] = 1
            sr[sr<0] = 0

            return sr


class landsat():

    def __init__(self, tile_path, output_path):

        # Bands per resolution (bands should be load always in the same order)
        self.bands = {'Panchromatic_Band': ['B8'],
             'Spectral_Bands': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B9'],
             'Thermal_bands': ['B10', 'B11']}

        self.band_desc = {'Panchromatic_Band': {'B8': 'B8 Panchromatic [503nm-676nm]'},
                 'Spectral_Bands': {'B1': 'B1 Ultra Blue (Coastal aerosol) [435nm-451nm]',
                     'B2': 'B2 Blue [452nm-512nm]',
                     'B3': 'B3 Green [533nm-590nm]',
                     'B4': 'B4 Red [636nm-673nm]',
                     'B5': 'B5 Near Infrared (NIR) [851nm-879nm]',
                     'B6': 'B6 Shortwave Infrared (SWIR) 1 [1566nm-1651nm]',
                     'B7': 'B7 Shortwave Infrared (SWIR) 2 [2107nm-2294nm]',
                     'B9': 'B9 Cirrus [1363nm-1384nm]'},
                 'Thermal_bands': {'B10': 'B10 Thermal Infrared (TIRS) 1  [1060nm-1119nm]',
                     'B11': 'B11 Thermal Infrared (TIRS) 2 [1150nm-1251nm]'},
                 }

        self.tile_path = tile_path
        self.output_path = output_path

    #Read the metadata file of Landsat
    def read_config_file(self):
        """
        Read a LandSat MTL config file to a Python dict
        """

        # Read config
        r = re.compile("^(.*?)MTL.txt$")
        matches = list(filter(r.match, os.listdir(self.tile_path)))
        if matches:
            mtl_path = os.path.join(self.tile_path, matches[0])
        else:
            raise ValueError('No MTL config file found.')
            
        print('xml_path: {}'.format(mtl_path))

        f = open(mtl_path)

        group_path = []
        config = {}

        for line in f:
            line = line.lstrip(' ').rstrip() #remove leading whitespaces and trainling newlines

            if line.startswith('GROUP'):
                group_name = line.split(' = ')[1]
                group_path.append(group_name)
                set_by_path(root=config, items=group_path, value={})

            elif line.startswith('END_GROUP'):
                del group_path[-1]

            elif line.startswith('END'):
                continue

            else:
                key, value  = line.split(' = ')
                try:
                    set_by_path(root=config, items=group_path + [key], value=json.loads(value))
                except Exception:
                    set_by_path(root=config, items=group_path + [key], value=value)
        f.close()
        config = config['L1_METADATA_FILE']
        return config

    def read_bands(self, tmp_ds):

        tmp_arr = tmp_ds.GetRasterBand(1).ReadAsArray()
        tmp_arr = tmp_arr.astype(np.float32)
        tmp_arr[tmp_arr==0] = np.nan #replace 0's with Nan's
        tmp_arr = np.ma.masked_where(condition=np.isnan(tmp_arr), a=tmp_arr)

        return tmp_arr

    def get_latslons(self):

        xlow, ylow = (self.coordinates['Corner Coordinates'])[0][1], (self.coordinates['Corner Coordinates'])[0][0]
        xup, yup = (self.coordinates['Corner Coordinates'])[2][1], (self.coordinates['Corner Coordinates'])[2][0]

        lats = np.linspace(ylow, yup, num=self.coordinates['Ysize'])
        lons = np.linspace(xlow, xup, num=self.coordinates['Xsize'])

        return lats, lons

    def save_netCDF(self, dataset, arr_bands):

        #path
        nc_path = os.path.join(self.output_path, '{}.nc'.format(dataset))

        #latitudes & longitudes arrays
        lats, lons = self.get_latslons()

        # create a file (Dataset object, also the root group).
        dsout = Dataset(nc_path, 'w', format='NETCDF4')
        dsout.description = dataset
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
        crs.spatial_ref = self.coordinates['geoprojection']

        dsout.close()


    def load_bands(self):

        self.metadata = self.read_config_file()

        for dataset in self.bands.keys():

            print("Loading {} ...".format(dataset))

            # Read dataset bands in GDAL
            self.arr_bands = {}

            # Get coordinates
            self.coordinates = {}

            for band in self.bands[dataset]:

                file = self.metadata['METADATA_FILE_INFO']['LANDSAT_PRODUCT_ID']
                file_path = os.path.join(self.tile_path, '{}_{}.TIF'.format(file, band))

                tmp_ds = gdal.Open(file_path)
                arr_band = self.read_bands(tmp_ds)

                dos = DOS(self.metadata, band, arr_band)
                self.arr_bands[band] = dos.sr_reflectance()

            self.coordinates['geotransform'] = tmp_ds.GetGeoTransform()
            self.coordinates['geoprojection'] = tmp_ds.GetProjection()

            self.coordinates['Xsize'] = tmp_ds.RasterXSize
            self.coordinates['Ysize'] = tmp_ds.RasterYSize
            self.coordinates['Corner Coordinates'] = GetExtent(tmp_ds.GetGeoTransform(), tmp_ds.RasterXSize, tmp_ds.RasterYSize)

            self.save_netCDF(dataset, self.arr_bands)
