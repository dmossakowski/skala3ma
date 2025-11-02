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
from typing import List
try:
    from src.Activity import Activity
except ImportError:
    # If running in a context where src isn't a top-level package, adjust as needed.
    from .src.Activity import Activity  # type: ignore

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


def add_activity(user, gym, routesid, name, date):
    activity_id = str(uuid.uuid4().hex)

    gym_id = gym.get('id')
    #routes_id = gym.get('routesid')
    activity = {"id": activity_id, "gym_id": gym_id, "routes_id": routesid, "starttime": date, "name": name, 
        "gym_name": gym.get('name'), 
            "routes": []
               }
    # write this competition to db
    _add_activity(activity_id, user.get('id'), gym_id, routesid, date, activity)
    return activity_id


def get_activity(session_id) -> Activity | None:
    """Return an Activity domain object for the given session id.

    For backward compatibility with code expecting the raw dict, use get_activity_raw().
    """
    raw = _get_activity(session_id)
    if raw is None:
        return None
    try:
        return Activity.from_json(raw)
    except Exception as e:
        logging.warning(f"Failed to parse Activity {session_id}: {e}; returning None")
        return None

def get_activity_raw(session_id):
    """Legacy accessor returning the stored JSON dict for an activity."""
    return _get_activity(session_id)


def get_activities(user_id):
    return _get_activities_by_user_id(user_id)


def get_activities_by_date_by_user(date, user_id):
    return _get_activities_by_date_by_user_id(date, user_id)


def get_activities_by_gym_routes(gym_id, routes_id):
    try:
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        result = cursor.execute("SELECT jsondata FROM " + activities_TABLE + " WHERE gym_id = ? AND routes_id = ?",
                                [str(gym_id), str(routes_id)])
        activities = []
        if result is not None and result.arraysize > 0:
            for row in result.fetchall():
                activities.append(json.loads(row[0]))
        return activities
    finally:
        db.close()


# add an entry to an existing session
def add_activity_entry(activity_id, route, status, note, user_grade):
    """Add a route attempt to an activity using the domain model.

    Parameters:
      activity_id: str - the session/activity identifier
      route: dict - legacy route metadata dict (must contain at least 'id' and 'grade')
      status: str - attempt status (attempted|climbed|flashed)
      note: str - optional user note
      user_grade: str - optional proposed grade
    Returns: updated Activity as lean dict (with attempts + distinct routes)
    """
    from src.RouteAttempt import RouteAttempt  # local import to avoid circulars if any
    from src.Route import Route

    activity = get_activity(activity_id)
    if activity is None:
        return None

    # Build a Route object from incoming route dict (minimal fields tolerated)
    route_obj = Route(
        id=route.get('id', route.get('route_id', '')),
        routenum=str(route.get('routenum', '')),
        line=str(route.get('line', '')),
        colorfr=route.get('colorfr', ''),
        color1=route.get('color1', ''),
        color2=route.get('color2', ''),
        grade=route.get('grade', ''),
        color_modifier=route.get('color_modifier', 'solid'),
        name=route.get('name', ''),
        openedby=route.get('openedby', ''),
        opendate=route.get('opendate', ''),
        notes=route.get('notes', ''),
    )

    attempt = RouteAttempt.from_route(
        route_obj,
        status=status,
        user_grade=user_grade,
        note=note,
    )

    # Use Activity.add_route_attempt (appends to attempts list; legacy flattened handled on persist)
    activity.add_route_attempt(attempt)

    # Persist (default legacy flattened to maintain storage format)
    update_activity(activity)

    return activity.to_dict()


def update_activity(activity: Activity, *, legacy_flatten: bool = True) -> Activity | None:
    """Persist an Activity domain object.

    By default writes the legacy flattened representation (routes list with attempts merged) to avoid
    breaking existing stored format. Set legacy_flatten=False to store lean form with separate attempts.
    """
    if activity is None or not isinstance(activity, Activity):
        return None
    payload = activity.to_dict(legacy_flatten=legacy_flatten)
    _update_activity_jsondata(activity.id, payload)
    return activity

def update_activity_legacy(activity_id: str, activity_json: dict):
    """Backward compatible wrapper using original signature (activity_id, activity_json)."""
    if activity_id is None or activity_json is None:
        return None
    _update_activity_jsondata(activity_id, activity_json)
    return activity_json


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
    activity.delete_route_attempt(entry_id)
    # Persist changes
    update_activity(activity)  # default flattened persist
    return activity.to_dict()


def get_activities_by_routes_id(routes_id):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        # Query to retrieve activities that contain the given route_id
        cursor.execute(f"SELECT jsondata FROM {activities_TABLE} WHERE routes_id = ?", [str(routes_id)])
        rows = cursor.fetchall()

        matching_entries = []

        for row in rows:
            activity = json.loads(row[0])
            for session_entry in activity.get('routes', []):
                matching_entries.append(session_entry)

        return matching_entries

    finally:
        db.close()
        sql_lock.release()


def get_activity_routes_by_gym_id(gym_id):
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        # Query to retrieve activities that contain the given route_id
        cursor.execute(f"SELECT jsondata FROM {activities_TABLE} WHERE gym_id = ?", [str(gym_id)])
        rows = cursor.fetchall()

        matching_entries = []

        for row in rows:
            activity = json.loads(row[0])
            for session_entry in activity.get('routes', []):
                matching_entries.append(session_entry)

        return matching_entries

    finally:
        db.close()
        sql_lock.release()


def get_activities_by_gym_id(gym_id) -> List[Activity]:
    """Return list of Activity domain objects for a given gym_id.

    Each row's JSON is parsed via Activity.from_json, which also constructs structured RouteAttempt objects
    from the legacy flattened 'routes' list.
    """
    activities: List[Activity] = []
    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        cursor.execute(f"SELECT jsondata FROM {activities_TABLE} WHERE gym_id = ?", [str(gym_id)])
        for row in cursor.fetchall():
            raw = json.loads(row[0])
            try:
                activities.append(Activity.from_json(raw))
            except Exception as e:
                logging.warning(f"Failed to parse Activity for gym {gym_id}: {e}")
        return activities
    finally:
        db.close()
        sql_lock.release()


def get_activities_all_anonymous():
    try:
        sql_lock.acquire()

        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        # Query to retrieve activities that contain the given route_id
        cursor.execute(f"SELECT jsondata FROM {activities_TABLE} order by added_at desc")
        rows = cursor.fetchall()

        matching_entries = []

        for row in rows:
            activity = json.loads(row[0])
            activity.pop('user_id')
            activity.pop('name')
            matching_entries.append(activity)

        return matching_entries

    finally:
        db.close()
        sql_lock.release()


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



