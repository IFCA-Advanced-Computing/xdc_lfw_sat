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
import os
import json
import datetime
from six import string_types
from functools import reduce
import operator
import io

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


def valid_region(region, coord = None):
    """
    check if the regions exits

    Parameters
    ----------
    coordinates: list of coordinates

    Raises
    ------
    FormatError
            Not a valid region
    """

    if coord == None:
        if region in config.regions:
            coordinates = config.regions[region]['coordinates']
        else:
            msg = "Region not available. The available regions are: {}".format(config.regions.keys())
            raise argparse.ArgumentTypeError(msg)
    else:

        #Hacer saltar el widget del mapa

        W = round(-360.0 + float(coord.split('[')[2][:8]), 4)
        S = float(coord.split('[')[2][-11:-4])
        E = round(-360.0 + float(coord.split('[')[4][:8]), 4)
        N = float(coord.split('[')[4][-11:-4])

        coordinates = {}
        coordinates['W'], coordinates['S'] = W, S
        coordinates['E'], coordinates['N'] = E, N

    return coordinates

def configuration_path(output_path, region):
    """
    Configure the tree of datasets path.
    Create the folder and the downloaded_files file.

    Parameters
    ----------
    path : datasets path from config file
    """

    region_path = os.path.join(output_path, region)

    if not (os.path.isdir(region_path)):
        if not (os.path.isdir(output_path)):
            os.mkdir(output_path)
        os.mkdir(region_path)

def unzip_tarfile(filename, tile_path):

    tar = tarfile.open(filename, "r:gz")
    tar.extractall(path = tile_path)
    tar.close()
    os.remove(filename)

def unzip_zipfile(filename, tile_path):

    zip_ref = zipfile.ZipFile(filename, 'r')
    zip_ref.extractall(tile_path)
    zip_ref.close()
    os.remove(filename)

#Sub-functions of read_config_file
def get_by_path(root, items):
    """
    Access a nested object in root by item sequence.
    ref: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    return reduce(operator.getitem, items, root)

#Sub-functions of read_config_file
def set_by_path(root, items, value):
    """
    Set a value in a nested object in root by item sequence.
    ref: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys
    """
    get_by_path(root, items[:-1])[items[-1]] = value


#Read the metadata file of Landsat
def landsat_config_file(tile_path):
    """
    Read a LandSat MTL config file to a Python dict
    """

    f = open(tile_path)

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


def open_compressed(byte_stream, file_format, output_folder):
    """
    Extract and save a stream of bytes of a compressed file from memory.
    Parameters
    ----------
    byte_stream : bytes
    file_format : str
        Compatible file formats: tarballs, zip files
    output_folder : str
        Folder to extract the stream
    Returns
    -------
    Folder name of the extracted files.
    """

    tar_extensions = ['tar', 'bz2', 'tb2', 'tbz', 'tbz2', 'gz', 'tgz', 'lz', 'lzma', 'tlz', 'xz', 'txz', 'Z', 'tZ']
    if file_format in tar_extensions:
        tar = tarfile.open(mode="r:{}".format(file_format), fileobj=io.BytesIO(byte_stream))
        tar.extractall(output_folder)
        folder_name = tar.getnames()[0]
        return os.path.join(output_folder, folder_name)

    elif file_format == 'zip':
        zf = zipfile.ZipFile(io.BytesIO(byte_stream))
        zf.extractall(output_folder)
        folder_name = zf.namelist()[0].split('/')[0]
        return os.path.join(output_folder, folder_name)

    else:
        raise ValueError('Invalid file format for the compressed byte_stream')
