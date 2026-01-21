

import json
import os
import glob
import random
from datetime import datetime, date, timedelta, timezone
import time
from io import BytesIO
from src.Gym import Gym
from src.RouteSet import RouteSet
from src.User import User

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
import sqlite3 as lite
import uuid
import requests

from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context

import logging


import threading
import logging

# Create a global logging RLock
sql_lock = threading.RLock()

class DatabaseLock:
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

print("DATA_DIRECTORY="+str(DATA_DIRECTORY))

SPOTIFY_APP_ID = os.getenv('SPOTIFY_APP_ID')

print("SPOTIFY_APP_ID="+str(SPOTIFY_APP_ID))


ENV_VAR = os.getenv('ENV_VAR')

print("ENV_VAR="+str(ENV_VAR))


LINKED_VAR = os.getenv('LINKED_VAR')

print("LINKED_VAR="+str(LINKED_VAR))




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

    with DatabaseLock(sql_lock):
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        cursor.execute("INSERT INTO " + COMPETITIONS_TABLE +
                       "(id, jsondata, added_at) VALUES"+
                        " (?, ?, datetime('now')) ",
                       [compId, json.dumps(competition)])
        db.commit()
        db.close()
        logging.info('competition added: '+str(compId))
    


#internal method.. not locked!!!
# used when saving competiton details in admin
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
    email = email.lower()
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    cursor.execute("SELECT DISTINCT json_extract(competitions.jsondata,'$.id') FROM competitions, json_tree(competitions.jsondata, '$.climbers') WHERE json_tree.key='email' AND json_tree.value=? order by added_at desc", [email])

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

def get_all_gyms():
    return _get_gyms()

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
    method_start_time = time.time()
    if email is None:
        return None
    email = email.lower()
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    update_start_time = time.time()

    one = cursor.execute(
        '''SELECT jsondata FROM ''' + USERS_TABLE + ''' where lower(email) = ? LIMIT 1;''', [email])
    
    update_end_time = time.time()
    update_duration = update_end_time - update_start_time
    
    one = one.fetchone()
    db.close()

    if one is None or one[0] is None:
        return None

    user = json.loads(one[0])
    if user.get('email') is None:
        user['email'] = email

    method_duration = time.time() - method_start_time
    #logging.debug(f'get_user_by_email - in {update_duration:.4f}s ; user id {email} in {method_duration:.4f}s')
    
    return user


def get_users_by_gym_id(gym_id):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT jsondata FROM ''' + USERS_TABLE + ''' where json_extract(jsondata, '$.gymid')=? ;''', [gym_id])

    users = []
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            user = json.loads(row[0])
            users.append(user)

    return users


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


def get_all_users():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT id, jsondata FROM ''' + USERS_TABLE )

    users = []
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            user = json.loads(row[1])
            users.append(user)

    return users


def search_all_users(search_string):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()

    query = '''
    SELECT jsondata FROM ''' + USERS_TABLE + '''
    WHERE (lower(trim(json_extract(jsondata, '$.fullname'))) LIKE lower(trim(?))
    OR lower(trim(json_extract(jsondata, '$.firstname'))) LIKE lower(trim(?))
    OR lower(trim(json_extract(jsondata, '$.lastname'))) LIKE lower(trim(?))
    OR lower(trim(json_extract(jsondata, '$.nick'))) LIKE lower(trim(?)))
    AND json_extract(jsondata, '$.is_confirmed') = true
    LIMIT 10;
    '''
    
    search_pattern = f'%{search_string}%'
    rows = cursor.execute(query, [search_pattern, search_pattern, search_pattern, search_pattern])
    
    users = []
    if rows is not None:
        for row in rows.fetchall():
            user = json.loads(row[0])
            users.append(user)
    
    return users




def get_users_with_competition_id(competition_id):
    # Connect to the database
    conn = lite.connect(COMPETITIONS_DB)
    cursor = conn.cursor()

    # Enable the JSON1 extension
    #conn.enable_load_extension(True)
    #conn.execute('SELECT load_extension("mod_spatialite")')
    
    # Query to retrieve users with the specified competition ID in their permissions
    query = """
    SELECT jsondata
    FROM climbers, json_tree(climbers.jsondata, '$.permissions.competitions')
    WHERE json_tree.value = ?
    """
    cursor.execute(query, (competition_id,))
    users = cursor.fetchall()

    # List to store users with the specified competition ID in their permissions
    filtered_users = [json.loads(user[0]) for user in users]

    # Close the database connection
    conn.close()

    return filtered_users



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






