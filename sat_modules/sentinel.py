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
Given two dates and region, download N Sentinel Collections scenes from ESA
Sentinel dataHUB.

The downloaded Sentinel collection scenes are compatible with:
S2MSI1C: Top-of-atmosphere reflectances in cartographic geometry
or S2MSI2A: Bottom-of-atmosphere reflectance in cartographic geometry

Parameters
----------
inidate: datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")
enddate: datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")
region: name of one reservoir saved in the "coord_reservoirs.json" file

Author: Daniel Garcia Diaz
Date: Sep 2018
"""

#imports subfunctions
from sat_modules import config
from sat_modules import utils

#imports apis
import requests
from tqdm import tqdm
import os
import json

class Sentinel:

    def __init__(self, inidate, enddate, region=None, platform='Sentinel-2', producttype="S2MSI1C"):

        #Search parameter needed for download
        self.inidate = inidate.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.enddate = enddate.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.region = region
        self.coord = config.regions[region]["coordinates"]
        self.producttype = producttype
        self.platform = platform

        #work path
        self.path = config.local_path

        #metadata of the data
        self.output = {}

        #ESA APIs
        self.api_url = 'https://scihub.copernicus.eu/apihub/'
        self.credentials = config.sentinel_pass


    def search(self):

        # Post the query to Copernicus
        query = {'footprint': '"Intersects(POLYGON(({0} {1},{2} {1},{2} {3},{0} {3},{0} {1})))"'.format(self.coord['W'],
                                                                                                        self.coord['S'],
                                                                                                        self.coord['E'],
                                                                                                        self.coord['N']),
                 'producttype': self.producttype,
                 'platformname': self.platform,
                 'beginposition': '[{} TO {}]'.format(self.inidate, self.enddate)
                 }

        data = {'format': 'json',
                'start': 0,  # offset
                'rows': 100,
                'limit': 100,
                'orderby': '',
                'q': ' '.join(['{}:{}'.format(k, v) for k, v in query.items()])
                }

        response = requests.post(self.api_url + 'search?',
                                 data=data,
                                 auth=(self.credentials['username'], self.credentials['password']),
                                 headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'})

        # Parse the response
        json_feed = response.json()['feed']
        print('Found {} results from Sentinel'.format(json_feed['opensearch:totalResults']))

        if int(json_feed['opensearch:totalResults']) == 0:
            results = []

        else:
            results = json_feed['entry']
            print('Retrieving {} results'.format(len(results)))

            if isinstance(results, dict):  # if the query returns only one product, products will be a dict not a list
                results = [results]

        return results


    def download(self):

        session = requests.session()
        session.auth = (self.credentials['username'], self.credentials['password'])
        chunk_size = 1024

        #load the downloaded files
        with open(os.path.join(self.path, 'downloaded_files.json')) as data_file:
            downloaded_files = json.load(data_file)

        #results of the search
        results = self.search()

        for file in results:

            ID = file['id']
            filename = file['title']
            summary = file['summary']

            #file size
            download_url = "https://scihub.copernicus.eu/dhus/odata/v1/Products('{}')/$value".format(ID)
            resp = session.get(download_url, stream=True, allow_redirects=True)
            size = int(resp.headers['content-Length'])

            if size < 250000000: #size Bytes
                print ("    {} not valid file!, corner image".format(filename))
                continue

            #Metadata for Onedata
            self.output[filename] = {}
            self.output[filename]['inidate'] = summary.split(',')[0].split(' ')[-1]
            self.output[filename]['enddate'] = summary.split(',')[0].split(' ')[-1]
            self.output[filename]['region'] = self.region
            self.output[filename]['W'] = str(self.coord['W'])
            self.output[filename]['E'] = str(self.coord['E'])
            self.output[filename]['N'] = str(self.coord['N'])
            self.output[filename]['S'] = str(self.coord['S'])
            self.output[filename]['params'] = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B10', 'B11', 'B12']

            if filename in downloaded_files['Sentinel-2'][self.region]:
                print ("    file {} already downloaded".format(filename))
                continue

            #create path and folder for the scene
            region_path = os.path.join(self.path, self.region)

            print ('    Downloading {} files'.format(filename))
            downloaded_files['Sentinel-2'][self.region].append(filename)

            #download
            with tqdm(total = size, unit_scale=True, unit='B') as pbar:
                with session.get(download_url, auth =session.auth, stream=True, allow_redirects=True) as r:
                    filename = os.path.join(region_path, '{}.zip'.format(filename))
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                pbar.update(chunk_size)

        # Save the new list of files
        with open(os.path.join(self.path, 'downloaded_files.json'), 'w') as outfile:
            json.dump(downloaded_files, outfile)
