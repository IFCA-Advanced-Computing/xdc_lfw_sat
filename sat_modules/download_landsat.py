# -*- coding: utf-8 -*-

# Copyright 2018 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Given two dates and region, download N Landsat Collections scenes from EarthExplorer.
The downloaded Landsat collection scenes are compatible with LANDSAT_8_C1

Parameters
----------
inidate: datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")
enddate: datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")
region: name of one reservoir
coordinates : dict; Coordinates of the region to search.
Example: {"W": -2.830, "S": 41.820, "E": -2.690, "N": 41.910}}
producttype : str; Dataset type. A list of productypes can be found in https://mapbox.github.io/usgs/reference/catalog/ee.html
username: str
password : str

Author: Daniel Garcia Diaz
Date: Sep 2018
"""
#APIs
import os, re, shutil
import json

import requests

#subfunctions
from sat_modules import utils
from sat_modules import landsat_utils

class download_landsat:

    def __init__(self, inidate, enddate, region, coordinates=None, producttype='LANDSAT_8_C1', cloud=100,
                 username=None, password=None, path=None):
        """
        Parameters
        ----------
        inidate : str
            Initial date of the query in format '%Y-%m-%dT%H:%M:%SZ'
        enddate : str
            Final date of the query in format '%Y-%m-%dT%H:%M:%SZ'
        coordinates : dict
            Coordinates of the region to search.
            Example: {"W": -2.830, "S": 41.820, "E": -2.690, "N": 41.910}}
        producttype : str
            Dataset type. A list of productypes can be found in https://mapbox.github.io/usgs/reference/catalog/ee.html
        username: str
        password : str
        """
        self.session = requests.Session()

        # Search parameters
        self.inidate = inidate.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.enddate = enddate.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.coord = coordinates
        self.producttype = producttype
        self.region = region
        self.cloud = cloud

        #work path
        self.path = path

        # API
        api_version = '1.4.1'
        self.api_url = 'https://earthexplorer.usgs.gov/inventory/json/v/{}/'.format(api_version)
        self.login_url = 'https://ers.cr.usgs.gov/login/'
        self.credentials = {'username': username, 'password': password}

        # Fetching the API key
        data = {'username': username,
                'password': password,
                'catalogID': 'EE'}
        response = self.session.post(self.api_url + 'login?',
                                     data={'jsonRequest': json.dumps(data)})
        response.raise_for_status()
        json_feed = response.json()
        if json_feed['error']:
            raise Exception('Error while searching: {}'.format(json_feed['error']))
        self.api_key = json_feed['data']

    def search(self):
        """
        build the query and get the Landsat Collections scenes from request def
        """

        # Post the query
        query = {'datasetName': self.producttype,
                 'includeUnknownCloudCover': False,
                 'maxResults': 100,
                 'temporalFilter': {'startDate': self.inidate,
                                    'endDate': self.enddate},
                 'spatialFilter': {'filterType': 'mbr',
                                   'lowerLeft': {'latitude': self.coord['S'],
                                                 'longitude': self.coord['W']},
                                   'upperRight': {'latitude': self.coord['N'],
                                                  'longitude': self.coord['E']}
                                   },
                 'apiKey': self.api_key
                 }

        response = self.session.post(self.api_url + 'search',
                                     params={'jsonRequest': json.dumps(query)})
        response.raise_for_status()
        json_feed = response.json()
        if json_feed['error']:
            raise Exception('Error while searching: {}'.format(json_feed['error']))
        results = json_feed['data']['results']

        print('Found {} results from Landsat'.format(len(results)))
        return results

    def download(self):

        #results of the search
        results = self.search()
        if not isinstance(results, list):
            results = [results]

        # Make the login
        response = self.session.get(self.login_url)
        data = {'username': self.credentials['username'],
                'password': self.credentials['password'],
                'csrf_token': re.findall(r'name="csrf_token" value="(.+?)"', response.text),
                '__ncforminfo': re.findall(r'name="__ncforminfo" value="(.+?)"', response.text)
                }
        response = self.session.post(self.login_url, data=data, allow_redirects=False)
        response.raise_for_status()

        # Download the files
        for r in results:
            tile_id = r['entityId']

            save_dir = os.path.join(self.path, tile_id)
            output_path = os.path.join(self.path, self.region, tile_id)

            if not os.path.isdir(save_dir):
                os.mkdir(save_dir)
                os.mkdir(output_path)
            else:
                print('File {} already downloaded'.format(tile_id))
                continue

            print('Downloading {} ...'.format(tile_id))

            url = 'https://earthexplorer.usgs.gov/download/12864/{}/STANDARD/EE'.format(tile_id)
            response = self.session.get(url, stream=True, allow_redirects=True)
            tile_path = utils.open_compressed(byte_stream=response.raw.read(),
                                             file_format='gz',
                                             output_folder=save_dir)

            l8 = landsat_utils.landsat(tile_path=save_dir, output_path=output_path)
            l8.load_bands()
            shutil.rmtree(save_dir)
