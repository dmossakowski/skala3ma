#    Copyright (C) 2023 David Mossakowski
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


import json
import os
import glob
import random
from datetime import datetime, date, timedelta
import time
from collections import Counter
import tracemalloc
import sqlite3 as lite
import uuid
import copy
from threading import RLock
import csv

import requests

from CalculationStrategy import CalculationStrategy
from CalculationStrategyFsgt import CalculationStrategyFsgt0, CalculationStrategyFsgt1
import skala_db
import activities_db

from src.User import User

sql_lock = RLock()
from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context

from functools import lru_cache, reduce
import logging

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
GODMODE = os.getenv('GODMODE') == "true"

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

# ID, date, name, location
COMPETITIONS_TABLE = "competitions"
# ID, name, club, m/f, list of climbs
USERS_TABLE = "climbers"
ROUTES_TABLE = "routes"
ROUTES_CLIMBED_TABLE = "routes_climbed"
GYM_TABLE = "gyms"
#comps = {}
#climbers = {}


colors = { 'Vert':'#2E8B57',
'Vert marbré':'#2E8B57',
'Rouge':'#FF0000',
'Rouge marbré':'#FF0000',
'Gris':'#708090',
'Marron':'#A0522D',
'Rose marbré':'#FF69B4',
'Jaune':'#FFFF00',
'Orange':'#FFA500',
'Rose':'#FF69B4',
'Mauve':'#800080',
'Blanc':'#FFFFFF',
'Bleu':'#0000FF',
'Bleu marbré':'#0000FF',
'Noir':'#000000',
'Noir marbré':'#000000',
'Violet': '#9400D3',
'Saumon':'#FFE4C4'}


categories = {0:"Séniors 16-49 ans | Ado 12-13", 
              1:"Titane 50-64 ans | Ado 14-15 ", 
              2: "Diamant 65 ans et + | Ado 16-17"}

categories_ado = {0:"Ado 12-13", 
              1:"Ado 14-15 ", 
              2: "Ado 16-17"}


def get_enhanced_gym_routes(routesid):
    routes = skala_db.get_routes(routesid)
    

    for route in routes:
        route['color'] = colors.get(route['color'], '#000000')
        route['category'] = categories.get(route['category'], 'Séniors 16-49 ans | Ado 12-13')
    return routes