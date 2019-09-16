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

#APIs
import os, re
import numpy as np
from osgeo import gdal

#import subfunctions
from sat_modules import gdal_utils
from sat_modules import utils

class landsat():
    
    def __init__(self, tile_path):
        
        self.max_res = 30
        
        # Bands per resolution (bands should be load always in the same order)
        self.res_to_bands = {15: ['B8'],
                             30: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B9', 'B10', 'B11']}
        
        self.band_desc = {30: {'B1': 'B1 Ultra Blue (coastal/aerosol) [435nm-451nm]',
                               'B2': 'B2 Blue [452nm-512nm]',
                               'B3': 'B3 Green [533nm-590nm]',
                               'B4': 'B4 Red [636nm-673nm]',
                               'B5': 'B5 Near Infrared (NIR)	[851nm-879nm]',
                               'B6': 'B6 Shortwave Infrared (SWIR) 1	[1566nm-1651nm]',
                               'B7': 'B7 Shortwave Infrared (SWIR) 2	[2107nm-2294nm]',
                               'B9': 'B9 Cirrus [1363nm-1384nm]',
                               'B10': 'B10 Thermal Infrared (TIRS) 1 [1060nm-1119nm]',
                               'B11': 'B11 Thermal Infrared (TIRS) 2 [1150nm-1251nm]'},
                         15: {'B8': 'B8 Panchromatic [503nm-676nm]'}
                         }
        
        self.resolutions = [res for res in self.res_to_bands.keys() if res <= self.max_res]
        
        self.tile_path = tile_path
        
    def read_config_file(self):
        
        # Read config
        r = re.compile("^(.*?)MTL.txt$")
        matches = list(filter(r.match, os.listdir(self.tile_path)))
        if matches:
            mtl_path = os.path.join(self.tile_path, matches[0])
        else:
            raise ValueError('No MTL config file found.')
        config = utils.landsat_config_file(mtl_path)

        return config
            
    def read_bands(self, tmp_ds):
        
        tmp_arr = tmp_ds.GetRasterBand(1).ReadAsArray()
        tmp_arr = tmp_arr.astype(np.float32)
        tmp_arr[tmp_arr==0] = np.nan #replace 0's with Nan's
        tmp_arr = np.ma.masked_where(condition=np.isnan(tmp_arr), a=tmp_arr)
    
        return tmp_arr
    
    
    def save_files(self):
        
        for res in self.resolutions:
            output_path = os.path.join(self.tile_path, 'Bands_{}.tif'.format(res))
            coord = self.coordinates[res]
            description = self.band_desc[res]
            bands = self.data_bands[res]
            arr_bands = []
            desc = []
            for b in bands.keys():
                arr_bands.append(bands[b])
                desc.append(description[b])
            gdal_utils.save_gdal(output_path, np.array(arr_bands), desc, coord['geotransform'], coord['geoprojection'], file_format='GTiff')
            
    def load_bands(self):
        
        self.config = self.read_config_file()
        
        # Read dataset bands in GDAL
        self.ds_bands = {res: None for res in self.resolutions}
        self.data_bands = {}
        
        # Get coordinates
        self.coordinates = {}

        for res in self.resolutions:
            
            print("Loading selected data from GDAL: {}m".format(res))
            self.ds_bands[res] = []
            self.data_bands[res] = {}
            self.coordinates[res] = {}
            
            for band in self.res_to_bands[res]:
                
                file = self.config['METADATA_FILE_INFO']['LANDSAT_PRODUCT_ID']
                file_path = os.path.join(self.tile_path, '{}_{}.TIF'.format(file, band))
                
                tmp_ds = gdal.Open(file_path)
                self.ds_bands[res].append(tmp_ds)
                
                tmp_arr = self.read_bands(tmp_ds)            
                self.data_bands[res][band] = tmp_arr

    
            self.coordinates[res]['geotransform'] = self.ds_bands[res][0].GetGeoTransform()
            self.coordinates[res]['geoprojection'] = self.ds_bands[res][0].GetProjection()
        
        self.save_files()
