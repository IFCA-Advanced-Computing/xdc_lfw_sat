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
from osgeo import gdal, osr

class sentinel():

    def __init__(self, tile_path, output_path):

        # Bands per resolution (bands should be load always in the same order)
        self.bands = {10: ['B4', 'B3', 'B2', 'B8'],
                             20: ['B5', 'B6', 'B7', 'B8A', 'B11', 'B12'],
                             60: ['B1', 'B9', 'B10']}

        #Bands descriptions
        self.band_desc = {10: {'B4': 'B4 Red	[665 nm]',
                               'B3': 'B3 Green	[560 nm]',
                               'B2': 'B2 Blue	[490 nm]',
                               'B8': 'B8 Near infrared	[842 nm]'},
                          20: {'B5': 'B5 Vegetation classification	[705 nm]',
                               'B6': 'B6 Vegetation classification	[740 nm]',
                               'B7': 'B7 Vegetation classification	[783 nm]',
                               'B8A': 'B8A Vegetation classification	[865 nm]',
                               'B11': 'B11 Snow / ice / cloud discrimination	[1610 nm]',
                               'B12': 'B12 Snow / ice / cloud discrimination	[2190 nm]'},
                          60: {'B1': 'B1 Aerosol detection	[443 nm]',
                               'B9': 'B9 Water vapour	[945 nm]',
                               'B10': 'B10 Cirrus	[1375 nm]'}}

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

    
    def load_bands(self):

        self.sets = {10: [], 20: [], 60: []}
        self.coord = {10: {}, 20: {}, 60: {}}
        data_bands = {10: {}, 20: {}, 60: {}}

        raster = self.read_config_file()
        datasets = raster.GetSubDatasets()

    	# Getting the bands shortnames and descriptions
        for dsname, dsdesc in datasets:
            for res in self.sets.keys():
                if '{}m resolution'.format(res) in dsdesc:
                    
                    print('Loading bands of Resolution {}'.format(res))

                    self.sets[res] += [(dsname, dsdesc)]
                    ds_bands = gdal.Open(dsname)
                    data_bands[res] = ds_bands.ReadAsArray()
                    self.coord[res]['geotransform'] = ds_bands.GetGeoTransform()
                    self.coord[res]['geoprojection'] = ds_bands.GetProjection()
                    break

        self.arr_bands = {10: {}, 20: {}, 60: {}}
        for res in self.sets.keys():
            for i, band in enumerate(self.bands[res]):
                self.arr_bands[res][band] = data_bands[res][i]


    def write_band(self, dst_ds, arr_bands, dataset, band_desc):
    
        for i, b in enumerate(arr_bands[dataset]):
        
            print ('Saving {} ...'.format(band_desc[dataset][b]))
        
            # write band
            dst_ds.GetRasterBand(i+1).SetDescription(band_desc[dataset][b])
            dst_ds.GetRasterBand(i+1).SetNoDataValue(np.nan)
            dst_ds.GetRasterBand(i+1).WriteArray(arr_bands[dataset][b])
            
            
    def save_netCDF(self):
    
        os.mkdir(self.output_path)
        self.load_bands()
        
        for dataset in self.band_desc.keys():
            
            #path
            nc_path = os.path.join(self.output_path, 'Bands_{}m.nc'.format(dataset))
            
            #properties
            list_bands = list(self.arr_bands[dataset].keys())
            num_bands = len(self.arr_bands[dataset])
            nx, ny = self.arr_bands[dataset][list_bands[0]].shape        
            gt = self.coord[dataset]['geotransform']
            epsg = int((self.coord[dataset]['geoprojection'].split(','))[-1][1:-3])
            
            # prepare netCDF file
            dst_drv = gdal.GetDriverByName('netCDF')
            dst_ds = dst_drv.Create(nc_path, ny, nx, num_bands, gdal.GDT_Float32)
            dst_ds.SetGeoTransform(gt)
            srs = osr.SpatialReference() 
            srs.ImportFromEPSG(epsg)
            dst_ds.SetProjection(srs.ExportToWkt())
        
            #Write bands
            self.write_band(dst_ds, self.arr_bands, dataset, self.band_desc)
            
            # finalize to disk and close
            dst_ds.FlushCache()
            dst_ds = None