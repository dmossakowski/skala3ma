

import json
import os
import glob
import random
from datetime import datetime, date, timedelta
import time
import numpy as np
import pandas as pd
import numpy.random
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import plotly
import plotly.graph_objects as go
import plotly.express as px
import tracemalloc
import sqlite3 as lite
import uuid
import copy
from threading import RLock

sql_lock = RLock()
from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context

from sklearn.cluster import KMeans

from collections import defaultdict

from matplotlib.figure import Figure
from sklearn.preprocessing import MinMaxScaler

from functools import lru_cache
import logging
from dotenv import load_dotenv



load_dotenv()

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

# ID, date, name, location
COMPETITIONS_TABLE = "competitions"
# ID, name, club, m/f, list of climbs
CLIMBERS_TABLE = "climbers"
ROUTES_TABLE = "routes"
ROUTES_CLIMBED_TABLE = "routes_climbed"
GYM_TABLE = "gym_table"
#comps = {}
#climbers = {}

emptyResults = {"M":{ "0":[], "1":[], "2":[]}, "F":{"0":[], "1":[], "2":[] }}


def addCompetition(compId, name, date, gym):
    if compId is None:
        compId = str(uuid.uuid4())

    #comps[id] = { "name":name, "date" :date, "gym":gym, "climbers":{}}
    competition = {"id": compId, "name": name, "date": date, "gym": gym, "status":"preopen", "climbers": {},
                   "results": copy.deepcopy(emptyResults)}
    # write this competition to db
    add_competition(compId, name, date, gym, competition);

    return compId




# add climber to a competition
def addClimber(climberId, competitionId, email, name, club, sex, category=0):
    logging.info("adding climber "+str(climberId))
    if email is None:
        raise ValueError('Email cannot be None')

    if climberId is None:
        climberId = str(uuid.uuid4())

    try:
        category = int(category)
    except:
        raise ValueError('category must be an integer')

    if sex=='m' or sex=='M':
        sex='M'
    elif sex=='f' or sex=='F':
        sex='F'
    else:
        raise ValueError('Only valid values are mfMF')

    try:
        sql_lock.acquire()

        competition = get_competition(competitionId)
        climbers = competition['climbers']
        logging.info(climbers)

        for cid in climbers:
            if climbers[cid]['email']==email:
                return climbers[cid]

        climbers[climberId] = {"id":climberId, "email":email, "name":name, "club" :club, "sex":sex, "category":category, "routesClimbed":[], "score":0, "rank":0 }
        logging.info(competition)

        _update_competition(competitionId, competition)
    finally:
        sql_lock.release()

    return climbers[climberId]


def getCompetitions():
    return get_all_competitions()


def getClimber(competitionId, climberId):
    comp = get_competition(competitionId)
    return comp['climbers'][climberId]


def getCompetition(competitionId):
    print("retreiving competition"+str(competitionId))
    return get_competition(competitionId)
    #return comps[competitionId]


def addRouteClimbed(competitionId, climberId, routeNumber):
    #print(comps)
    #comp = comps[competitionId]
    try:
        sql_lock.acquire()

        comp = get_competition(competitionId)
        climber = comp['climbers'][climberId]
        if climber is None:
            return

        routes_climbed = climber['routesClimbed']
        #print (routes_climbed)
        routes_climbed.append(routeNumber)
        _update_competition(competitionId, comp)
    finally:
        sql_lock.release()
    return comp


def setRoutesClimbed(competitionId, climberId, routeList):
    try:
        sql_lock.acquire()

        comp = get_competition(competitionId)

        climber = comp['climbers'][climberId]

        if climber is None:
            return
        climber['routesClimbed'] = []
        for route in routeList:
            routes_climbed = climber['routesClimbed']
            #print(routes_climbed)
            routes_climbed.append(route)
        comp = recalculate(competitionId, comp)
        _update_competition(competitionId, comp)
    finally:
        sql_lock.release()

