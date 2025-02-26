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


import base64
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

#last 44 
clubs = {               
    40:"11C+",
    0:"APACHE" , 111:"Argenteuil Grimpe", 2:"AS Noiseraie Champy" , 
                       4:"ASG Bagnolet"  , 5:"Athletic Club Bobigny", 6:"Au Pied du Mur (APDM)" ,
                       7:"Chelles Grimpe"  , 8:"Cimes 19"  , 9:"CMA Plein Air", 
                       44: "Cordée 13",
                       10:"Faites le Mur - CPS10" , 
                       42:"CSMG Escalade - Gennevilliers",
                       11:"Dahu 91" , 
                       43: "EMA - Maisons-Alfort",
                       41:"EscaladA'sceaux",
                       39:"Escalade Populaire Montreuilloise",
                       12:"Entente Sportive Aérospatial Mureaux(ESAM)" ,
                       14:"ESC 11", 15:"ESC15"   ,16:"Espérance Sportive Stains",
                      17:"Grimpe 13"   ,
                      38:"Grimpe Fertoise Pays de Brie",
                      3:"Grimpe heureuse de Pierrefitte" ,
                      18:"Grimpe Tremblay Dégaine", 19:"GrimpO6"   ,
                      20:"Groupe Escalade Saint Thibault"  ,
                      21:"Le Mur 20"  ,
                      1:"Nanterre Grimpe"  ,
                      22:"Neuf-a-pic", 23:"Quatre +"  ,24:"ROC14"  , 25:"RSCC ESCALADE MONTAGNE RANDONNEE",
                      26:"RSC Montreuillois"   ,27:"SNECMA Sports Corbeil", 28:"SNECMA Sports Genevilliers"   ,
                      29:"Union Sportive Saint Arnoult", 30:"US Fontenay"   , 31:"US Ivry - Orme au Chat" , 32:"US Métro"  ,
                      33:"USMA", 34:"Vertical 12", 35:"Vertical Maubuée", 36:"Villejuif Altitude" 
                       
                        }




# created - only visible to admin or someone who has the right to see it
# open - visible and registration is possible
# inprogress - visible, can still register and can enter routes climbed
# scoring - cannot register, can enter routes, calculate and see results
# closed - cannot change routes and no need to recalculate
competition_status_created = 0
competition_status_open = 1
competition_status_inprogress = 2
competition_status_scoring = 3
competition_status_closed = 4
competition_status_archived = 5
competition_status_future = 5

competition_status = {"created":competition_status_created, "open":1, "inprogress":2, "scoring":3, "closed":4, "archived":5}


user_roles = ["none", "judge", "competitor", "admin"]

supported_languages = {"en_US":"English","fr_FR":"Francais","pl_PL":"Polski"}
first_default_language = "fr_FR"

competition_type_adult_fsgt = 0
competition_type_ado_fsgt = 1

competition_types = {"adult_fsgt":competition_type_adult_fsgt, "ado_fsgt":competition_type_ado_fsgt}

gym_status = {"created":0, "confirmed":1, "active":3, "inactive":4, "deleted":5}

reference_data = {"categories":categories, "categories_ado":categories_ado,
                   "clubs":clubs, "competition_status": competition_status, "colors_fr":colors,
                  "supported_languages":supported_languages, "route_finish_status": activities_db.route_finish_status,
                  "competition_types":competition_types, "gym_status":gym_status}


from src.email_sender import EmailSender

# Initialize EmailSender with necessary configurations
email_sender = EmailSender(
    reference_data=reference_data
)


# called from main_app_ui
def addCompetition(compId, added_by, name, date, routesid, max_participants, competition_type, instructions):
    if compId is None:
        compId = str(uuid.uuid4().hex)

    routes = skala_db.get_routes_by_id(routesid)
    gym = skala_db.get_gym_by_routes_id(routesid)

    if gym is None:
        raise ValueError('Gym not found')
    
    if (routes is None or len(routes)==0):
        raise ValueError('Routes not found')
    
    if max_participants is None:
        max_participants=80

    #sanitized_instruction = re.sub(r'[^\w\s]', '', instruction)

   
    competition = {"id": compId, "name": name, "date": date, "gym": gym['name'],"gym_id":gym['id'],
                   "routesid": routesid, "status": "preopen", "climbers": {},
                   "max_participants": max_participants,
                   "results": copy.deepcopy(CalculationStrategy.emptyResults),
                   "calc_type": CalculationStrategy.calc_type_fsgt1,
                   "competition_type":competition_type,
                   "status" : competition_status_created,
                   "routes": routes.get('routes'),
                   "instructions": instructions,
                   "added_by": added_by}
    # write this competition to db
    skala_db._add_competition(compId, competition);

    return compId


def update_competition_details(competition, name, date, instructions):
    competition['name']=name
    competition['date'] = date
    competition['instructions'] = instructions
    skala_db._update_competition(competition['id'], competition)
    return competition
    


def update_competition_routes(competition, routesid, force=False):
    # only update routes if it is different
    #if competition.get('routes') is None or competition.get('routesid') != routesid:
    competition['routesid'] = routesid
    routes = skala_db.get_routes_by_id(routesid)

    if (routes is None or len(routes)==0):
        logging.error('Routes not found '+str(competition.get('id')))
        return competition
        #raise ValueError('Routes not found')
    
    competition['routes'] = routes.get('routes')

    try:
        setRoutesClimbed2(competition)
    except:
        logging.error('error setting routes climbed2')
        pass
    
    skala_db._update_competition(competition['id'], competition)

    return competition


# add or register climber to a competition
def addClimber(climberId, competitionId, email, name, firstname, lastname, club, sex, category):
    logging.info("adding climber to competition "+str(climberId))
    if email is None:
        raise ValueError('Email cannot be None')
    email = email.lower()
    if climberId is None:
        climberId = str(uuid.uuid4().hex)

    try:
        category = int(category)
    except:
        raise ValueError('category must be an integer')

    if sex == 'm' or sex == 'M':
        sex = 'M'
    elif sex == 'f' or sex == 'F':
        sex = 'F'
    else:
        raise ValueError('Only valid values are mfMF')

    try:
        sql_lock.acquire()

        competition = get_competition(competitionId)
        climbers = competition['climbers']
        #logging.info(climbers)

        for cid in climbers:
            if climbers.get(cid).get('email').lower()==email.lower():
                #return climbers[cid]
                raise ValueError('User with email '+email+' already registered')

        climbers[climberId] = {"id":climberId, "email":email, "name":name, "firstname":firstname, "lastname":lastname,
                               "club" :club, "sex":sex, "category":category, "routesClimbed":[], "score":0, "rank":0,
                                "routesClimbed2":[], }
        #logging.info(competition)

        _update_competition(competitionId, competition)
    except Exception as e:
        logging.error(f'Error adding climber to the competition {email}: {str(e)}')
        raise
    finally:
        sql_lock.release()

    return climbers[climberId]


# remove or unregister climber from a competition
def removeClimber(climberId, competitionId):
    try:
        sql_lock.acquire()
        competition = get_competition(competitionId)

        climbers = competition['climbers']
        if climberId in climbers and competition['status'] in [competition_status_open]:
            del climbers[climberId]
            _update_competition(competitionId, competition)
    finally:
        sql_lock.release()


def get_climber_json(climberId, email, name, firstname, lastname, club, sex, category=0):
    climber_json = {"id": climberId, "email": email, "name": name, "firstname": firstname, "lastname": lastname,
                           "club": club, "sex": sex, "category": category, "routesClimbed": [], "score": 0, "rank": 0}



def getCompetitions():
    return get_all_competitions()


def getClimber(competitionId, climberId):
    comp = get_competition(competitionId)
    return comp['climbers'][climberId]


