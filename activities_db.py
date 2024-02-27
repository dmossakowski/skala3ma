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

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

activities_TABLE = "activities"


route_finish_status = {0: "attempt", 1: "flash", 2: "redpoint", 3: "toprope"}


def init():
    logging.info('initializing skala_activity...')

    if os.path.exists(DATA_DIRECTORY) and os.path.exists(COMPETITIONS_DB):
        db = lite.connect(COMPETITIONS_DB)

        # ptype 0-public
        cursor = db.cursor()

        cursor.execute('''CREATE TABLE if not exists ''' + activities_TABLE + '''(
                       id text NOT NULL UNIQUE,
                       user_id text NOT NULL, 
                       gym_id text NOT NULL,
                       routes_id text NOT NULL,
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null,  
                       jsondata json NOT NULL
                       )''')
        db.commit()

        print('created ' + activities_TABLE)


def add_activity(user, gym, name, date):
    activity_id = str(uuid.uuid4().hex)

    gym_id = gym.get('id')
    routes_id = gym.get('routesid')
    activity = {"id": activity_id, "gym_id": gym_id, "routes_id": routes_id, "starttime": date, "name": name, 
        "gym_name": gym.get('name'), 
            "routes": []
               }
    # write this competition to db
    _add_activity(activity_id, user.get('id'), gym_id, routes_id, date, activity)
    return activity_id





def get_activity(session_id):
    return _get_activity(session_id)


def get_activities(user_id):
    return _get_activities_by_user_id(user_id)

def get_activities_by_date_by_user(date, user_id):
    return _get_activities_by_date_by_user_id(date, user_id)


# add an entry to an existing session
def add_activity_entry(activity_id, route, status, note, user_grade):
    entry_id = str(uuid.uuid4().hex)

    route_id = route.get('id')  
    grade = route.get('grade')

    activity = get_activity(activity_id)
    session_entry = {"id": entry_id, "route_id": route_id, "status": status, "note": note, 
                     "grade": grade, "user_grade": user_grade,
                   }
    session_entry = {**route, **session_entry}
    activity.get('routes').append(session_entry)
    # write this competition to db
    _update_activity(activity_id, activity.get("user_id"), activity.get("gym_id"), activity.get("routes_id"), activity);

    return activity

def update_activity(activity_id, activity_json):
    if activity_json is None or activity_id is None:
        return None
    # write this competition to db
    _update_activity_jsondata(activity_id, activity_json)


def delete_activity(activity_id):
    activity = get_activity(activity_id)

    if activity is None:
        return None

    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        cursor.execute("delete from " + activities_TABLE + " where id =? ",
                       [str(activity_id)])
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("deleted activity for user:"+str(activity_id))

    return activity



def delete_activity_route(activity_id, entry_id):
    activity = get_activity(activity_id)

    if activity is None:
        return None
    for route_index, route in enumerate(activity['routes']):
        if route['id'] == entry_id:
            activity['routes'].pop(int(route_index))
    _update_activity(activity_id, activity.get("user_id"), activity.get("gym_id"), activity.get("routes_id"), activity);

    return activity


def _add_activity(activity_id, user_id, gym_id, routes_id, date, jsondata):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        jsondata['id']=activity_id
        jsondata['user_id']=user_id
        jsondata['gym_id']=gym_id
        jsondata['routes_id']=routes_id
        jsondata['date']=date

        cursor.execute("INSERT INTO " + activities_TABLE + " (id, user_id, gym_id, routes_id, added_at, jsondata ) "
                                                    "values (?, ?, ?, ?, ?, ?)",
                       [str(activity_id), str(user_id), str(gym_id), str(routes_id), date, json.dumps(jsondata)])
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("added climbing session for user:"+str(user_id))


def _update_activity_jsondata(activity_id, new_jsondata):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        # Convert new_jsondata to a JSON string
        new_jsondata_str = json.dumps(new_jsondata)

        cursor.execute(f"UPDATE {activities_TABLE} SET jsondata = ? WHERE id = ?", (new_jsondata_str, str(activity_id)))
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info(f"Updated jsondata for activity: {activity_id}")


def _get_activity(activity_id):
    try:
        #sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        result = cursor.execute("select jsondata from " + activities_TABLE + " where id =? ",
                       [str(activity_id)])
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


def _get_activities_by_user_id(user_id):
    try:
        #sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        result = cursor.execute("select jsondata from " + activities_TABLE + " where user_id =? order by added_at desc",
                       [str(user_id)])
        #result = result.fetchall()
        activities=[]
        if result is not None and result.arraysize > 0:
            for row in result.fetchall():
                # comp = row[0]
                activities.append(json.loads(row[0]))
                # gyms[gym['id']] = gym
        return activities

    finally:
        db.commit()
        db.close()
        #sql_lock.release()
        #logging.info("retrieved climbing session for user:"+str(session_id))


def _get_activities_by_date_by_user_id(date, user_id):
    try:
        #sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        result = cursor.execute("select jsondata from " + activities_TABLE + " where user_id =? and added_at =? ",
                       (str(user_id), date))
        #result = result.fetchall()
        activities=[]
        if result is not None and result.arraysize > 0:
            for row in result.fetchall():
                # comp = row[0]
                activities.append(json.loads(row[0]))
                # gyms[gym['id']] = gym
        return activities

    finally:
        db.commit()
        db.close()
        #sql_lock.release()
        #logging.info("retrieved climbing session for user:"+str(session_id))



def _update_activity(activity_id, user_id, gym_id, routes_id, jsondata):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        cursor.execute(
            "update " + activities_TABLE + " set user_id = ?, gym_id = ?, routes_id = ?, jsondata = ? where id=?",
            [str(user_id), str(gym_id), str(routes_id), json.dumps(jsondata), str(activity_id)])

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("updated climbing session for user:" + str(user_id))