# calculates points per route per sex
# first loop counts how many times the route was climbed
# second loop iterates over this same list but then does 1000/times the route was climbed
def _getRouteRepeats(competitionId, sex, comp):
    pointsPerRoute = [0 for i in range(100)]
    for climber in comp['climbers']:
        if comp['climbers'][climber]['sex'] != sex:
            continue
        #print(climber)
        routesClimbed = comp['climbers'][climber]['routesClimbed']
        #print(routesClimbed)
        for r in routesClimbed:
            pointsPerRoute[r]=pointsPerRoute[r]+1

    logging.info("route repeats: ")
    logging.info(pointsPerRoute)

    for i, r in enumerate(pointsPerRoute):
        if r == 0 :
            pointsPerRoute[i]=1000
        else:
            pointsPerRoute[i]=1000/r
    logging.info("points per route: ")
    logging.info(pointsPerRoute)

    return pointsPerRoute



def recalculate(competitionId, comp=None):
    logging.info('calculating...')

    try:
        sql_lock.acquire()
        if comp is None:
            comp = get_competition(competitionId)
        comp['results'] = copy.deepcopy(emptyResults)
        for climberId in comp['climbers']:
            comp = _calculatePointsPerClimber(competitionId,climberId, comp)

        #rank climbers
        for climberId in comp['climbers']:
            try:
                climbersex = comp['climbers'][climberId]['sex']
                climbercat = str(comp['climbers'][climberId]['category'])

                comp['climbers'][climberId]['rank'] = comp['results'][climbersex][climbercat].index(comp['climbers'][climberId]['score'])+1
            except ValueError:
                comp['climbers'][climberId]['rank'] = -1

        results = comp['results']
        for sex in results:
            for cat in results[sex]:
                pointsA = results[sex][cat]
                if len(pointsA) == 0:
                    continue
                #pointsA.sort()
                #pointsA = results[sex][cat].sort()
                #results[sex][cat] = pointsA.sort()
        if comp is None:
            comp = _update_competition(competitionId, comp)
    finally:
        sql_lock.release()

    return comp


def _calculatePointsPerClimber(competitionId, climberId, comp):
    routesClimbed = comp['climbers'][climberId]['routesClimbed']
    sex = comp['climbers'][climberId]['sex']

    if sex == "M":
        routeRepeats = _getRouteRepeats(competitionId, "M", comp)
    elif sex == "F":
        routeRepeats = _getRouteRepeats(competitionId, "F", comp)
    else:
        return None;
    points = 0
    for i, v in enumerate(routesClimbed):
        points += routeRepeats[v]
        logging.info(str(climberId) + " route="+str(v) + " - route points=" + str(routeRepeats[v]) + " total points=" + str(points))

    comp['climbers'][climberId]['score'] = points
    climbersex = comp['climbers'][climberId]['sex']
    climbercat = str(comp['climbers'][climberId]['category'])
    pointsA = comp['results'][climbersex][climbercat]
    pointsA.append(points)
    pointsA.sort(reverse=True)
    comp['climbers'][climberId]['rank'] = pointsA.index(points)
    #(comp['results'][climbersex][climbercat]).append(points)

    logging.info("results" + str(climbersex)+str(climbercat)+ " add "+str(points))
    return comp


lru_cache.DEBUG = True