def getFlatCompetition(competitionId):
    print("retreiving flat competition " + str(competitionId))
    competition = get_competition(competitionId)

    for climberid in competition['climbers']:
        data = competition['climbers'][climberid]
        for i in range(100):
            if (i in competition['climbers'][climberid]['routesClimbed']):
                data['r' + str(i)] = 1
            else:
                data['r' + str(i)] = 0
    return competition


def getCompetition(competitionId):
    print("retreiving competition "+str(competitionId))
    return get_competition(competitionId)
 

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


# update each climber with routes they climbed
# the routes array is made of up the same entries as routes in gym
# routesClimbed2 is calculated from routes object set on competition (not from db based on routesid)
# returns the competition
# no db update
def setRoutesClimbed2(competition):
    if competition.get('routes') is None or competition.get('routesid') is None:
        raise ValueError('Routes on competition not found')
    
    for climber in competition['climbers']:
        climber = competition['climbers'][climber]
        climber['routesClimbed2'] = []
     
        if climber is None:
            return
        climber['routesClimbed2'] = []
        for route in climber['routesClimbed']:
            if competition.get('routes') is not None:
                for route2 in competition['routes']:
                    if str(route2.get('routenum')) == str(route):
                        climber['routesClimbed2'].append(route2)

    return competition
    


# update climber with a list of routes they climbed
# the list is a list of route numbers so the lowest number is 1 (not 0)
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


def update_competition(competitionId, competition):
    _update_competition(competitionId, competition)



def get_route_repeats(sex, comp):
    if comp['calc_type'] == CalculationStrategy.calc_type_fsgt0:
        return CalculationStrategyFsgt0._getRouteRepeats(None, sex, comp)
    else:
        return CalculationStrategyFsgt1._getRouteRepeats(None, sex, comp)


def recalculate(competitionId, comp=None):
    #logging.info('calculating...')
    try:
        sql_lock.acquire()
        if comp is None:
            comp = get_competition(competitionId)
            if comp is None:
                return
        
        # Choose the strategy based on the calculationType
        if comp['calc_type'] == CalculationStrategy.calc_type_fsgt0:
            strategy = CalculationStrategyFsgt0()
        elif comp['calc_type'] == 1:
            strategy = CalculationStrategyFsgt1()
        elif comp['calc_type'] == 'ffme0':
            strategy = CalculationStrategyFfme0()
        else:
            raise ValueError("Invalid calculationType")

        # Use the strategy to recalculate the competition
        strategy.recalculate(comp)
        if comp is None:
            comp = _update_competition(competitionId, comp)
    finally:
        sql_lock.release()

    return comp


# returns sorted arrays based on rank
def get_sorted_rankings(competition):
    
    
    rankings = {}
    rankings['F'] = []
    rankings['M'] = []
    rankings['0F'] = []
    rankings['1F'] = []
    rankings['2F'] = []
    rankings['0M'] = []
    rankings['1M'] = []
    rankings['2M'] = []
    rankings['A'] = []
    #rankings['club'] = []

    # scratch first
    for climberid in competition.get('climbers'):
        climber = competition.get('climbers').get(climberid)
        rank = int(climber['rank'])
        #rankings[climber['sex']].insert(rank-1, climber)

    # sort by awayPoints, then position; note the lambda uses a tuple
    a = competition.get('climbers').values()
    #clubs = set(competition.get('climbers')[k]['category'])

    clubs = reduce(lambda acc, c: acc.update({ competition['climbers'][c]['club'] :{"M":0, "F":0, "MC":0, "FC":0, "TOTAL":0 }})
                                        or acc if competition['climbers'][c]['club'] not in acc else acc,
                   competition.get('climbers'), {})

    # do not generate rankings for all users together for the fsgt0 calculation
    # because in fsgt0 points for each route are divided separately by men and woman
    # so it does not make sense to rank them together
    if (competition.get('calc_type') != CalculationStrategy.calc_type_fsgt0):
        for itemid in sorted(competition.get('climbers'),
                         key=lambda k: (competition.get('climbers')[k]['score']),
                         reverse=True):
            climber = competition.get('climbers').get(itemid)
            rankings['A'].append(climber)


    for itemid in sorted(competition.get('climbers'),
                         key=lambda k: (competition.get('climbers')[k]['sex'], competition.get('climbers')[k]['score']),
                         reverse=True):
        climber = competition.get('climbers').get(itemid)
        rankings[climber['sex']].append(climber)

    for itemid in sorted(competition.get('climbers'),
                         key=lambda k: (competition.get('climbers')[k]['sex'], competition.get('climbers')[k]['category'], competition.get('climbers')[k]['score']),
                         reverse=True):
        climber = competition.get('climbers').get(itemid)
        catcode = str(climber['category'])+str(climber['sex'])
        rankings[catcode].append(climber)
        sex = climber['sex']
        classement = len(rankings[catcode])

        if climber['score']==0:
            continue
        # add one point for each climber
        points = clubs[climber['club']][sex]
        clubs[climber['club']][sex] = points + 1

        if classement<6:
            points = clubs[climber['club']][sex+"C"]
            clubs[climber['club']][sex+"C"] = points + 6 - classement

    for clubname in clubs:
        total = clubs[clubname]['M']+clubs[clubname]['F']+clubs[clubname]['MC']+clubs[clubname]['FC']
        clubs[clubname]['TOTAL'] = total

    sortedclubs = []
    prevTotal = -1
    #prevClub
    rank = 0
    for club in sorted(clubs, key=lambda x:(clubs[x]['TOTAL'], clubs[x]['F']+clubs[x]['M'], clubs[x]['F']),reverse=True):
        if club in ['other','Autre club non répertorié']:
            continue
        clubs[club]['name'] = club
        if prevTotal != clubs[club]['TOTAL']:
            rank = rank + 1
            prevTotal = clubs[club]['TOTAL']
        else:
            if clubs[club]['M'] == clubs[prevClub]['M']:
                if clubs[club]['F'] < clubs[prevClub]['F']:
                    rank = rank + 1
            else:
                rank = rank + 1

        clubs[club]['rank'] = rank
        sortedclubs.append(clubs[club])
        prevClub = club

    rankings['club']=sortedclubs
    return rankings


def calculate_score(grades):
    points_per_grade = {
        '1': 1,
        '2': 4,
        '3': 16,
        '4a': 64,
        '4b': 256,
        '4c': 1024,
        '5a': 4096,
        '5a+': 8096,
        '5b': 16384,
        '5b+': 32384,
        '5c': 65536,
        '5c+': 125384,
        '6a': 262144,
        '6a+': 524288,
        '6b': 1048576,
        '6b+': 2097152,
        '6c': 4194304,
        '6c+': 8388608,
        '7a': 16777216,
        '7a+': 33554432,
        '7b': 67108864,
        '7b+': 134217728,
        '7c': 268435456,
        '7c+': 536870912,
        '8a': 1073741824,
        '8a+': 2147483648,
        '8b': 4294967296,
        '8b+': 8589934592,
        '8c': 17179869184,
        '8c+': 34359738368,
        '9a': 68719476736,
        '9a+': 137438953472,
        '9b': 274877906944,
        '9b+': 549755813888,
        '9c': 1099511627776
    }
    
    score = 0
    for i, grade in enumerate(grades):
        if grade in points_per_grade:
            points = points_per_grade[grade]
            if i > 0 and grades[i-1].endswith('+'):
                points /= 2
            score += points
    
    return score



def test_calcul():
    test_data = []
    test_data.append(['6a','2'])
    test_data.append(['4a','4b','5a','2'])
    test_data.append(['4a','4b','5a'])
    test_data.append(['4a','4b','6a','5a','2'])
    test_data.append(['4a','4b','6a','5b','2'])
    test_data.append(['4a','4b','6a','5a','7a'])

    


