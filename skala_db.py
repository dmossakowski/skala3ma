

import json
import os
import glob
import random
from datetime import datetime, date, timedelta
import time
from io import BytesIO

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

from collections import Counter
import tracemalloc
import sqlite3 as lite
import uuid
import copy
from threading import RLock
import csv

import requests

sql_lock = RLock()
from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context

import logging
from dotenv import load_dotenv


load_dotenv()

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

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
CHALLENGE_TABLE = "challenges"
IMG_TABLE = "images"

def init():
    logging.info('initializing skala_db...')

    if not os.path.exists(DATA_DIRECTORY):
        os.makedirs(DATA_DIRECTORY)


    if os.path.exists(DATA_DIRECTORY):
        db = lite.connect(COMPETITIONS_DB)

        # ptype 0-public
        cursor = db.cursor()

        cursor.execute('''CREATE TABLE if not exists ''' + COMPETITIONS_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null, 
                       jsondata json)''')

        cursor.execute('''CREATE TABLE if not exists ''' + USERS_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       email text not null, 
                       jsondata integer not null,  
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + GYM_TABLE + '''(
                               id text NOT NULL UNIQUE, 
                               routesid text not null, 
                               jsondata json not null, 
                               added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + ROUTES_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       gym_id text NOT NULL, 
                       jsondata json,
                       added_at DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + ROUTES_CLIMBED_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       competitionId text not null, 
                       climberId text not null, 
                       routes json not null, 
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + IMG_TABLE + ''' 
                        (id text not null primary key, 
                        picture BLOB not null, 
                        source TEXT not null)''')


        #cursor.execute('''CREATE TABLE if not exists ''' + CHALLENGE_TABLE + '''(
         #                      id text NOT NULL UNIQUE,
          #                     type text not null,
           #                    climberId text not null,
            #                   jsondata json not null,
             #                  added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        db.commit()
        #add_testing_data()

        #print('loading routes from  ' + COMPETITIONS_DB)
        #routes = add_nanterre_routes()


        #user_authenticated_fb("c1", "Bob Mob", "bob@mob.com",
         #                  "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

        #user_authenticated_fb("c1", "Bob Mob2", "bob@mob.com",
         #                  "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

        #user_authenticated_fb("c2", "Mary J", "mary@j.com",
         #                  "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")


        print('created ' + COMPETITIONS_DB)
    


def _add_competition(compId, competition):
    if compId is None:
        compId = str(uuid.uuid4().hex)

    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        cursor.execute("INSERT INTO " + COMPETITIONS_TABLE +
                       "(id, jsondata, added_at) VALUES"+
                        " (?, ?, datetime('now')) ",
                       [compId, json.dumps(competition)])

        logging.info('competition added: '+str(compId))
    finally:
        db.commit()
        db.close()
        sql_lock.release()


#internal method.. not locked!!!
def _update_competition(compId, competition):

    if compId is None:
        raise ValueError("cannot update competition with None key");
    db = lite.connect(COMPETITIONS_DB)

    cursor = db.cursor()

    cursor.execute("update  " + COMPETITIONS_TABLE + " set jsondata=? where id=?  ",
                   [json.dumps(competition), compId])

    #logging.info('updated competition: '+str(compId))
    db.commit()
    db.close()


def delete_competition(compId):

    if compId is None:
        raise ValueError("cannot delete competition with None key");
    db = lite.connect(COMPETITIONS_DB)

    cursor = db.cursor()

    cursor.execute("delete from " + COMPETITIONS_TABLE + " where id=?  ",
                   [compId])

    db.commit()
    db.close()





def get_competition(compId):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    one = cursor.execute(
        '''SELECT jsondata FROM ''' + COMPETITIONS_TABLE + ''' where id=? LIMIT 1;''',[compId])
    one = one.fetchone()

    if one is None or one[0] is None:
        return None
    else:
        competition = json.loads(one[0])
        return competition


def get_competitions_for_email(email):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    cursor.execute("SELECT DISTINCT json_extract(competitions.jsondata,'$.id') FROM competitions, json_tree(competitions.jsondata, '$.climbers') WHERE json_tree.key='email' AND json_tree.value=?;", [email])

    # Extract the competition ids from the query results
    competition_ids = [row[0] for row in cursor.fetchall()]

    return competition_ids




