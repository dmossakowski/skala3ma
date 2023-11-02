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
import sqlite3 as lite
import uuid
import copy
from threading import RLock
import csv
import skala_db
import logging
import os

sql_lock = RLock()

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

JOURNEYS_TABLE = "journeys"
JOURNEY_ENTRY_DB = "journey_entries"


route_finish_status = {0: "attempt", 1: "flash", 2: "redpoint", 3: "toprope"}


def init():
    logging.info('initializing skala_journey...')

    if os.path.exists(DATA_DIRECTORY) and os.path.exists(COMPETITIONS_DB):
        db = lite.connect(COMPETITIONS_DB)

        # ptype 0-public
        cursor = db.cursor()

        cursor.execute('''CREATE TABLE if not exists ''' + JOURNEYS_TABLE + '''(
                       id text NOT NULL UNIQUE,
                       user_id text NOT NULL, 
                       gym_id text NOT NULL,
                       routes_id text NOT NULL,
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null,  
                       jsondata json NOT NULL
                       )''')
        db.commit()

        print('created ' + JOURNEYS_TABLE)

def add_journey_session(user, gym_id, routes_id, date):
    journey_id = str(uuid.uuid4().hex)

    journey = {"id": journey_id, "gym_id": gym_id, "routes_id": routes_id, "description": "", "routes": [],
               }
    # write this competition to db
    _add_journey_session(journey_id, user.get('id'), gym_id, routes_id, date, journey)
    return id



def add_journey_session2(date, user, gym_id, routes_id, description):
    journey_id = str(uuid.uuid4().hex)

    journey = {"id": journey_id, "gym_id": gym_id, "routes_id": routes_id, "description": description, "routes": [],
               }
    # write this competition to db
    _add_journey_session(date, user, gym_id, routes_id, description, journey)
    return id


def get_journey_session(session_id):
    return _get_journey(session_id)

def get_journey_sessions(user_id):
    return _get_journey_sessions_by_user_id(user_id)

# add an entry to an existing session
def add_journey_session_entry(journey_id, route_id, status, note):
    entry_id = str(uuid.uuid4().hex)

    journey = get_journey_session(journey_id)
    session_entry = {"id": entry_id, "route_id": route_id, "status": status, "note": note,
                   }
    journey.get('routes').append(session_entry)
    # write this competition to db
    _update_journey(journey_id, journey.get("user_id"), journey.get("gym_id"), journey.get("routes_id"), journey);

    return journey


def remove_journey_session(journey_id, entry_id):
    journey = get_journey_session(journey_id)

    if journey is None:
        return None
    for route_index, route in enumerate(journey['routes']):
        if route['id'] == entry_id:
            journey['routes'].pop(int(route_index))
    _update_journey(journey_id, journey.get("user_id"), journey.get("gym_id"), journey.get("routes_id"), journey);

    return journey


def _add_journey_session(journey_id, user_id, gym_id, routes_id, date, jsondata):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        jsondata['id']=journey_id
        jsondata['user_id']=user_id
        jsondata['gym_id']=gym_id
        jsondata['routes_id']=routes_id
        jsondata['date']=date

        cursor.execute("INSERT INTO " + JOURNEYS_TABLE + " (id, user_id, gym_id, routes_id, added_at, jsondata ) "
                                                    "values (?, ?, ?, ?, ?, ?)",
                       [str(journey_id), str(user_id), str(gym_id), str(routes_id), date, json.dumps(jsondata)])
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("added climbing session for user:"+str(user_id))


def _get_journey(journey_id):
    try:
        #sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        result = cursor.execute("select jsondata from " + JOURNEYS_TABLE + " where id =? ",
                       [str(journey_id)])
        result = result.fetchone()

        if result is None or result[0] is None:
            return None

        if result[0] is not None:
            return json.loads(result[0])
        else:
            return None

    finally:
        db.commit()
        db.close()
        #sql_lock.release()
        #logging.info("retrieved climbing session for user:"+str(session_id))


def _get_journey_sessions_by_user_id(user_id):
    try:
        #sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        result = cursor.execute("select jsondata from " + JOURNEYS_TABLE + " where user_id =? ",
                       [str(user_id)])
        #result = result.fetchall()
        journeys=[]
        if result is not None and result.arraysize > 0:
            for row in result.fetchall():
                # comp = row[0]
                journeys.append(json.loads(row[0]))
                # gyms[gym['id']] = gym
        return journeys

    finally:
        db.commit()
        db.close()
        #sql_lock.release()
        #logging.info("retrieved climbing session for user:"+str(session_id))





def _update_journey(journey_id, user_id, gym_id, routes_id, jsondata):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        cursor.execute(
            "update " + JOURNEYS_TABLE + " set user_id = ?, gym_id = ?, routes_id = ?, jsondata = ? where id=?",
            [str(user_id), str(gym_id), str(routes_id), json.dumps(jsondata), str(journey_id)])

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("updated climbing session for user:" + str(user_id))