def avg(grades):
    # create a dictionary to convert grades to numbers
    grade_dict2 = {"1": 0, "2": 1, "3": 2, "4a": 3, "4b": 4, "4c": 5, "5a": 6, "5b": 7, "5c": 8, "6a": 9,
                  "6a+": 10, "6b": 11, "6b+": 12, "6c": 13, "6c+": 14, "7a": 15, "7a+": 16, "7b": 17, 
                  "7b+": 18, "7c": 19, "7c+": 20, "8a": 21, "8a+": 22, "8b": 23, "8b+": 24, "8c": 25, 
                  "8c+": 26, "9a": 27, "9a+": 28, "9b": 29, "9b+": 30, "9c": 31}
    grade_dict = {'1': 1, '2': 2, '3': 3, '4a': 4.1, '4b': 4.4, '4c': 4.7,
                    '5a': 5.2, '5b': 5.5, '5c': 5.8, '6a': 6.1, '6a+': 6.2, 
                    '6b': 6.4, '6b+': 6.5, '6c': 6.7, '6c+': 6.8, '7a': 7.1,
                    '7a+': 7.2, '7b': 7.4, '7b+': 7.5, '7c': 7.7, '7c+': 7.8,
                    '8a': 8.1, '8a+': 8.2, '8b': 8.4, '8b+': 8.5, '8c': 8.7, '8c+': 8.8,
                    '9a': 9.1, '9a+': 9.2, '9b': 9.5, '9b+': 9.6, '9c': 9.9}

    # convert grades to numbers
    nums = [grade_dict[g] for g in grades]
    # calculate the average number
    avg_num = sum(nums) / len(nums)
    avg_grade = ""

    # Convert the grades to numerical values and calculate the mean
    grade_sum = sum([grade_dict[grade] for grade in grades])
    mean_num = grade_sum / len(grades)
    mean_grade=''
    # convert the average number back to a grade
    for g, n in grade_dict.items():
        if n == round(avg_num):
            avg_grade= g
        if n == round(mean_num):
            mean_grade= g


    return {'avg':avg_grade,'avg_num':avg_num, 'mean':mean_grade, 'mean_num':mean_num}


def mean_climbing_grade(grades):
    # Define a dictionary to map the letter grades to numerical values
    grade_values = {'1': 1, '2': 2, '3': 3, '4a': 4.1, '4b': 4.4, '4c': 4.7,
                    '5a': 5.2, '5b': 5.5, '5c': 5.8, '6a': 6.1, '6a+': 6.2, 
                    '6b': 6.4, '6b+': 6.5, '6c': 6.7, '6c+': 6.8, '7a': 7.1,
                    '7a+': 7.2, '7b': 7.4, '7b+': 7.5, '7c': 7.7, '7c+': 7.8,
                    '8a': 8.1, '8a+': 8.2, '8b': 8.4, '8b+': 8.5, '8c': 8.7, '8c+': 8.8,
                    '9a': 9.1, '9a+': 9.2, '9b': 9.5, '9b+': 9.6, '9c': 9.9}

    # Convert the grades to numerical values and calculate the mean
    grade_sum = sum([grade_values[grade] for grade in grades])
    mean_grade = grade_sum / len(grades)

    return mean_grade



def calculate_average_score(routes):
    score_dict = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4a": 4.1,
        "4b": 4.2,
        "4c": 4.3,
        "5a": 5.1,
        "5b": 5.2,
        "5c": 5.3,
        "6a": 6.1,
        "6a+": 6.15,
        "6b": 6.2,
        "6b+": 6.25,
        "6c": 6.3,
        "6c+": 6.35,
        "7a": 7.1,
        "7a+": 7.15,
        "7b": 7.2,
        "7b+": 7.25,
        "7c": 7.3,
        "7c+": 7.35,
        "8a": 8.1,
        "8a+": 8.15,
        "8b": 8.2,
        "8b+": 8.25,
        "8c": 8.3,
        "8c+": 8.35,
        "9a": 9.1,
        "9a+": 9.15,
        "9b": 9.2,
        "9b+": 9.25,
        "9c": 9.3,
    }
    score_total = 0
    count = 0
    route_counts = {}
    for route in routes:
        if route in score_dict:
            if route in route_counts:
                route_counts[route] += 1
            else:
                route_counts[route] = 1
            count += 1
    for route, count in route_counts.items():
        score_total += score_dict[route] * count ** 0.5
    if count == 0:
        return 0
    else:
        return round(score_total / count * count ** 0.25, 2)


lru_cache.DEBUG = True


def init():
    logging.info('initializing competition engine...')

    skala_db.init()
    #user_authenticated_fb("c1", "Bob Mob", "bob@mob.com",
    #                       "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

    #user_authenticated_fb("c1", "Bob Mob2", "bob@mob.com",
    #                       "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

    #user_authenticated_fb("c2", "Mary J", "mary@j.com",
    #                       "https://platform-lookaside.fbsbx.com/platform/profilepic/?asid=10224632176365169&height=50&width=50&ext=1648837065&hash=AeTqQus7FdgHfkpseKk")

    activities_db.init()

    for competition in skala_db.get_all_competitions().values():
        _validate_or_upgrade_competition(competition)

    logging.info('created ' + COMPETITIONS_DB)

    logging.info("running user migrations - adding gymid to users...")
    emails = get_all_user_emails() # select email from climbers table
    for email in emails:
        user = get_user_by_email(email)
        if user is None:
            logging.info('no climber in db for email: '+str(email))
            continue
        if user.get('gymid') is None:
            if user.get('club') is not None:
                gym = skala_db.get_gym_by_gym_name(user['club'])
                if gym is not None:
                    user['gymid'] = gym['id']
                    logging.info('adding gymid: '+str(gym['id'])+' for user '+str(user['email']))
                    skala_db.upsert_user(user)
                elif user.get('club') == 'ROC 14':
                    user['gymid'] = '005d3b0d78b5477db673f6424b0fbeba'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'Entente Sportive de Nanterre':
                    user['gymid'] = '1'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'ESC XV':
                    user['gymid'] = '591a28aa8e924d25a3c9c0cc6a0c883f'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'US Ivry':
                    user['gymid'] = '8b797c6675934ad197b15d6f7950c8e2'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'RSC Champigny':
                    user['gymid'] = 'ca09c1dab6c04bb7b8e224bd9344d4c9'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'US Fontenay' or user.get('club') == 'USF Escalade':
                    user['gymid'] = '1a088f939d1b4a82a359bda05fed0f24'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'CPS 10 - Faites le mur':
                    user['gymid'] = '20605d959edc4bee8a212935973590e4'
                    skala_db.upsert_user(user)
                elif user.get('club') == 'AS Pierrefitte' or user.get('club') == 'Grimpe Heureuse de Pierrefitte':
                    user['gymid'] = 'a247c13c9ae54e898d2651cf7369145a'
                    skala_db.upsert_user(user)
                else:    
                    logging.info('no gym found for club: '+str(user['club'])+' for user '+str(user['email'])+' confirmed='+str(user.get('is_confirmed')))
        
            #user['gymid'] = ''
    skala_db.update_gym_data(reference_data)
    skala_db.update_users_data()




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