def init():
    logging.info('initializing competition engine...')

    if os.path.exists(DATA_DIRECTORY) and not os.path.exists(COMPETITIONS_DB):
        db = lite.connect(COMPETITIONS_DB)

        # ptype 0-public
        cursor = db.cursor()

        cursor.execute('''CREATE TABLE if not exists ''' + COMPETITIONS_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null, 
                       jsondata json)''')

        cursor.execute('''CREATE TABLE if not exists ''' + CLIMBERS_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       fid text,
                       gid text,  
                       name text,
                       fname text, 
                       gname text, 
                       nick text, 
                       sex text,
                       email text not null, 
                       fpictureurl text,
                       gpictureurl text,
                       role integer not null, 
                       isgod boolean not null check(role IN (0,1)), 
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + GYM_TABLE + '''(
                               id text NOT NULL UNIQUE, 
                               gymid text not null, 
                               gymname text not null, 
                               isadmin boolean not null check(isadmin IN (0,1)), 
                               added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + ROUTES_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       gymid text not null, 
                       routenum text not null, 
                       routedesc text not null, 
                       routegrade text not null, 
                       isadmin boolean not null check(isadmin IN (0,1)), 
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        cursor.execute('''CREATE TABLE if not exists ''' + ROUTES_CLIMBED_TABLE + '''(
                       id text NOT NULL UNIQUE, 
                       competitionId text not null, 
                       climberId text not null, 
                       routes json not null, 
                       added_at DATETIME DEFAULT CURRENT_TIMESTAMP not null)''')

        db.commit()
        add_testing_data()
        add_test_routes()
        user_authenticated_fb("c1", "Bob Mob", "bob@mob.com",
                           "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

        user_authenticated_fb("c1", "Bob Mob2", "bob@mob.com",
                           "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

        user_authenticated_fb("c2", "Mary J", "mary@j.com",
                           "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

        print('created ' + COMPETITIONS_DB)


def add_competition(compId, name, date, gym, competition):
    if compId is None:
        compId = str(uuid.uuid4())

    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        cursor.execute("INSERT  INTO " + COMPETITIONS_TABLE + " VALUES (?, datetime('now'), ?) ",
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

    logging.info('updated competition: '+str(compId))
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
        return json.loads(one[0])


def get_all_competitions():
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT jsondata FROM ''' + COMPETITIONS_TABLE + ''' ;''')

    comps = {}
    if rows is not None and rows.arraysize > 0:
        for row in rows.fetchall():
            comp = row[0]
            comp = json.loads(row[0])
            comps[comp['id']] = comp

    return comps


def get_climber(id):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    one = cursor.execute(
        '''SELECT * FROM ''' + CLIMBERS_TABLE + ''' where id=? LIMIT 1;''',[id])
    one = one.fetchone()


    if one is None or one[1] is None:
        return None

    if one[1] is not None:
        return one
    else:
        return None


def get_climber_by_email(email):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    one = cursor.execute(
        '''SELECT * FROM ''' + CLIMBERS_TABLE + ''' where email=? LIMIT 1;''',[email])
    one = one.fetchone()


    if one is None or one[0] is None:
        return None

    if one[0] is not None:
        return one[0]
    else:
        return None



def user_authenticated_fb(fid, name, email, picture):
    climber = get_climber_by_email(email)
    climberId = str(uuid.uuid4())

    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if climber is None:
            cursor.execute("INSERT  INTO " + CLIMBERS_TABLE +
                           "(id, fid, fname, email, fpictureurl, role, isgod, added_at) " +
                            " values (?,?,?,?, ?,?,?,datetime('now')) ",
                           [str(climberId), str(fid),  str(name), str(email), str(picture), 0, 0])
            logging.info('added user id ' + str(email))
        else:
            cursor.execute("UPDATE "+CLIMBERS_TABLE+" set fid = ?, fname= ?, fpictureurl=? where email =? ",
                           [str(fid), str(name), str(picture), str(email)])
            logging.info('updated user id ' + str(email))

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(name))




def user_registered_for_competition(climberId, name, email, sex):
    climber = get_climber_by_email(email)

    if climberId is None:
        climberId = str(uuid.uuid4())

    try:
        sql_lock.acquire()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if climber is None:
            cursor.execute("INSERT  INTO " + CLIMBERS_TABLE +
                           "(id, email, name, sex, role, isgod, added_at) " +
                            " values (?,?,?,?, ?,?,datetime('now')) ",
                           [str(climberId),  str(email), str(name), str(sex),  0, 0])
            logging.info('added user id ' + str(email))
        else:
            cursor.execute("UPDATE "+CLIMBERS_TABLE+" set sex = ?  where email =? ",
                           [str(sex), str(email)])
            logging.info('updated user id ' + str(email))

    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(name))




# select * from routes group by gymid order by max(added_at);
def get_route(gymid, routenum):
    db = lite.connect(COMPETITIONS_DB)
    cursor = db.cursor()
    count = 0
    rows = cursor.execute(
        '''SELECT * FROM ''' + CLIMBERS_TABLE +
        ''' where gymid=? and routenum=? group by gymid order by max(added_at) limit 1;''',
        [gymid, routenum])

    one = rows.fetchone()

    if one is None or one[1] is None:
        return None
    else:
        return one


def add_route(gymid, routenum, routedesc, routegrade):
    db = lite.connect(COMPETITIONS_DB)

    db.in_transaction
    cursor = db.cursor()

    cursor.execute("INSERT INTO " + ROUTES_TABLE + " VALUES (?,?,?,?,?,?, datetime('now')) ",
                   [str(uuid.uuid4()), str(gymid), str(routenum), str(routedesc),str(routegrade), 0])

    logging.info('added route: '+str(routenum))

    db.commit()
    db.close()







def add_test_routes():
    add_route("gym1", "0", "easy by dsm", "5A")
    #time.sleep(1)
    add_route("gym2", "0", "easy by dsm", "5A")
    #time.sleep(1)
    add_route("gym3", "0", "easy by dsm", "5A")
    #time.sleep(1)
    add_route("gym1", "0", "easy by dsm", "5C")
    #time.sleep(1)
    add_route("gym2", "0", "easy by dsm", "5C")
    #time.sleep(1)
    add_route("gym3", "0", "easy by dsm", "5C")
    #time.sleep(1)
    add_route("gym1", "1", "easy by dsm", "5B")
    #time.sleep(1)
    add_route("gym2", "1", "easy by dsm", "5B")
    #time.sleep(1)
    add_route("gym3", "1", "easy by dsm", "5B")
    #time.sleep(1)
    add_route("gym1", "1", "easy by dsm", "5C")
    #time.sleep(1)
    add_route("gym2", "1", "easy by dsm", "5C")
    #time.sleep(1)
    add_route("gym3", "1", "easy by dsm", "5C")
    #time.sleep(1)


def add_testing_data():
    addCompetition("abc", "FSGT 2021/2022", "20220101", "ESC 15")
    addCompetition("def", "FSGT 2021/2022", "20220207", "Tremblay")
    addCompetition("ghi", "FSGT 2021/2022", "20220312", "Roc 14")

    addClimber("c1", "abc", "c1@a.com", "Bob Mob", "Nanterre", "M")
    addClimber("c2", "abc", "c2@a.com", "Mary J", "Ville", "F")
    addClimber("c3", "abc", "c3@a.com", "Jean Li", "ESC15", "F")
    addClimber("c4", "abc", "c4@a.com", "Rose Rose", "Ville", "F")

    addClimber("c5", "abc", "c5@a.com", "Rudolf", "Nanterre", "M", 1)
    addClimber("c6", "abc", "c6@a.com", "Gary", "Ville", "m", 1)
    addClimber("c7", "abc", "c7@a.com", "Philomena", "ESC15", "F", 1)
    addClimber("c8", "abc", "c8@a.com", "Beatrice", "Ville", "F", 1)

    addClimber("c9", "abc", "c9@a.com", "Gianni", "Nanterre", "M", 2)
    addClimber("c10", "abc", "c10@a.com", "Monty", "Ville", "m", 2)
    addClimber("c11", "abc", "c11@a.com", "Rijka", "ESC15", "F", 2)
    addClimber("c12", "abc", "c12@a.com", "Salomona", "Ville", "F", 2)

    addClimber("c13", "abc", "c13@a.com", "Donny", "Nanterre", "M", 0)
    addClimber("c14", "abc", "c14@a.com", "Mark", "Ville", "m", 0)
    addClimber("c15", "abc", "c15@a.com", "Sonia", "ESC15", "F", 0)
    addClimber("c16", "abc", "c16@a.com", "Wilma", "Ville", "F", 0)

    setRoutesClimbed("abc", "c1", [2, 3, 4, 5, 7, 12, 17, 19, 24, 21, 24, 25, 26])
    addRouteClimbed("abc", "c1", 13)
    addRouteClimbed("abc", "c1", 14)
    addRouteClimbed("abc", "c1", 15)
    addRouteClimbed("abc", "c1", 16)

    setRoutesClimbed("abc", "c2", [2, 3, 4, 12, 13, 17, 24, 21, 24, 25, 26])
    setRoutesClimbed("abc", "c3", [1, 5, 6, 12, 13, 17,24, 25, 13, 15, 24])
    setRoutesClimbed("abc", "c4", [1, 13, 17, 24, 26, 52, 25, 34, 3, 4, 24])
    setRoutesClimbed("abc", "c5", [1, 13, 17, 14, 15, 16, 24, 25])
    setRoutesClimbed("abc", "c6", [1, 2, 3, 5, 7, 13, 14, 15, 15, 24, 25])
    setRoutesClimbed("abc", "c7", [1, 13, 14, 15, 16, 24, 25])
    setRoutesClimbed("abc", "c8", [2, 3, 12, 13, 14, 24, 25])

    setRoutesClimbed("abc", "c9", [2, 3, 12, 14, 24])
    setRoutesClimbed("abc", "c10", [2, 3, 4, 12, 13, 17, 18])
    setRoutesClimbed("abc", "c11", [2, 3, 4, 5, 12, 14, 24])
    setRoutesClimbed("abc", "c12", [2, 3, 4, 6, 4, 12])

    setRoutesClimbed("abc", "c13", [2, 3, 7, 8, 12, 15, 24])
    setRoutesClimbed("abc", "c14", [2, 3, 6, 7, 8, 12, 15, 17])
    setRoutesClimbed("abc", "c15", [2, 3, 4, 8, 12, 16, 17, 24])
    setRoutesClimbed("abc", "c16", [2, 3, 5, 12, 16, 17, 24])

    # competition def
    addClimber("c1", "def", "c1@a.com", "Bob Mob", "ESC15", "M")
    addClimber("c2", "def", "c2@a.com", "Ryan Pal", "Ville", "M")

    addClimber("c3", "def", "c3@a.com", "Jean Li", "ESC15", "F")
    addClimber("c4", "def", "c4@a.com", "Rose Rose", "Ville", "F")

    addClimber("c5", "def", "c5@a.com", "Rudolf", "Nanterre", "M", 1)
    addClimber("c6", "def", "c6@a.com", "Gary", "Ville", "m", 1)
    addClimber("c7", "def", "c7@a.com", "Philomena", "ESC15", "F", 1)
    addClimber("c8", "def", "c8@a.com", "Beatrice", "Ville", "F", 1)

    setRoutesClimbed("def", "c1", [1, 12, 24])
    setRoutesClimbed("def", "c2", [1, 12, 25])

    setRoutesClimbed("def", "c3", [1, 12, 24])
    setRoutesClimbed("def", "c4", [1 ,12, 25])

    setRoutesClimbed("def", "c5", [1, 12, 24])
    setRoutesClimbed("def", "c6", [1, 12, 25])

    setRoutesClimbed("def", "c7", [1, 12, 24])
    setRoutesClimbed("def", "c8", [1 ,12, 25])

    recalculate("abc")


#if __name__ == '__main__':
    #library = loadLibraryFromFiles()

    #getOrphanedTracks(library)