# need to check so that anonymous user registering for a competition
#  is not able to overwrite an actual user
def upsert_user(user):
    method_start_time = time.time() 
    
    try:
        sql_lock.acquire()
        existing_user = None
        email = user.get('email')
        #db = lite.connect(COMPETITIONS_DB)
        #cursor = db.cursor()

        if email is not None:
            email = email.lower()
            update_duration = 1
            existing_user = get_user_by_email(email)
            if existing_user is None:
                _add_user(None, email, user)
                logging.info(' added user id ' + str(email))
            else:
                existing_user.update(user)
                _update_user(user['id'], email, existing_user)
                logging.info(' updated user id ' + str(email))
    except Exception as e:
        logging.error(f"Error in upsert_user for email {email}: {e}")
   
    finally:
        #db.commit()
        #db.close()
        sql_lock.release()
        method_duration = time.time() - method_start_time
        logging.info(f'upsert_user - in {update_duration:.4f}s ; user id {email} in {method_duration:.4f}s')
    
        return existing_user



def user_authenticated_fb(fid, name, email, picture):
    try:
        sql_lock.acquire()
        email = email.lower()
        user = get_user_by_email(email)
        _common_user_validation(user)
        #db = lite.connect(COMPETITIONS_DB)
        #cursor = db.cursor()
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
    except Exception as e:
        logging.error(f"Error in user_authenticated_fb for email {email}: {e}")
   
    finally:
        #db.commit()
        #db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))


def user_authenticated_google(name, email, picture):
    try:
        sql_lock.acquire()
        email = email.lower()
        user = get_user_by_email(email)
        _common_user_validation(user)
        #db = lite.connect(COMPETITIONS_DB)
        #cursor = db.cursor()
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
    except Exception as e:
        logging.error(f"Error in user_authenticated_google for email {email}: {e}")
    finally:
        #db.commit()
        #db.close()
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
        return User.generate_permissions()

    if user.get('permissions') is None:
        user['permissions'] = User.generate_permissions()

    if user.get('email') == 'dmossakowski@gmail.com':
        user['permissions']['godmode'] = True
        user['permissions']['general'] = ['create_competition', 'edit_competition', 'update_routes']
        user['permissions']['competitions'] = ['abc','def','ghi']
        user['permissions']['gyms'] = ['1']

    return user['permissions']




def has_permission_for_competition(competitionId, user):
    permissions = get_permissions(user)
    huh = competitionId in permissions['competitions']
    return competitionId in permissions['competitions'] or permissions['godmode'] == True


def has_permission_for_gym(gym_id, user):
    permissions = get_permissions(user)
    huh = gym_id in permissions['gyms']
    return gym_id in permissions['gyms'] or permissions['godmode'] == True


# Add general permission if it already doesn't exist
# user is a user dictionary
# permission is a string
def add_user_permission(user, permission):
    try:
        sql_lock.acquire()
        #db = lite.connect(COMPETITIONS_DB)
        #cursor = db.cursor()
        permissions = user.get('permissions')
        if permissions is None:
            permissions = User.generate_permissions()
            user['permissions'] = permissions

        if permission not in permissions['general']:
            permissions['general'].append(permission)
        _update_user(user['id'], user['email'], user)
        logging.info('updated user id ' + str(user['email']))
    except Exception as e:
        logging.error(f"Error in add_user_permission for email {user.get('email')}: {e}")
 
    finally:
        #db.commit()
        #db.close()
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
    if user is None:
        raise ValueError("User cannot be None")
    try:
        sql_lock.acquire()
        #db = lite.connect(COMPETITIONS_DB)
        #cursor = db.cursor()
        permissions = user.get('permissions')
        if permissions is None:
            permissions = User.generate_permissions()
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
    except Exception as e:
        logging.error(f"Error in _modify_user_permissions for email {user.get('email')}: {e}")
        raise ValueError("Unknown action parameter. Only valid values are ADD or REMOVE")
        
    finally:
        #db.commit()
        #db.close()
        sql_lock.release()
        logging.info("done with user:"+str(user['email']))
        return user