# this method is for migrating competitions to new format when available
# it is called from init method so on every start of the server
def _validate_or_upgrade_competition(competition):

    needs_updating = False
    if competition.get('status') is None or competition.get('status') not in competition_status.values():
        needs_updating = True
        competition['status'] = competition_status['created']

    #if competition.get('gym_id') is None:
     #   raise ValueError('gym_id is missing for competition '+str(competition['id']))

    if competition.get('max_participants') is None:
        competition['max_participants'] = 80
        needs_updating = True

    if competition.get('competition_type') is None:
        competition['competition_type'] = competition_type_adult_fsgt
        needs_updating = True


    if competition.get('calc_type') is None:
        competition['calc_type'] = CalculationStrategy.calc_type_fsgt0
        needs_updating = True

    if competition.get('routesid') is None:
        gym = get_gym(competition['gym_id'])
        competition['routesid'] = gym['routesid']

    #if competition.get('routes') is None:
     #   update_competition_details(competition, competition['name'], competition['date'], competition['routesid'], competition.get('instructions'))
    
    # do another check here for routes included in the competition against the routes in the gym
    # do a check that the length of the routesClimbed2 is the same as the length of the routesClimbed

    empty_routes_count = sum(1 for climber in competition['climbers'].values() if not climber.get('routesClimbed2'))
    if empty_routes_count == len(competition['climbers']) and competition.get('routes') is not None:
        competition = setRoutesClimbed2(competition)
        needs_updating = True
    
    if needs_updating:
        update_competition(competition['id'], competition)

    return competition


def get_all_competitions():
    return skala_db.get_all_competitions()

def get_all_competitions_using_routes(routesid):
    competitions = skala_db.get_all_competitions()

    competitions2 = []
    for competition in competitions.values():
        if competition.get('routesid') == routesid:
            logging.info('found competition '+str(competition.get('id'))+' using routes '+str(routesid))
            competitions2.append(competition)
    return competitions2


def get_all_gyms_using_routes(routesid):
    gyms = skala_db.get_all_gyms()

    gyms2 = []
    for gym in gyms.values():
        if gym.get('routesid') == routesid:
            logging.info('found gym '+str(gym.get('name'))+' using routes '+str(routesid))
            gyms2.append(gym)
    return gyms2




def get_competitions_by_year(year):
    """
    This function returns the list of competitions for the current year (actually season, e.g. 2023-2024).

    Args:
        year (int): The first year of the season (e.g. 2023)
        

    Returns:
        The list of competitions
    """
    competitions = get_all_competitions()
    competitions2 = {}
    if not year.isdigit():
        year = datetime.now().year

    # The sport season starts in September and ends in August.
    date_strt, date_end = datetime(int(year), 9, 1), datetime(int(year)+1, 8, 31)
    input_format = "%Y-%m-%d"
    
    for competition_id in competitions:
        competition = competitions.get(competition_id)
        competition_date = competition.get('date')
        try:
            if competition_date is None or len(competition_date)<2:
                parsered_date=date_end
            else:
                parsered_date = datetime.strptime(competition_date, input_format)
            if parsered_date >= date_strt and parsered_date <= date_end:
                competitions2[competition['id']] = competition

        except ValueError:
            print("This is the incorrect date string format.")

    return dict(sorted(competitions2.items(),
                         key=lambda x: x[1]['date'],
                         reverse=False))


def get_active_competitions():
    competitions = skala_db.get_all_competitions()
    #for key, competition in competitions.items:
     #   if competition.get('status')  in [competition_status_archived]:
      #       competitions.

    active_competitions = {key: competition for key,
                competition in competitions.items() if competition.get('status')  in [competition_status_archived]}

    return active_competitions


def get_user(id):
    return skala_db.get_user(id)


def get_user_by_email(email):
    return skala_db.get_user_by_email(email)


def get_all_user_emails():
    return skala_db.get_all_user_emails()


def get_all_competition_ids():
    return skala_db.get_all_competition_ids()


def get_category_from_dob(dob):
        if dob is None:
            return -1
        dob = datetime.strptime(dob, "%Y-%m-%d")
        # Calculate the age
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Determine the category based on age
        if 17 <= age <= 49:
            return 0
        elif 50 <= age <= 64:
            return 1
        elif age >= 65:
            return 2
        elif 12 <= age <= 13:
            return 0
        elif 14 <= age <= 15:
            return 1
        elif 16 <= age <= 17:
            return 2
        else:
            return -1  # Return -1 if age does not fit any category


                                    
def user_self_update(climber, name, firstname, lastname, nick, sex, club, gymid, dob):
    if climber is None:
        raise ValueError("Climber cannot be None")

    try:
        sql_lock.acquire()
        fullname = ""
        if firstname is not None and lastname is not None:
            fullname = firstname+" "+lastname

        newclimber = {'fullname': name, 'nick': nick, 'firstname':firstname, 'lastname':lastname,
                      'sex': sex, 'club': club, 'gymid': gymid, 'dob': dob}
        
        if club is not None:
            gym = skala_db.get_gym(gymid)
            if gym is not None:
                newclimber['gymid'] = gym.get('id')
            else:
                climber.pop('gymid', None)

        email = climber.get('email')
        email = email.lower()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if climber is None:
            skala_db._add_user(None, email, newclimber)
            logging.info('added user id ' + str(email))
        else:
            climber.update(newclimber)
            skala_db._update_user(climber['id'], email, climber)
            logging.info('updated user id ' + str(climber))
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))
        return climber


def upsert_user(user):
    try:
        sql_lock.acquire()
        existing_user = None
        email = user.get('email')
        email = email.lower()
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()

        if email is not None:
            existing_user = get_user_by_email(email)
            if existing_user is None:
                skala_db._add_user(None, email, user)
                logging.info('added user id ' + str(email))
            else:
                existing_user.update(user)
                skala_db._update_user(user['id'], email, existing_user)
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("upsert_user done with user:"+str(email))
        return existing_user


def user_authenticated_fb(fid, name, email, picture):
    try:
        sql_lock.acquire()
        user = get_user_by_email(email)
        email = email.lower()
        _common_user_validation(user)
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if user is None:
            newuser = {'fid': fid, 'fname': name, 'email': email, 'fpictureurl': picture }
            _common_user_validation(newuser)
            user = skala_db._add_user(None, email, newuser)
            logging.info('added fb user id ' + str(email))
        else:
            u = {'fid': fid, 'fname': name, 'email': email, 'fpictureurl': picture}
            user.update(u)
            user = skala_db._update_user(user['id'], email, user)
            logging.info('updated user id ' + str(email))
        return user
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))


def user_authenticated_google(name, email, picture):
    try:
        sql_lock.acquire()
        user = get_user_by_email(email)
        email = email.lower()
        _common_user_validation(user)
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if user is None:
            newuser = {'gname': name, 'email': email, 'gpictureurl': picture }
            _common_user_validation(newuser)
            user = skala_db._add_user(None, email, newuser)
            logging.info('added google user id ' + str(email))
        else:
            u = {'gname': name, 'email': email, 'gpictureurl': picture}
            user.update(u)
            user = skala_db._update_user(user['id'], email, user)
            logging.info('updated google user id ' + str(email))
        return user
    finally:
        db.commit()
        db.close()
        sql_lock.release()
        logging.info("done with user:"+str(email))


# this function is used to set or update password  
# it's also called each time a user authenticates using username/password
# this is so that the user is up to date (format, permissions, etc)
def user_authenticated(email, password):
    try:
        sql_lock.acquire()
        user = get_user_by_email(email)
        email = email.lower()
        
        _common_user_validation(user)
        db = lite.connect(COMPETITIONS_DB)
        cursor = db.cursor()
        if user is None:
            newuser = {'email': email, 'password': password, }
            _common_user_validation(newuser)
            user = skala_db._add_user(None, email, newuser)
            logging.info('added google user id ' + str(email))
        else:
            u = {'email': email, 'password': password}
            user.update(u)
            user = skala_db._update_user(user['id'], email, user)
            logging.info('update normal user ' + str(email))
        return user
    finally:
       
        sql_lock.release()
        