def get_all_competitions():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT jsondata FROM ''' + COMPETITIONS_TABLE + ''' order by added_at desc ;''')

    comps = {}
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            comp = row[0]
            comp = json.loads(row[0])
            comps[comp['id']] = comp

    return comps


def get_user(id):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    one = cursor.execute(
        '''SELECT jsondata FROM ''' + USERS_TABLE + ''' where id=? LIMIT 1;''',[id])
    one = one.fetchone()


    if one is None or one[0] is None:
        return None

    if one[0] is not None:
        return json.loads(one[0])
    else:
        return None



def get_user_by_email(email):

    if email is None:
        return None
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    one = cursor.execute(
        '''SELECT jsondata FROM ''' + USERS_TABLE + ''' where email=? LIMIT 1;''', [email])
    one = one.fetchone()

    if one is None or one[0] is None:
        return None

    user = json.loads(one[0])
    if user.get('email') is None:
        user['email'] = email

    return user


def get_all_user_emails():

    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT email FROM ''' + USERS_TABLE + ''' order by email ;''')
    emails = []
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            emails.append(row[0])
    return emails


def get_all_competition_ids():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT id FROM ''' + COMPETITIONS_TABLE + ''' ;''')
    ids = []
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            ids.append(row[0])
    return ids







def upsert_user(user):
    try:
        sql_lock.acquire()
        existing_user = None
        email = user.get('email')
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        if email is not None:
            existing_user = get_user_by_email(email)
            if existing_user is None:
                _add_user(None, email, user)
                logging.info('added user id ' + str(email))
            else:
                existing_user.update(user)
                _update_user(user['id'], email, existing_user)
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))
        return existing_user



def user_authenticated_fb(fid, name, email, picture):
    try:
        sql_lock.acquire()
        user = get_user_by_email(email)
        _common_user_validation(user)
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if user is None:
            newuser = {'fid': fid, 'fname': name, 'email': email, 'fpictureurl': picture }
            _add_user(None, email, newuser)
            _common_user_validation(newuser)
            logging.info('added fb user id ' + str(email))
        else:
            u = {'fid': fid, 'fname': name, 'email': email, 'fpictureurl': picture}
            user.update(u)
            _update_user(user['id'], email, user)
            logging.info('updated user id ' + str(email))
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))


def user_authenticated_google(name, email, picture):
    try:
        sql_lock.acquire()
        user = get_user_by_email(email)
        _common_user_validation(user)
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if user is None:
            newuser = {'gname': name, 'email': email, 'gpictureurl': picture }
            _common_user_validation(newuser)
            _add_user(None, email, newuser)
            logging.info('added google user id ' + str(email))
        else:
            u = {'gname': name, 'email': email, 'gpictureurl': picture}
            user.update(u)
            _update_user(user['id'], email, user)
            logging.info('updated google user id ' + str(email))
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))


def _common_user_validation(user):
    if user is None:
        return

    permissions = user.get('permissions')
    if permissions is None:
        permissions = get_permissions(user)
        user['permissions'] = permissions


# returns base empty permissions dictionary
# who can create new competition? gym admins?
def get_permissions(user):
    if user is None:
        return _generate_permissions()

    if user.get('permissions') is None:
        user['permissions'] = _generate_permissions()

    if user.get('email') == 'dmossakowski@gmail.com':
        user['permissions']['godmode'] = True
        user['permissions']['general'] = ['create_competition', 'edit_competition', 'update_routes']
        user['permissions']['competitions'] = ['abc','def','ghi']
        user['permissions']['gyms'] = ['1']

    return user['permissions']


def _generate_permissions():
    return {
        "godmode": False,
        "general": [], # crud_competition crud_gym
        "users":[''],
        "competitions":['abc','def'], # everyone has ability to modify these test competitions
        "gyms":[] # contains gym ids
            }


def has_permission_for_competition(competitionId, user):
    permissions = get_permissions(user)
    huh = competitionId in permissions['competitions']
    return competitionId in permissions['competitions'] or session['name'] == 'David Mossakowski'


def has_permission_for_gym(gym_id, user):
    permissions = get_permissions(user)
    huh = gym_id in permissions['gyms']
    return gym_id in permissions['gyms'] or session['name'] == 'David Mossakowski'


def add_user_permission(user, permission):
    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        permissions = user.get('permissions')
        if permissions is None:
            permissions = _generate_permissions()
            user['permissions'] = permissions

        if permission not in permissions['general']:
            permissions['general'].append(permission)
        _update_user(user['id'], user['email'], user)
        logging.info('updated user id ' + str(user['email']))

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info(str(permission)+" done with user:"+str(user['email']))
        return user



# modify permission to edit specific competition to a user
def modify_user_permissions_to_competition(user, competition_id, action="ADD"):
    return _modify_user_permissions(user, competition_id, 'competitions', action)


def modify_user_permissions_to_gym(user, gym_id, action="ADD"):
    return _modify_user_permissions(user, gym_id, 'gyms', action)


# modify permission to edit specific competition to a user
def _modify_user_permissions(user, item_id, permission_type, action="ADD"):
    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        permissions = user.get('permissions')
        if permissions is None:
            permissions = _generate_permissions()
            user['permissions'] = permissions

        if action == "ADD":
            if item_id not in permissions[permission_type]:
                permissions[permission_type].append(item_id)
                _update_user(user['id'], user['email'], user)
                logging.info('added user permissions id ' + str(user['email'])+ ' type='+str(permission_type)+
                     ' action='+str(action))
        elif action == "REMOVE":
            permissions[permission_type].remove(item_id)
            _update_user(user['id'], user['email'], user)
            logging.info('removed user permissions id ' + str(user['email'])+ ' type='+str(permission_type)+
                     ' action='+str(action))
        else:
            raise ValueError("Unknown action parameter. Only valid values are ADD or REMOVE")
        

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(user['email']))
        return user





# this overwrites details from competition registration to the main user entry
# these details will be used for next competition registration
# these details are deemed the most recent and correct
def user_registered_for_competition(climberId, name, firstname, lastname, email, sex, club, category):
    user = get_user_by_email(email)

    if climberId is None:
        climberId = str(uuid.uuid4().hex)

    newclimber = {}
    newclimber['id'] = climberId
    newclimber['name'] = name
    newclimber['firstname'] = firstname
    newclimber['lastname'] = lastname
    newclimber['sex'] = sex
    newclimber['club'] = club
    newclimber['category'] = category

    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if user is None:
            _common_user_validation(newclimber)
            _add_user(climberId, email, newclimber)
            climber = newclimber
            logging.info('added user id ' + str(email))
        else:
            user.update(newclimber)
            _update_user(climberId, email, user)
            logging.info('updated user id ' + str(email))

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(name))
        #return climber



def _add_user(climberId, email, climber):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    if climberId is None:
        climberId = str(uuid.uuid4().hex)
        climber['id'] = climberId
    cursor.execute("INSERT  INTO " + USERS_TABLE +
                   "(id, email, jsondata, added_at) " +
                   " values (?, ?, ?, datetime('now')) ",
                   [str(climberId), email, json.dumps(climber)])
    logging.info('added user id ' + str(email))
    db.commit()
    db.close()


def _update_user(climberId, email, climber):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    if climberId is None:
        climberId = str(uuid.uuid4().hex)
        climber['id'] = climberId
    cursor.execute("UPDATE " + USERS_TABLE + " set jsondata=? where email =? ",
                   [json.dumps(climber), str(email)])
    logging.info('updated user id ' + str(email))
    db.commit()
    db.close()







def _get_gyms():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT jsondata FROM ''' + GYM_TABLE + ''' ;''')

    gyms = {}
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            #comp = row[0]
            gym = json.loads(row[0])
            gyms[gym['id']] = gym

    db.close()
    #for gymid in gyms:
    #    routes = _get_routes(gyms[gymid]['routesid'])
    #    gyms[gymid]['routes'] = routes

    return gyms