# this overwrites details from competition registration to the main user entry
# these details will be used for next competition registration
# these details are deemed the most recent and correct
# this should not be called when registering an anonmymous user as they could provide any details
# and thus overwrite the actual, confirmed user details
def user_registered_for_competition(climberId, name, firstname, lastname, email, sex, club, club_id, dob):
    email = email.lower()
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
    newclimber['club_id'] = club_id
    newclimber['dob'] = dob

    try:
        sql_lock.acquire()
        if user is None:
            _common_user_validation(newclimber)
            _add_user(climberId, email, newclimber)
            climber = newclimber
            logging.info('added user id ' + str(email))
        else:
            user.update(newclimber)
            _update_user(climberId, email, user)
            logging.info('updated user id ' + str(email))
    except Exception as e:
        logging.error(f"Error in user_registered_for_competition for email {email}: {e}")
 
    finally:
        sql_lock.release()
        logging.info("done with user:"+str(name))
        #return climber


def _add_user(climberId, email, climber):
    email = email.lower()
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    if climberId is None:
        climberId = str(uuid.uuid4().hex)
        climber['id'] = climberId
        climber['created_on'] = datetime.now(timezone.utc).isoformat()
    cursor.execute("INSERT  INTO " + USERS_TABLE +
                   "(id, email, jsondata, added_at) " +
                   " values (?, ?, ?, datetime('now')) ",
                   [str(climberId), email, json.dumps(climber)])
    logging.info('added user id ' + str(email))
    db.commit()
    db.close()
    return climber


def _update_user(climberId, email, climber):
    # Start timing for the entire method
    method_start_time = time.time()

    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    email = email.lower()

    update_start_time = time.time()
    if climberId is None:
        if (climber.get('id') is None):
            climberId = str(uuid.uuid4().hex)
            climber['id'] = climberId
            cursor.execute("UPDATE " + USERS_TABLE + " set id=?, jsondata=? where email =? ",
                   [str(climberId), json.dumps(climber), str(email)])
        else:
            logging.warning(f"climberId is None and climber['id'] is None for email {email}")
    else:
        climberId = climber['id']
        cursor.execute("UPDATE " + USERS_TABLE + " set jsondata=? where lower(email) =? ",
                   [ json.dumps(climber), str(email)])
    
    # End timing for the update query
    update_end_time = time.time()
 
    # Calculate duration for the update query
    update_duration = update_end_time - update_start_time
    
    db.commit()
    db.close()
     # End timing for the entire method
    method_end_time = time.time()
   
    # Calculate duration for the entire method
    method_duration = method_end_time - method_start_time
    #logging.info(f'query executed in {update_duration:.4f} seconds ; user id {email} in {method_duration:.4f} seconds (total method duration)')
    
    return climber


def _get_gyms(status=None):
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
            if status is None or gym.get('status') is None or gym.get('status') >= status:
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


def _get_gyms_by_ids(gym_ids, status=None):
    gyms = {}
    if not gym_ids:
        return gyms

    placeholders = ','.join(['?'] * len(gym_ids))
    query = f'SELECT id, jsondata FROM {GYM_TABLE} WHERE id IN ({placeholders})'

    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    try:
        cursor.execute(query, gym_ids)
        rows = cursor.fetchall()
        for row in rows:
            gym_id, jsondata = row
            gym = json.loads(jsondata)
            if status is None or gym.get('status') == status:
                gyms[gym_id] = gym
    except Exception as e:
        logging.error(f"Error in _get_gyms_by_ids for email : {e}")
 
    finally:
        db.close()

    return gyms



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



def get_gym_by_gym_name(gym_name):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''select jsondata  from gyms where lower(trim(json_extract(jsondata, '$.name'))) like lower(trim(?));''', [gym_name])

    one = rows.fetchone()
    db.close()
    if one is not None and one[0] is not None:
        return json.loads(one[0])


    return None


def search_gym_by_name_address(search_string):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()

    query = '''
    SELECT jsondata FROM ''' + GYM_TABLE + '''
    WHERE (lower(trim(json_extract(jsondata, '$.name'))) LIKE lower(trim(?)) 
    OR lower(trim(json_extract(jsondata, '$.address'))) LIKE lower(trim(?))) 
    LIMIT 10;
    '''
    
    search_pattern = f'%{search_string}%'
    rows = cursor.execute(query, [search_pattern, search_pattern])
    
    users = []
    if rows is not None:
        for row in rows.fetchall():
            user = json.loads(row[0])
            users.append(user)
    
    return users


def search_gym_by_owner(owner_id):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()

    query = '''
    SELECT jsondata FROM ''' + GYM_TABLE + '''
    WHERE lower(trim(json_extract(jsondata, '$.added_by'))) = lower(trim(?));
    '''
    
    rows = cursor.execute(query, [owner_id])
    
    gyms = []
    if rows is not None:
        for row in rows.fetchall():
            gym = json.loads(row[0])
            gyms.append(gym)
    
    return gyms


def get_gym_by_ref_id(ref_id):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''select jsondata  from gyms where lower(trim(json_extract(jsondata, '$.ref_id'))) like lower(trim(?));''', [ref_id])

    one = rows.fetchone()
    db.close()
    if one is not None and one[0] is not None:
        return json.loads(one[0])


    return None