# this function is used to confirm a user and write them to the db
# the only way that this can be called if a user clicked on a confirmation link
# which means that the user has a valid email
def confirm_user(email):
    try:
        sql_lock.acquire()
        user = get_user_by_email(email)
        if user is not None and user.get('is_confirmed') == True:
            return user
        
        
        _common_user_validation(user)
        
        if user is None:
            newuser = {'email': email, 'is_confirmed': True}
            _common_user_validation(newuser)
            user = skala_db._add_user(None, email, newuser)
            logging.info('added confirmed user email' + str(email))
        else:
            user['is_confirmed'] = True
            user = skala_db._update_user(user['id'], email, user)
        
            #logging.info('normal user is confirmed ' + str(email))
        return user
    finally:
        sql_lock.release()



def _common_user_validation(user):
    if user is None:
        return

    permissions = user.get('permissions')
    if permissions is None:
        permissions = get_permissions(user)
        user['permissions'] = permissions

    is_confirmed = user.get('is_confirmed')
    if is_confirmed is None:
        user['is_confirmed'] = False
    if user.get('gpictureurl') is not None or user.get('fpictureurl') is not None:
        user['is_confirmed'] = True


# returns base empty permissions dictionary
# who can create new competition? gym admins?
# if this is the first user who logs in then this user becomes the godmode user
def get_permissions(user):
    if user is None:
        return User.generate_permissions()

    if user.get('permissions') is None:
        all_users = get_all_user_emails()
        if len(all_users)==0 or GODMODE == True:
            user['permissions'] = {}
            user['permissions']['godmode'] = True
            user['permissions']['general'] = ['create_gym','create_competition', 'edit_competition', 'update_routes']
            user['permissions']['competitions'] = ['abc','def','ghi']
            user['permissions']['gyms'] = ['1']
        else:
            user['permissions'] = User.generate_permissions()

    return user['permissions']




def has_permission_for_competition(competitionId, user):
    permissions = get_permissions(user)
    huh = competitionId in permissions['competitions']
    return competitionId in permissions['competitions'] or permissions['godmode'] == True


def add_user_permission_create_competition(user):
    skala_db.add_user_permission(user,'create_competition')


def add_user_permission_create_gym(user):
    skala_db.add_user_permission(user,'create_gym')

def add_user_permission_update_routes(user):
    skala_db.add_user_permission(user,'update_routes')

def add_user_permission_edit_competition(user):
    skala_db.add_user_permission(user,'edit_competition')


def has_permission_for_gym(gym_id, user):
    permissions = get_permissions(user)
    #huh = gym_id in permissions['gyms']
    return gym_id in permissions['gyms'] or permissions['godmode'] == True


# modify permission to edit specific competition to a user
def modify_user_permissions_to_competition(user, competition_id, action="ADD"):
    return skala_db.modify_user_permissions_to_competition(user, competition_id, action)


def remove_user_permissions_to_competition(user, competition_id):
    return skala_db.modify_user_permissions_to_competition(user, competition_id, "REMOVE")


def add_user_permissions_to_gym(user, gym_id):
    return skala_db.modify_user_permissions_to_gym(user, gym_id, "ADD")


def remove_user_permissions_to_gym(user, gym_id):
    return skala_db.modify_user_permissions_to_gym(user, gym_id, "REMOVE")


def can_create_competition(climber):
    if climber is None:
        return False
    permissions = climber.get('permissions')
    if 'create_competition' in permissions['general'] or permissions['godmode'] == True:
        return True
    return False
    


def can_edit_competition(climber, competition):
    permissions = climber.get('permissions')
    if permissions['godmode'] == True  \
        or ('edit_competition' in permissions['general'] \
        and competition['id'] in permissions['competitions']):
        return True
    return False


def can_edit_users(user):
    if user is None:
        return False
    permissions = user.get('permissions')
    if permissions['godmode'] == True:
        return True


def is_god(user):
    return user.get('permissions').get('godmode') == True

def competition_can_be_deleted(competition):
    climbers = competition.get('climbers')
    
    if climbers is not None and len(climbers)>0:
        return False
    if competition['status'] != competition_status_created:
        return False

    return True
    

# can update routes if:
# user has update_routes general permission
# competition is in scoring or inprogress status
# user has permission for the given competition
def can_update_routes(user, competition):
    permissions = user.get('permissions')

    if 'update_routes' in permissions['general'] \
            and competition['status'] in [competition_status_scoring, competition_status_inprogress]\
            and competition['id'] in permissions['competitions']:
        return True

    return False


# checks if user can register for a competition
def can_register(user, competition):
    if competition is None:
        raise ValueError('competition cannot be None')

    if user is not None:
        climbers = competition['climbers']
        for cid in climbers:
            if climbers[cid]['email']==user['email']:
                return 'error5321'

    if len(competition['climbers']) >= 200:
        return 'error5323'

    # competition is in the correct state then allow
    if competition['status'] in [competition_status_open, competition_status_scoring, competition_status_inprogress]:
        return ""
    else:
        return 'error5322'


def competition_accepts_registrations(competition):
        # competition is in the correct state then allow
    return competition['status'] in [competition_status_open, competition_status_scoring, competition_status_inprogress]


# checks if user can register for a competition
def is_registered(user, competition):
    if competition is None:
        raise ValueError('competition cannot be None')

    if user is not None:
        climbers = competition['climbers']
        for cid in climbers:
            if climbers.get(cid).get('id')==user['id']:
                return True

    return False


# checks if user can unregister from a competition
def can_unregister(user, competition):
    if competition is None:
        raise ValueError('competition cannot be None')

    if competition['status'] not in [competition_status_open, competition_status_scoring, competition_status_inprogress]:
        return False
    
    if user is not None:
        climbers = competition['climbers']
        for cid in climbers :
            if climbers.get(cid).get('email').lower()==user['email'].lower():
                return True

    return False


def can_edit_gym(user, gym):
    if user is None or gym is None: 
        return False
    permissions = user.get('permissions')
    if gym['id'] in permissions['gyms'] or permissions['godmode'] == True:
        return True
    return False


def can_create_gym(user):
    permissions = user.get('permissions')
    if 'create_gym' in permissions['general'] or permissions['godmode'] == True:
        return True
    return False


# this overwrites details from competition registration to the main user entry
# these details will be used for next competition registration
# these details are deemed the most recent and correct
def user_registered_for_competition(climberId, name, firstname, lastname, email, sex, club, dob):
    skala_db.user_registered_for_competition(climberId, name, firstname, lastname, email, sex, club, dob)


def update_gym_routes(gymid, routesid, jsondata):
    skala_db._update_gym_routes(gymid, routesid, jsondata)


def update_gym(gymid, jsondata):
    skala_db._update_gym(gymid, jsondata)


def update_routes(routesid, jsondata):
    skala_db._update_routes(routesid, jsondata)


def get_gym(gymid):
    gym = None
    try:
        sql_lock.acquire()
        gym = skala_db._get_gym(gymid)
    finally:
        sql_lock.release()
        logging.info("retrieved gym by id  "+str(gymid))
        return gym


def get_gyms(status=None):
    gyms = None
    try:
        sql_lock.acquire()
        gyms = skala_db._get_gyms(status)
    except Exception as e:
        logging.error('error getting gyms: '+str(e))
    finally:
        sql_lock.release()
        logging.info("retrieved all gyms  ")
        return gyms


def get_gyms_by_ids(ids):
    gyms = None
    try:
        sql_lock.acquire()
        gyms = skala_db._get_gyms_by_ids(ids)
    finally:
        sql_lock.release()
        logging.info("retrieved gyms by ids: " + str(ids))
    return gyms


def get_routes(routesid):
    if routesid is None:
        # generate routes
        #return generate_dummy_routes(100)
        raise ValueError('routesid cannot be None')
    else:
        routes = skala_db._get_routes(routesid)
        if routes is None:
            return None

        if type(routes) == list:
            routesdict = {"id":routesid, "routes":routes}
            skala_db._update_routes(routesid, routesdict)
            routes = routesdict
        
        return routes