def _get_gym(gymid):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT jsondata FROM ''' + GYM_TABLE + ''' where id=? ;''',[gymid])

    gym = {}
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            #comp = row[0]
            gym = json.loads(row[0])
            #gyms[gym['id']] = gym

    db.close()
    #routes = _get_routes(gym['routesid'])
    #gym['routes'] = routes
    return gym


# should gym_id be added to ouput?
def get_routes_by_gym_id(gym_id):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT id,jsondata FROM ''' + ROUTES_TABLE + ''' where gym_id=? ;''', [gym_id])

    allroutes = {}
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            #comp = row[0]
            id = row[0]
            routes = json.loads(row[1])
            routes['id'] = id
            if routes.get('name') is None:
                routes['name'] = ''
            allroutes[routes['id']] = routes

    db.close()
    return allroutes


def get_gym_by_routes_id(routesid):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''select a.jsondata from gyms a, routes b where b.id = ? and a.id=b.gym_id;''', [routesid])

    one = rows.fetchone()
    db.close()
    if one is not None and one[0] is not None:
        return json.loads(one[0])


    return None



def get_all_routes_ids():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT id, gym_id FROM ''' + ROUTES_TABLE + '''  ;''')

    routes = []
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            #comp = row[0]
            #routes = json.loads(row[0])

            routes.append({'id':row[0],'gym_id':row[1]})
            #gyms[gym['id']] = gym

    db.close()
    return routes


