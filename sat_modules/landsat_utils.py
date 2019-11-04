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
from osgeo import gdal, osr
import numpy as np
import json


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


class DOS(object):

    def __init__(self, data_bands, metadata):
        """
        initialize the variables used to preprocess landsat images
        and apply DOS1 atmospheric correction
        """
        self.data_bands = data_bands
        self.name_bands = {'B1': 'BAND_1', 'B2': 'BAND_2', 'B3': 'BAND_3', 'B4': 'BAND_4', 'B5': 'BAND_5', 
                          'B6': 'BAND_6', 'B7': 'BAND_7', 'B8': 'BAND_8', 'B9': 'BAND_9', 'B10': 'BAND_10', 'B11': 'BAND_11', }
        self.metadata = metadata
        self.arr_sr = {15: {}, 30: {}}
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

        for res in self.data_bands.keys():
            for band in self.data_bands[res]:
                
                name = self.name_bands[band]
                print ('Loading band ...: {}'.format(band))
            
                if band=='B10' or band=='B11':
                                    
                    self.Ml = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_MULT_{}'.format(name)])
                    self.Al = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_ADD_{}'.format(name)])      
                    self.k1 = float(self.metadata['TIRS_THERMAL_CONSTANTS']['K1_CONSTANT_{}'.format(name)])
                    self.k2 = float(self.metadata['TIRS_THERMAL_CONSTANTS']['K2_CONSTANT_{}'.format(name)])
                
                    arr = self.data_bands[res][band]                
                    T = self.sr_thermal(arr)
                    self.arr_sr[res][band] = T
                
                else:

                    self.Ml = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_MULT_{}'.format(name)])
                    self.Al = float(self.metadata['RADIOMETRIC_RESCALING']['RADIANCE_ADD_{}'.format(name)])
                    self.rad_max = float(self.metadata['MIN_MAX_RADIANCE']['RADIANCE_MAXIMUM_{}'.format(name)])
                    self.ref_max = float(self.metadata['MIN_MAX_REFLECTANCE']['REFLECTANCE_MAXIMUM_{}'.format(name)])
                    self.d = float(self.metadata['IMAGE_ATTRIBUTES']['EARTH_SUN_DISTANCE'])
                    self.z = 90 - float(self.metadata['IMAGE_ATTRIBUTES']['SUN_ELEVATION'])
                    self.Esun = (np.pi * self.d**2) * self.rad_max / self.ref_max
                    
                    arr = self.data_bands[res][band]
                    min_value = np.amin(arr)
                    Lsr = self.sr_radiance(arr, min_value)
                    sr = (np.pi * self.d**2 * Lsr) / (((self.Esun * np.cos(self.z * np.pi / 180.) * self.Tz) + self.Ed) * self.Tv)
                    sr[sr>=1] = 1
                    self.arr_sr[res][band] = sr

        return self.arr_sr


class landsat():

    def __init__(self, tile_path, output_path):

        # Bands per resolution (bands should be load always in the same order)
        self.bands = {'Panchromatic_Band': ['B8'],
             'Spectral_Bands': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B9'],
             'Thermal_bands': ['B10', 'B11']}

        self.band_desc = {'Panchromatic_Band': {'B8': 'B8 Panchromatic [503nm-676nm]'},
                 'Spectral_Bands': {'B1': 'B1 Ultra Blue (coastal/aerosol) [435nm-451nm]',
                     'B2': 'B2 Blue [452nm-512nm]',
                     'B3': 'B3 Green [533nm-590nm]',
                     'B4': 'B4 Red [636nm-673nm]',
                     'B5': 'B5 Near Infrared (NIR)	[851nm-879nm]',
                     'B6': 'B6 Shortwave Infrared (SWIR) 1	[1566nm-1651nm]',
                     'B7': 'B7 Shortwave Infrared (SWIR) 2	[2107nm-2294nm]',
                     'B9': 'B9 Cirrus [1363nm-1384nm]'},
                 'Thermal_bands': {'B10': 'B10 Thermal Infrared (TIRS) 1 [1060nm-1119nm]',
                     'B11': 'B11 Thermal Infrared (TIRS) 2 [1150nm-1251nm]'},
                 }

        self.tile_path = tile_path
        self.output_path = output_path

        
    #Read the metadata file of Landsat
    def read_config_file(self, tile_path):
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


    def load_bands(self):

        self.metadata = self.read_config_file()

        # Read dataset bands in GDAL
        ds_bands = {dataset: None for dataset in self.bands.keys()}
        self.arr_bands = {}

        # Get coordinates
        self.coordinates = {}

        for dataset in self.bands.keys():

            print("Loading {} ...".format(dataset))
            ds_bands[dataset] = []
            self.arr_bands[dataset] = {}
            self.coordinates[dataset] = {}

            for band in self.bands[dataset]:

                file = self.metadata['METADATA_FILE_INFO']['LANDSAT_PRODUCT_ID']
                file_path = os.path.join(self.tile_path, '{}_{}.TIF'.format(file, band))
                
                tmp_ds = gdal.Open(file_path)
                tmp_arr = self.read_bands(tmp_ds)            
                self.arr_bands[dataset][band] = tmp_arr

            self.coordinates[dataset]['geotransform'] = ds_bands[dataset][0].GetGeoTransform()
            self.coordinates[dataset]['geoprojection'] = ds_bands[dataset][0].GetProjection()


    def write_band(self, dst_ds, arr_bands, dataset, band_desc):
    
        for i, b in enumerate(arr_bands[dataset]):
        
            print ('Saving {} ...'.format(band_desc[dataset][b]))
        
            # write band
            dst_ds.GetRasterBand(i+1).SetDescription(band_desc[dataset][b])
            dst_ds.GetRasterBand(i+1).SetNoDataValue(np.nan)
            dst_ds.GetRasterBand(i+1).WriteArray(arr_bands[dataset][b])
            
            
    def save_netCDF(self):
    
        self.load_bands()

        dos = DOS(self.arr_bands, self.metadata)
        arr_sr = dos.sr_reflectance()
        
        os.mkdir(self.output_path)
        
        for dataset in self.band_desc.keys():
            
            #path
            nc_path = os.path.join(self.output_path, '{}.nc'.format(dataset))
            
            #properties
            list_bands = list(arr_sr[dataset].keys())
            num_bands = len(arr_sr[dataset])
            nx, ny = arr_sr[dataset][list_bands[0]].shape        
            gt = self.coordinates[dataset]['geotransform']
            epsg = int((self.coordinates[dataset]['geoprojection'].split(','))[-1][1:-3])
            
            # prepare netCDF file
            dst_drv = gdal.GetDriverByName('netCDF')
            dst_ds = dst_drv.Create(nc_path, ny, nx, num_bands, gdal.GDT_Float32)
            dst_ds.SetGeoTransform(gt)
            srs = osr.SpatialReference() 
            srs.ImportFromEPSG(epsg)
            dst_ds.SetProjection(srs.ExportToWkt())
        
            #Write bands
            self.write_band(dst_ds, arr_sr, dataset, self.band_desc)
            
            # finalize to disk and close
            dst_ds.FlushCache()
            dst_ds = None