def get_route(routesid, route_id):
    routes = get_routes(routesid)
    if routes is None:
        return None
    routes = routes['routes']
    for route in routes:
        if route['id'] == route_id:
            return route
    return None


def get_routes_by_gym_id(gym_id):
    return skala_db.get_routes_by_gym_id(gym_id)


def get_all_routes_ids():
    return skala_db.get_all_routes_ids()


def add_gym(user, gymid, routesid, name, logo_img_id=None, homepage=None, address=None, organization=None, routesA=None):
    if gymid is None:
        gymid = str(uuid.uuid4().hex)

    gymjson = get_gym_json(gymid, routesid, name, user['id'], logo_img_id, homepage, address, organization, routesA)
    update_gym_status(gymjson, reference_data.get('gym_status').get('created'))
    skala_db._add_gym(gymid, routesid, gymjson)

    gym_permissions = user['permissions']['gyms']
    gym_permissions.append(gymid)
    skala_db.upsert_user(user)

    return gymjson


def delete_gym(gym_id):
    if gym_id is None:
        return
    try:
        sql_lock.acquire()
        skala_db._delete_gym(gym_id)
        skala_db._delete_routes_by_gymid(gym_id)
    finally:
        sql_lock.release()
        logging.info("deleted gym and routes for "+gym_id)


def delete_routes(routes_id):
    if routes_id is None:
        return    
    try:
        sql_lock.acquire()
        c1 = get_all_competitions_using_routes(routes_id)
        c2 = get_all_gyms_using_routes(routes_id)
        if len(c1) == 0 and len(c2) == 0:
            try:
                logging.info('deleting routes' + routes_id)
                
                skala_db.delete_routes(routes_id)
                jsonobject = {"status": "success", "label": "routes_deleted"}
            except Exception as e:
                logging.error(f'Error deleting routes {id}: {str(e)}')
                jsonobject = {"status": "error", "label": "exception_deleting_routes", "message": str(e)}
        else:
            # Extract id and name for competitions
            competitions = [{'id': comp['id'], 'name': comp['name']} for comp in c1]
            
            # Extract id and name for gyms
            gyms = [{'id': gym['id'], 'name': gym['name']} for gym in c2]
            
            jsonobject = {
                "status": "error",
                "label": "cannot_delete_routes",
                "competitions": competitions,
                "gyms": gyms
            }

        
    finally:
        sql_lock.release()
        logging.info("deleted routes for "+routes_id)
        return jsonobject



#routesid is the default routes to display
#routes array has ids of all routes belonging to this gym
def get_gym_json(gymid, routesid, name, added_by, logo_img_id, homepage, address, organization, routesA):
    gymjson = {'id': gymid, 'routesid': routesid, 'name': name,
               'logo_img_id': logo_img_id, 'homepage': homepage, 'address': address, 'organization': organization,
               'added_by': added_by, 'routes': routesA}
    return gymjson

def update_gym_coordinates(gymJson, lat, lon):
    # ensure that lat and lon are valid numbers
    if lat is None or lon is None:
        return gymJson
    
    # test lat and lon to be valid numbers 
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        logging.info('lat or lon are not valid numbers lat='+str(lat)+' lon='+str(lon))
        return gymJson

    gymJson['lat'] = lat
    gymJson['lon'] = lon
    return gymJson


def update_gym_status(gymJson, status):
    if status is None:
        return gymJson
    gymJson['status'] = status
    return gymJson


def _get_route_dict(routeid, routenum, line, color1, color_modifier, grade, name, openedby, opendate, notes):
    oneline = {}
    oneline = {'id': routeid, 'routenum':routenum, 'line': line, 'colorfr': color1, 'color1': color1,
                'color_modifier': color_modifier, 'grade': grade, 'name': name, 'openedby': openedby,
                'opendate': opendate, 'notes': notes}
    return oneline


# replaces or adds routes depending if routesid is found
def upsert_routes(routesid, gym_id, routes):
    try:
        if routesid is None or routes is None:
            return None
        sql_lock.acquire()
        existing_routes = get_routes(routesid)
        
        logging.info("routes are a "+ str(type(routes)))

        if existing_routes is None:
            skala_db._add_routes(routesid, gym_id, routes)
            logging.info('routes added ' + str(routesid))
        else:
            skala_db._update_routes(routesid, routes)
            logging.info('routes updated ' + str(routesid))
    finally:
        sql_lock.release()
        logging.info("done with routes :"+str(routesid))