def get_all_gym_names():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    gym_names = []

    try:
        rows = cursor.execute(
            '''SELECT json_extract(jsondata, '$.name') FROM gyms'''
        )

        gym_names = [row[0] for row in rows.fetchall() if row[0] is not None]
    except Exception as e:
        logging.error(f"Error retrieving gym names: {e}")
    finally:
        db.close()

    return gym_names




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


def get_routes_by_id(routesid):
    routes = _get_routes(routesid)
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


def delete_routes(routesid):
    if routesid is None:
        return
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()
    cursor.execute("delete from " + ROUTES_TABLE + " where id=?",
                   [str(routesid)])

    logging.info('deleted routes: '+str(routesid))

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

    logging.info('updated gym with routes: '+str(routesid))

    db.commit()
    db.close()


def _update_gym(gymid, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    #db.in_transaction
    cursor = db.cursor()

    cursor.execute("update " + GYM_TABLE + " set jsondata = ?  where id=?",
                   [json.dumps(jsondata), str(gymid)])

    logging.info('updated gym: '+jsondata['name'])

    db.commit()
    db.close()


def _add_routes(routesid, gym_id, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    #db.in_transaction
    cursor = db.cursor()

    cursor.execute("INSERT INTO " + ROUTES_TABLE + " (id, gym_id, jsondata, added_at ) "
                                                   "values (?, ?, ?, datetime('now'))",
                   [str(routesid), str(gym_id), json.dumps(jsondata)])

    logging.info('added routes: '+str(jsondata))
    db.commit()
    db.close()


def _update_routes(routesid, jsondata):
    db = lite.connect(COMPETITIONS_DB)

    #db.in_transaction
    cursor = db.cursor()
    cursor.execute("BEGIN")
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



#####################################
# migration and one time use methods

# sample query to get non confirmed users
# select email  from climbers  where lower(trim(json_extract(jsondata, '$.is_confirmed'))) like '0' ;
def update_gym_data(reference_data):
    # Connect to the database
    logging.info("-----  checking if clubs exist in db")
    # check if all gyms from the local reference list are in the database  
    # we try to retrieve by gym name but also by ref_id in case the gym name has changed
    # this check by gym name should be removed in the future and only ref_id should be used
    for ref_id, club_name in reference_data.get('clubs').items():
        gym = get_gym_by_gym_name(club_name)
        if gym is not None:
            logging.info(f"Club '{club_name}' exists with ID: {gym.get('id')} ref_id='{ref_id}'")
            if gym.get('ref_id') is None:
                gym['ref_id'] = ref_id
                _update_gym(gym.get('id'), gym)
        else:
            gym = get_gym_by_ref_id(ref_id)

            if gym is not None:
                logging.info(f"Club '{club_name}' ref_id='{ref_id}' exists with ID: {gym.get('id')}")
            else:
                logging.warning(f"gym doesn't exist in db: {club_name} ref_id='{ref_id}' ")
                route_set = RouteSet()
                route_set.generate_dummy_routes(14)

                gym_id = str(uuid.uuid4().hex)
                gym = Gym(
                    gymid=gym_id,
                    routesid=route_set.get_id(),
                    name=club_name,
                    added_by="admin",
                    logo_img_id=None,
                    homepage=None,
                    address=None,
                    organization='FSGT',
                    routesA=None
                )
                gym.set_ref_id(ref_id)
                
                _add_routes(route_set.get_id(), gym_id, route_set.get_routes())
                _add_gym(gym_id, route_set.get_id(), gym.get_gym_json()) 

    # Retrieve all gyms from the GYM_TABLE
    conn = lite.connect(COMPETITIONS_DB)
    cursor = conn.cursor()
    
    cursor.execute('''SELECT id, jsondata FROM ''' + GYM_TABLE + ''' ;''')
    gyms = cursor.fetchall()

    for gym in gyms:
        gym_id, jsondata = gym
        gym_data = json.loads(jsondata)

        if 'added_by' in gym_data:
            email = gym_data['added_by']

            # Retrieve the user ID corresponding to the email address
            cursor.execute('''SELECT id FROM ''' + USERS_TABLE + ''' WHERE email = ?''', (email,))
            user = cursor.fetchone()

            if user is not None:
                user_id = user[0]

                # Update the added_by field with the user ID
                gym_data['added_by'] = user_id

                # Convert the updated gym data back to JSON
                updated_jsondata = json.dumps(gym_data)

                # Update the jsondata field in the GYM_TABLE
                cursor.execute('''UPDATE ''' + GYM_TABLE + ''' SET jsondata = ? WHERE id = ?''', (updated_jsondata, gym_id))

        if 'status' not in gym_data or gym_data.get('status') is None:
            gym_data['status'] = reference_data.get('gym_status').get('confirmed')

            # Convert the updated gym data back to JSON
            updated_jsondata = json.dumps(gym_data)

            # Update the jsondata field in the GYM_TABLE
            cursor.execute('''UPDATE ''' + GYM_TABLE + ''' SET jsondata = ? WHERE id = ?''', (updated_jsondata, gym_id))

        if 'organization' not in gym_data or gym_data.get('organization') is None:
            gym_data['organization'] = 'FSGT'

            # Convert the updated gym data back to JSON
            updated_jsondata = json.dumps(gym_data)

            # Update the jsondata field in the GYM_TABLE
            cursor.execute('''UPDATE ''' + GYM_TABLE + ''' SET jsondata = ? WHERE id = ?''', (updated_jsondata, gym_id))

    cursor.execute('''SELECT id, jsondata FROM ''' + ROUTES_TABLE + ''' ;''')
    routesSets = cursor.fetchall()
    
    # set grades to lowercase
    for routeSet in routesSets:
        route_id = routeSet[0]
        jsondata = json.loads(routeSet[1])

        # Modify the jsondata as needed
        # Example: Add a new key-value pair
        routes = jsondata.get('routes')
        modified = False
        if routes is not None:
            for route in routes:
                grade = route.get('grade')
                if grade and any(char.isupper() for char in grade):
                    route['grade'] = grade.lower()
                    modified = True


        # Convert the jsondata back to a JSON string
        if modified:
            updated_jsondata = json.dumps(jsondata)
            cursor.execute('''UPDATE ''' + ROUTES_TABLE + ''' SET jsondata = ? WHERE id = ?''', (updated_jsondata, route_id))




    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def update_users_data():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    
    # Fetch all users
    cursor.execute(f'SELECT id, jsondata FROM {USERS_TABLE}')
    users = cursor.fetchall()
    
    for user_id, jsondata in users:
        user = json.loads(jsondata)
        
        # Check if any of the specified fields are not empty
        if user.get('fpictureurl') or user.get('gpictureurl') or user.get('fname') or user.get('fid') or user.get('gname'):
            user['is_confirmed'] = True
            
            # Update the user data in the database
            updated_jsondata = json.dumps(user)
            cursor.execute(f'UPDATE {USERS_TABLE} SET jsondata = ? WHERE id = ?', (updated_jsondata, user_id))
            
            # Update the user data in the database
            #updated_jsondata = json.dumps(user)
            #cursor.execute(f'UPDATE {USERS_TABLE} SET jsondata = ? WHERE id = ?', (updated_jsondata, user_id))
    # Commit the changes
    db.commit()
    db.close()


def _parse_date(date_str):
    formats = ["%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            formatted_date = parsed_date.strftime("%m-%d-%Y")
            return True, formatted_date
        except ValueError:
            continue
    return False, date_str


# competitions migration function
def update_competitions_data():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    
    # Fetch all competitions
    cursor.execute(f'SELECT id, jsondata FROM {COMPETITIONS_TABLE}')
    competitions = cursor.fetchall()
    for competition_id, jsondata in competitions:
        competition = json.loads(jsondata)
        
    
        
    db.commit()
    db.close()

if __name__ == '__main__':
    init()
    #library = loadLibraryFromFiles()
    #getOrphanedTracks(library)