def _get_routes(routesid):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    one = cursor.execute(
        '''SELECT jsondata, gym_id FROM ''' + ROUTES_TABLE + ''' where id=? LIMIT 1;''', [routesid])
    one = one.fetchone()
    db.close()

    if one is None or one[0] is None:
        return None

    routes = json.loads(one[0])
    routes['gym_id'] = one[1]
    return routes


def _add_gym(gymid, routesid, gym):
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()
    jsondata = json.dumps(gym)
    cursor.execute("INSERT INTO " + GYM_TABLE + " (id, routesid, jsondata, added_at ) "
                                                   "values ( ?, ?, ?, datetime('now'))",
                   [str(gymid), str(routesid),  jsondata])

    logging.info('added gym: '+str(jsondata))

    db.commit()
    db.close()


def _delete_routes_by_gymid(gymid):
    if gymid is None:
        return
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()
    cursor.execute("delete from " + ROUTES_TABLE + " where gym_id=?",
                   [str(gymid)])

    logging.info('deleted routes for gym: '+str(gymid))

    db.commit()
    db.close()


def _delete_gym(gymid):
    if gymid is None:
        return
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()
    cursor.execute("delete from " + GYM_TABLE + " where id=?",
                   [str(gymid)])

    logging.info('deleted gym: '+str(gymid))

    db.commit()
    db.close()


def _update_gym_routes(gymid, routesid, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    #db.in_transaction
    cursor = db.cursor()

    cursor.execute("update " + GYM_TABLE + " set  routesid = ? , jsondata = ? , added_at=datetime('now' ) where id=?",
                   [ str(routesid), json.dumps(jsondata), str(gymid)])

    logging.info('updated gym with routes: '+str(jsondata))

    db.commit()
    db.close()


def _update_gym(gymid, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    #db.in_transaction
    cursor = db.cursor()

    cursor.execute("update " + GYM_TABLE + " set jsondata = ? , added_at=datetime('now' ) where id=?",
                   [json.dumps(jsondata), str(gymid)])

    logging.info('updated gym: '+jsondata['name'])

    db.commit()
    db.close()


def _add_routes(routesid, gym_id, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()

    cursor.execute("INSERT INTO " + ROUTES_TABLE + " (id, gym_id, jsondata, added_at ) "
                                                   "values (?, ?, ?, datetime('now'))",
                   [str(routesid), str(gym_id), json.dumps(jsondata)])

    logging.info('added routes: '+str(jsondata))
    db.commit()
    db.close()


def _update_routes(routesid, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()

    cursor.execute("Update " + ROUTES_TABLE + " set  jsondata = ? where id = ?  ",
                                                   [json.dumps(jsondata), str(routesid)])

    logging.info('updated route: '+str(routesid))
    db.commit()
    db.close()


def save_image(img_id, logourl):
    logourl_response = requests.get(logourl)

    picture = lite.Binary(logourl_response.content)
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()

    cursor.execute('''INSERT INTO ''' +IMG_TABLE+'''  (id, picture, source) VALUES (?, ?, ?)''',
                   [img_id, picture, logourl])
    db.commit()
    db.close()


def get_image(img_id):
# This can only serve one image at a time, so match by id
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    cursor.execute("select picture from " +IMG_TABLE+" WHERE id = ?", (img_id,))
    result = cursor.fetchone()
    image_bytes = result[0]

    bytes_io = BytesIO(image_bytes)
    return bytes_io


if __name__ == '__main__':
    init()
    #library = loadLibraryFromFiles()
    #getOrphanedTracks(library)