def send_email_to_participants(competition, sent_by, email_content):
    recipientCount=0
    if email_content is not None and len(email_content) > 10:
        #print("email_content: " + email_content)
        for climber_id in competition['climbers']:
            email_to = competition['climbers'][climber_id]['email']
            #print("sending email to: " + email_to)
            competition_url = url_for('app_ui.getCompetition', competitionId=competition['id'], _external=True)
            email_sender.send_email_to_participant(competition['name'],competition_url, email_to, email_content)
            recipientCount += 1
        users= skala_db.get_users_by_gym_id(competition['gym_id'])
        for user in users:
            if user.get('permissions') is None or user.get('permissions').get('competitions') is None:
                continue 
            if competition['id'] in user['permissions']['competitions']:
                email_to = user['email']
                competition_url = url_for('app_ui.getCompetition', competitionId=competition['id'], _external=True)
                email_sender.send_email_to_participant(competition['name'],competition_url, email_to, email_content)
                recipientCount += 1
        emails = competition.get('emails')
        if emails is None:
            emails = []
        email_content = base64.b64encode(email_content.encode('utf-8')).decode('utf-8')
        time_sent = (datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        email = {'content': email_content, 'recipientCount': recipientCount, 'date': time_sent, 'sent_by': sent_by}
        emails.append(email)
        competition['emails'] = emails
        update_competition(competition['id'], competition)
    return recipientCount


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


def load_csv_routes():
    with open('topo-nanterre.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        routes = {'routes':[]}
        for row in reader:
             routes.get('routes').append(row)
    return routes


def loadgymsdict():
    return {'gyms': [
        {'id': '', 'routesid': '1', 'name': 'Nanterre Sprortiv' },
        {'id': '', 'routesid': '2', 'name': 'ESS 78'}]
    }


def generate_dummy_routes(size):
    routes_id = str(uuid.uuid4().hex)
    routes = {"id":routes_id }
    routesA = []
    for i in range(1, size+1):
        route_id = str(uuid.uuid4().hex)
        route = _get_route_dict(route_id, str(i), '1', '#2E8857', 'solid', '?', 'route'+str(i), '', '', '')
        routesA.append(route)

    routes['routes'] = routesA
    routes['name'] = "Default"
    return routes


def get_img(img_id):
    return skala_db.get_image(img_id)


def loadroutesdict():
    return {'routes': [
        {'id': '111', 'routenum': '1', 'line': '1', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '4b', 'name': 'Dummy route', 'openedby': '', 'opendate': '', 'notes': 'dummy routes'},
        {'id': '222', 'routenum': '2', 'line': '1', 'colorfr': 'Rouge', 'color1': '#FF0000', 'color2': '', 'grade': '5a+', 'name': "L'égyptienne", 'openedby': 'Sebastiao', 'opendate': 'dec.-21', 'notes': 'Départ bas / horizontal'},
        {'id': '333', 'routenum': '3', 'line': '1', 'colorfr': 'Gris', 'color1': '#708090', 'color2': '', 'grade': '5b+', 'name': 'Fifty shades of grès', 'openedby': 'Olivier', 'opendate': 'oct.-19', 'notes': 'sans arête'},
        {'id': '444', 'routenum': '4', 'line': '1', 'colorfr': 'Marron', 'color1': '#A0522D', 'color2': '', 'grade': '5c', 'name': 'James Brown', 'openedby': 'Florian, Guillaume, Paulo', 'opendate': 'oct.-19', 'notes': ''},
        {'id': '', 'routenum': '5', 'line': '1', 'colorfr': 'Rose marbré', 'color1': '#FF69B4', 'color2': '', 'grade': '6b', 'name': 'Jeny dans le 6', 'openedby': 'Guillaume', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '6', 'line': '1', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '6a+', 'name': '', 'openedby': '', 'opendate': 'déc.-17', 'notes': ''},
        {'id': '', 'routenum': '7', 'line': '2', 'colorfr': 'Orange', 'color1': '#FFA500', 'color2': '', 'grade': '5a', 'name': "Jeanne d'Arc", 'openedby': 'Jeanne', 'opendate': 'avr.-19', 'notes': 'voie enfants'},
        {'id': '', 'routenum': '8', 'line': '2', 'colorfr': 'Rose', 'color1': '#FF69B4', 'color2': '', 'grade': '5a+', 'name': 'Spacy', 'openedby': 'Sebastiao', 'opendate': 'avr.-19', 'notes': ''},
        {'id': '', 'routenum': '9', 'line': '2', 'colorfr': 'Mauve', 'color1': '#800080', 'color2': '', 'grade': '5b', 'name': "L'araignée mauve", 'openedby': 'Pol', 'opendate': 'nov.-19', 'notes': ''},
        {'id': '', 'routenum': '10', 'line': '2', 'colorfr': 'Blanc', 'color1': '#FFFFFF', 'color2': '', 'grade': '6b', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '11', 'line': '2', 'colorfr': 'Bleu', 'color1': '#0000FF', 'color2': '', 'grade': '5c', 'name': 'Hématome', 'openedby': 'Aurélien, Guillaume', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '12', 'line': '2', 'colorfr': 'Gris', 'color1': '#708090', 'color2': '', 'grade': '5c', 'name': '', 'openedby': 'Nicolas', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '13', 'line': '3', 'colorfr': 'Rose marbré', 'color1': '#FF69B4', 'color2': '', 'grade': '4b', 'name': '', 'openedby': '', 'opendate': 'avr.-17', 'notes': ''},
        {'id': '', 'routenum': '14', 'line': '3', 'colorfr': 'Orange', 'color1': '#FFA500', 'color2': '', 'grade': '5a+', 'name': '', 'openedby': 'Sandrine, Sébastien', 'opendate': 'oct.-18', 'notes': ''},
        {'id': '', 'routenum': '15', 'line': '3', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '5c', 'name': 'Jaune Lennon', 'openedby': 'Olivier', 'opendate': 'oct.-19', 'notes': ''},
        {'id': '', 'routenum': '16', 'line': '3', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '6a', 'name': '', 'openedby': 'Hélène', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '17', 'line': '4', 'colorfr': 'Noir', 'color1': '#000000', 'color2': '', 'grade': '4a', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '18', 'line': '4', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '5b', 'name': 'Mousse bleue', 'openedby': 'Sebastiao', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '19', 'line': '4', 'colorfr': 'Blanc', 'color1': '', 'color2': '', 'grade': '6a', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '20', 'line': '4', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '5c', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '21', 'line': '4', 'colorfr': 'Orange', 'color1': '#FFA500', 'color2': '', 'grade': '6a', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '22', 'line': '5', 'colorfr': 'Orange', 'color1': '#FFA500', 'color2': '', 'grade': '6 ?', 'name': '', 'openedby': 'Jérôme', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '23', 'line': '5', 'colorfr': 'Noir marbré', 'color1': '', 'color2': '', 'grade': '4c', 'name': 'Marble bubble', 'openedby': 'Sebastiao', 'opendate': 'oct.-19', 'notes': ''},
        {'id': '', 'routenum': '24', 'line': '5', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '5a', 'name': 'Et toc', 'openedby': 'Jérôme', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '25', 'line': '5', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '5c', 'name': 'La bleusaille', 'openedby': 'Sebastiao', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '26', 'line': '5', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '5c', 'name': "C'est vert", 'openedby': 'Olivier', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '27', 'line': '5', 'colorfr': 'Gris', 'color1': '#708090', 'color2': '', 'grade': '5c+', 'name': 'La base', 'openedby': 'Jérôme', 'opendate': 'avr.-17', 'notes': ''},
        {'id': '', 'routenum': '28', 'line': '5', 'colorfr': 'Rose', 'color1': '#FF69B4', 'color2': '', 'grade': '5c', 'name': 'Pollux', 'openedby': 'Ivan', 'opendate': 'nov.-19', 'notes': 'sans arête'},
        {'id': '', 'routenum': '29', 'line': '5', 'colorfr': 'Orange', 'color1': '', 'color2': '', 'grade': '6a', 'name': 'Peace mémé', 'openedby': 'Jérôme', 'opendate': '', 'notes': 'sans arête'},
        {'id': '', 'routenum': '30', 'line': '5', 'colorfr': 'Vert marbré', 'color1': '#2E8B57', 'color2': '', 'grade': '6a+/6b ?', 'name': '', 'openedby': 'Estelle', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '31', 'line': '6', 'colorfr': 'Rose marbré', 'color1': '#FF69B4', 'color2': '', 'grade': '6b', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '32', 'line': '7', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '4c', 'name': 'Début de séance', 'openedby': 'Rémy', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '33', 'line': '7', 'colorfr': 'Bleu marbré', 'color1': '', 'color2': '', 'grade': '5b', 'name': '', 'openedby': '', 'opendate': 'juil.-18', 'notes': ''},
        {'id': '', 'routenum': '34', 'line': '7', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '5c+', 'name': 'La coulée verte', 'openedby': 'Sebastien, Yohan', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '35', 'line': '8', 'colorfr': 'Rouge marbré', 'color1': '', 'color2': '', 'grade': '6a', 'name': 'Timal', 'openedby': 'Jérôme', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '36', 'line': '8', 'colorfr': 'Orange', 'color1': '', 'color2': '', 'grade': '6c+', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '37', 'line': '8', 'colorfr': 'Rose marbré', 'color1': '', 'color2': '', 'grade': '7b', 'name': '', 'openedby': '', 'opendate': '', 'notes': 'suite de la voie en 6'},
        {'id': '', 'routenum': '38', 'line': '9', 'colorfr': 'Noir', 'color1': '', 'color2': '', 'grade': '5a+', 'name': '', 'openedby': '', 'opendate': 'oct.-18', 'notes': ''},
        {'id': '', 'routenum': '39', 'line': '9', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '5c', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '40', 'line': '9', 'colorfr': 'Gris', 'color1': '#708090', 'color2': '', 'grade': '6a+', 'name': 'Cour-âge', 'openedby': 'Jérôme', 'opendate': 'avr.-19', 'notes': 'dièdre'},
        {'id': '', 'routenum': '41', 'line': '9', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '6b', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '42', 'line': '9', 'colorfr': 'Blanc', 'color1': '', 'color2': '', 'grade': '6c/7a ?', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '43', 'line': '10', 'colorfr': 'Violet', 'color1': '', 'color2': '', 'grade': '5a', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '44', 'line': '10', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '5b+', 'name': '', 'openedby': 'Jennifer', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '45', 'line': '10', 'colorfr': 'Vert', 'color1': '', 'color2': '', 'grade': '6a ?', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '46', 'line': '11', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '6c', 'name': "Au nom de l'amour", 'openedby': 'Jérôme', 'opendate': 'oct.-19', 'notes': ''},
        {'id': '', 'routenum': '47', 'line': '11', 'colorfr': 'Noir marbré', 'color1': '', 'color2': '', 'grade': '7b', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '48', 'line': '12', 'colorfr': 'Rose marbré', 'color1': '', 'color2': '', 'grade': '5c', 'name': '', 'openedby': 'Jérôme', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '49', 'line': '12', 'colorfr': 'Orange', 'color1': '#FFA500', 'color2': '', 'grade': '6a', 'name': 'Pozer', 'openedby': 'Jérôme', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '50', 'line': '12', 'colorfr': 'Mauve', 'color1': '', 'color2': '', 'grade': '6c', 'name': 'Carma-sutra', 'openedby': 'Jérôme', 'opendate': 'fév-19', 'notes': ''},
        {'id': '', 'routenum': '51', 'line': '12', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '6c+', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '52', 'line': '12', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '7b', 'name': 'Serrerbrale', 'openedby': 'Jérôme', 'opendate': 'nov.-19', 'notes': ''},
        {'id': '', 'routenum': '53', 'line': '12', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '7b', 'name': '', 'openedby': '', 'opendate': 'déc.-17', 'notes': ''},
        {'id': '', 'routenum': '54', 'line': '12', 'colorfr': 'Blanc', 'color1': '', 'color2': '', 'grade': '8a ?', 'name': '', 'openedby': 'Jérôme', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '55', 'line': '13', 'colorfr': 'Noir', 'color1': '', 'color2': '', 'grade': '5b', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '56', 'line': '13', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '6c', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '57', 'line': '13', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '6c', 'name': '', 'openedby': 'Jérôme', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '58', 'line': '13', 'colorfr': 'Rose', 'color1': '', 'color2': '', 'grade': '6c', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '59', 'line': '14', 'colorfr': 'Orange', 'color1': '#FFA500', 'color2': '', 'grade': '5a', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '60', 'line': '14', 'colorfr': 'Marron', 'color1': '', 'color2': '', 'grade': '6a', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '61', 'line': '14', 'colorfr': 'Vert marbré', 'color1': '#2E8B57', 'color2': '', 'grade': '6b+', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '62', 'line': '15', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '6a', 'name': 'Doigt döner', 'openedby': 'Olivier, Rémy', 'opendate': 'avr.-19', 'notes': ''},
        {'id': '', 'routenum': '63', 'line': '15', 'colorfr': 'Rose marbré', 'color1': '', 'color2': '', 'grade': '6a', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '64', 'line': '15', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '6a+', 'name': 'Rire jaune', 'openedby': 'Aurélien, Guillaume', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '65', 'line': '15', 'colorfr': 'Noir marbré', 'color1': '', 'color2': '', 'grade': '7a ?', 'name': '', 'openedby': 'Jérôme', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '66', 'line': '15', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '6c', 'name': '', 'openedby': 'Franck', 'opendate': 'déc.-17', 'notes': ''},
        {'id': '', 'routenum': '67', 'line': '15', 'colorfr': 'Blanc', 'color1': '', 'color2': '', 'grade': '7a+', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '68', 'line': '16', 'colorfr': 'Orange', 'color1': '', 'color2': '', 'grade': '5b', 'name': '', 'openedby': 'Franck', 'opendate': 'oct.-18', 'notes': ''},
        {'id': '', 'routenum': '69', 'line': '16', 'colorfr': 'Rose', 'color1': '', 'color2': '', 'grade': '5c+', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': ''},
        {'id': '', 'routenum': '70', 'line': '16', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '6a', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': 'départ commun 5c en 17'},
        {'id': '', 'routenum': '71', 'line': '16', 'colorfr': 'Bleu marbré', 'color1': '', 'color2': '', 'grade': '6b', 'name': '', 'openedby': 'Franck', 'opendate': 'oct.-18', 'notes': ''},
        {'id': '', 'routenum': '72', 'line': '16', 'colorfr': 'Gris', 'color1': '', 'color2': '', 'grade': '6b', 'name': 'Pince-mi pince-la', 'openedby': 'Jérôme', 'opendate': 'dec.-21', 'notes': 'colonnettes'},
        {'id': '', 'routenum': '73', 'line': '17', 'colorfr': 'Rouge', 'color1': '', 'color2': '', 'grade': '5c', 'name': '', 'openedby': 'Franck', 'opendate': 'fev-22', 'notes': 'départ commun 6a en 16'},
        {'id': '', 'routenum': '74', 'line': '17', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '5a', 'name': 'Joker', 'openedby': 'Eftalya, Sebastiao', 'opendate': 'nov.-19', 'notes': ''},
        {'id': '', 'routenum': '75', 'line': '17', 'colorfr': 'Saumon', 'color1': '#FFE4C4', 'color2': '', 'grade': '5a', 'name': 'Dièdre or alive', 'openedby': 'Jennifer', 'opendate': 'oct.-19', 'notes': ''},
        {'id': '', 'routenum': '76', 'line': '18', 'colorfr': 'Jaune', 'color1': '#FFFF00', 'color2': '', 'grade': '5c', 'name': 'Jauniligne', 'openedby': 'Sebastiao', 'opendate': 'oct.-19', 'notes': ''},
        {'id': '', 'routenum': '77', 'line': '18', 'colorfr': 'Blanc', 'color1': '', 'color2': '', 'grade': '6a+ ?', 'name': '', 'openedby': 'Davidski', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '78', 'line': '18', 'colorfr': 'Orange', 'color1': '', 'color2': '', 'grade': '5c', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '79', 'line': '18', 'colorfr': 'Bleu marbré', 'color1': '', 'color2': '', 'grade': '6c', 'name': '', 'openedby': 'Franck', 'opendate': 'oct.-18', 'notes': 'sans colonnettes'},
        {'id': '', 'routenum': '80', 'line': '19', 'colorfr': 'Saumon', 'color1': '', 'color2': '', 'grade': '5a+', 'name': '', 'openedby': '', 'opendate': 'juin-18', 'notes': ''},
        {'id': '', 'routenum': '81', 'line': '19', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '5b+', 'name': 'La coincée', 'openedby': 'Jérôme', 'opendate': 'déc.-19', 'notes': ''},
        {'id': '', 'routenum': '82', 'line': '19', 'colorfr': 'Noir', 'color1': '', 'color2': '', 'grade': '5b+', 'name': 'Icosium', 'openedby': 'Djallel', 'opendate': 'oct.-18', 'notes': ''},
        {'id': '', 'routenum': '83', 'line': '19', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '6a+', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '84', 'line': '20', 'colorfr': 'Vert', 'color1': '#2E8B57', 'color2': '', 'grade': '4c', 'name': '', 'openedby': '', 'opendate': 'juin-18', 'notes': ''},
        {'id': '', 'routenum': '85', 'line': '20', 'colorfr': 'Gris', 'color1': '', 'color2': '', 'grade': '5c ?', 'name': '', 'openedby': 'Nicolas', 'opendate': 'dec.-21', 'notes': ''},
        {'id': '', 'routenum': '86', 'line': '20', 'colorfr': 'Bleu', 'color1': '', 'color2': '', 'grade': '5b+', 'name': 'Clean up', 'openedby': 'Jérôme', 'opendate': 'déc.-19', 'notes': ''},
        {'id': '', 'routenum': '87', 'line': '20', 'colorfr': 'Jaune', 'color1': '', 'color2': '', 'grade': '5b+', 'name': '', 'openedby': '', 'opendate': '', 'notes': ''},
        {'id': '', 'routenum': '88', 'line': '20', 'colorfr': 'Marron', 'color1': '', 'color2': '', 'grade': '5c', 'name': '', 'openedby': 'Alex', 'opendate': 'fev-22', 'notes': 'sans vire, prises uniquement'},
        {'id': '', 'routenum': '89', 'line': '20', 'colorfr': 'Orange', 'color1': '', 'color2': '', 'grade': '6b', 'name': '', 'openedby': 'Franck', 'opendate': '', 'notes': ''}]}

if __name__ == '__main__':

    init()


    #library = loadLibraryFromFiles()

    #getOrphanedTracks(library)


