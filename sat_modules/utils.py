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
Satellite utils

Author: Daniel Garcia Diaz
Date: May 2018
"""

#Submodules
from sat_modules import config

#APIs
import zipfile, tarfile
import argparse
import numpy as np
import os, shutil
import json
import datetime
import utm
from netCDF4 import Dataset
from six import string_types


def valid_date(sd, ed):
    """
    check if the format date input is string("%Y-%m-%d") or datetime.date
    and return it as format datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")

    Parameters
    ----------
    sd(start_date) : str "%Y-%m-%d"
    ed(end_date) : str "%Y-%m-%d"

    Returns
    -------
    sd : datetime
        datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")
    ed : datetime
        datetime.strptime("YYYY-MM-dd", "%Y-%m-%d")

    Raises
    ------
    FormatError
        Unsupported format date
    ValueError
        Unsupported date value
    """

    if isinstance(sd, datetime.date) and isinstance(ed, datetime.date):

        return sd, ed

    elif isinstance(sd, string_types) and isinstance(ed, string_types):    
        try:
            sd = datetime.datetime.strptime(sd, "%Y-%m-%d")
            ed = datetime.datetime.strptime(ed, "%Y-%m-%d")
            if sd < ed:
                return sd, ed
            else:
                msg = "Unsupported date value: '{} or {}'.".format(sd, ed)
                raise argparse.ArgumentTypeError(msg)
        except:
            msg = "Unsupported format date: '{} or {}'.".format(sd, ed)
            raise argparse.ArgumentTypeError(msg)
    else:
        msg = "Unsupported format date: '{} or {}'.".format(sd, ed)
        raise argparse.ArgumentTypeError(msg)


def valid_region(r):
    """
    check if the regions exits

    Parameters
    ----------
    r(region) : str e.g: "CdP"

    Raises
    ------
    FormatError
            Not a valid region
    """

    if r in config.regions:
        pass
    else:
        msg = "Not a valid region: '{0}'.".format(r)
        raise argparse.ArgumentTypeError(msg)


def path():
    """
    Configure the tree of datasets path. 
    Create the folder and the downloaded_files file.

    Parameters
    ----------
    path : datasets path from config file
    """

    file = 'downloaded_files.json'
    list_region = config.regions
    local_path = config.local_path

    try:
        with open(os.path.join(local_path, file)) as data_file:
            json.load(data_file)
    except:
        if not (os.path.isdir(local_path)):
            os.mkdir(local_path)

        dictionary = {"Sentinel-2": {}, "Landsat 8": {}}

        for region in list_region:

            os.mkdir(os.path.join(local_path, region))
            dictionary['Sentinel-2'][region] = []
            dictionary['Landsat 8'][region] = []

        with open(os.path.join(local_path, 'downloaded_files.json'), 'w') as outfile:
            json.dump(dictionary, outfile)
