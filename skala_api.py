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
import io
import glob
import random
import uuid
from datetime import datetime, date, time, timedelta
import competitionsEngine
import csv
from functools import wraps
from dataclasses import dataclass

from flask import Flask, redirect, url_for, session, request, render_template, send_file, send_from_directory, jsonify, Response, \
    stream_with_context, copy_current_request_context, g

import logging

from flask import Blueprint
import activities_db as activities_db

import skala_db

from io import BytesIO

from flask import send_file
from collections import defaultdict
#import Activity

#from flask_openapi3 import APIBlueprint, OpenAPI, Tag

#book_tag = Tag(name="book", description="Some Book")

#comp_tag = Tag(name="competition", description="""
#        Some competition
#        with multiple lines 
#        #header also
#        """)

# Third party libraries
from flask import Flask, redirect, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

from pydantic import BaseModel
#skala_api_app = Blueprint('skala_api_app', __name__)

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

languages = {}

grades = ['?', '1', '2', '3', '4a', '4b', '4c', '5a','5a+', '5b', '5b+', '5c','5c+', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a', '9a+', '9b', '9b+', '9c']
    

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

# ID, date, name, location
COMPETITIONS_TABLE = "competitions"
# ID, name, club, m/f, list of climbs
CLIMBERS_TABLE = "climbers"

FSGT_APP_ID = os.getenv('FSGT_APP_ID')
FSGT_APP_SECRET = os.getenv('FSGT_APP_SECRET')

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

#skala_api_app = APIBlueprint('skala_api', __name__, url_prefix='/api1', doc_ui=True, abp_tags= [book_tag, comp_tag])
skala_api_app = Blueprint('skala_api', __name__, url_prefix='/api1')


skala_api_app.debug = True
skala_api_app.secret_key = 'development'
oauth = OAuth(skala_api_app)

genres = {"test": "1"}
authenticated = False

# Third party libraries
from flask import Flask, redirect, request, url_for

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
# Flask app setup

skala_api_app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

UPLOAD_FOLDER = os.path.join(DATA_DIRECTORY,'uploads')
ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'jpeg', 'gif'])

# skala_api_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


#from flask_openapi3 import Info, Tag
#from flask_openapi3 import OpenAPI


#info = Info(title="book API", version="1.0.0")
#book_tag = Tag(name="book", description="Some Book")



class Activity1(BaseModel):
    activity_name: str
    gym_id: str
    date: datetime
    

# User session management setup
# https://flask-login.readthedocs.io/en/latest

@skala_api_app.before_request
def x(*args, **kwargs):
    #logging.debug('api before request '+str(session.get('language'))+ ' accepted languages='+str(request.accept_languages))
    if not session.get('language'):
        #kk = competitionsEngine.supported_languages.keys()
        language = request.accept_languages.best_match(competitionsEngine.supported_languages.keys())
        if language is None:
            language = 'fr_FR'
        session['language'] = language
    #logging.debug ("api setting language to session language="+str(session['language']))
    set_language(session['language'])   
    


@skala_api_app.route('/api/language/<language>')
def set_language(language=None):
    if language is None:
        language = 'fr_FR'
    session['language'] = language
    logging.debug('api setting language requested to '+str(language))
    langpack = competitionsEngine.reference_data['languages'].get(language)
    if langpack is None:
        if language.startswith('pl'):
            langpack = competitionsEngine.reference_data['languages']['pl_PL']
        elif language.startswith('en'):
            langpack = competitionsEngine.reference_data['languages']['en_US']
        elif language.startswith('fr'):
            langpack = competitionsEngine.reference_data['languages']['fr_FR']
        else:
            langpack = competitionsEngine.reference_data['languages']['fr_FR']
            logging.warn('api setting language not found '+str(language))

    competitionsEngine.reference_data['current_language'] = langpack
    return language


@skala_api_app.route('/language')
def get_language():
    if not session.get('language'):
        return json.dumps({'language': 'fr_FR'})
    else:
        return json.dumps({'language': session['language']})


@skala_api_app.route('/langpack')
def get_langpack():
    if not session.get('language'):
        return json.dumps(competitionsEngine.reference_data['languages']['fr_FR'])
    else:
        return json.dumps(competitionsEngine.reference_data['languages'][session.get('language')])



def is_logged_in():
    if session is not None and session.get('expires_at') is not None:
        return True
    else:
        session["wants_url"] = request.url
        return False


def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if is_logged_in():
            return fn(*args, **kwargs)
        else:
            return redirect(url_for("skala_api_app.fsgtlogin"))
    return decorated_function



def admin_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None:
            user = competitionsEngine.get_user_by_email(session['email'])
            if user is not None:
                permissions = user.get('permissions')
                if 'create_gym' in permissions['general'] or permissions['godmode'] == True:
                    return fn(*args, **kwargs)
 
                if session.get('name') == 'David Mossakowski' or session.get('name') == 'Sebastiao Correia':
                    return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("app_ui.fsgtlogin"))
    return decorated_function


#@skala_api_app.get('/apitest', tags=[book_tag, comp_tag])
def testapi():
    return {"code": 0, "message": "ok"}



@skala_api_app.post('/competitionRawAdmin')
@login_required
def fsgtadmin():
    edittype = request.form.get('edittype')
    id = request.form.get('id')
    action = request.form.get('action')
    jsondata = request.form.get('jsondata')
    comp = {}
    jsonobject = None

    if jsondata is not None and len(jsondata) > 2:
        jsonobject = json.loads(jsondata)

    if edittype == 'user':
        if jsonobject is not None and action == 'update':
            competitionsEngine.upsert_user(jsonobject)

        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_user_by_email(id)

        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_user_emails()

    elif edittype == 'competition':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine._update_competition(jsonobject['id'],jsonobject)
        if id is not None  and action == 'delete':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.delete_competition(id)
        if id is not None and action == 'find':
            jsonobject = competitionsEngine.getCompetition(id)
        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_competition_ids()

    elif edittype == 'gym':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.update_gym(jsonobject['id'], jsonobject)

        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_gym(id)
        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_gyms()

    elif edittype == 'routes':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            # None is gymid but this is ok as the routes id will be found
            competitionsEngine.upsert_routes(id, None, jsonobject)


        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_routes(id)

        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_routes_ids()

    else:
        jsonobject = {"error": "choose edit type" }

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)



@skala_api_app.get('/activities')
@login_required
def get_activities():
    user = competitionsEngine.get_user_by_email(session['email'])
    activitiesA = activities_db.get_activities(user.get('id'))

    allActivities = activities_db.get_activities_all_anonymous()

    activities = {}
    activities['activities'] = activitiesA

    avg_stats = []
    user_stats = []
    user_activities_stats = calculate_activities_stats(activitiesA)
    all_activities_stats = calculate_activities_stats(allActivities)

    combined_dates = sorted(set(user_activities_stats['dates'] + all_activities_stats['dates']), reverse=False)

    # Limit the combined_dates list to only the last 26 items
    combined_dates = combined_dates[-25:]

    # Create a dictionary for all_activities_stats for quick lookups
    all_activities_dict = {date: count for date, count in zip(all_activities_stats['dates'], all_activities_stats['routes_done'])}

    # Loop through user_activities_stats and check if the date exists in all_activities_stats
    for date in combined_dates:
        if date in all_activities_dict:
            avg_stats.append(all_activities_dict[date])
        else:
            avg_stats.append(0)
        if date in user_activities_stats['dates']:
            user_stats.append(user_activities_stats['routes_done'][user_activities_stats['dates'].index(date)])
        else:
            user_stats.append(0)

    activities['stats'] = {}
    activities['stats']['dates'] = combined_dates
    activities['stats']['routes_done'] = user_stats
    activities['stats']['routes_avg'] = avg_stats
    return json.dumps(activities)


#calculates number of routes done per day
def calculate_activities_stats_per_day(activities):
    # Get today's date
    today = datetime.today().date()
    stats  = {}
    # Create a dictionary with dates 30 days back from today as keys and 0 as initial values
    routes_done = {(today - timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(160, -1, -1)}

    for activity in activities:
        if activity.get('date') is None:
            continue
        # Parse the 'date' into a date object
        activity_date = activity['date']
        # If the activity date is in the routes_done dictionary, add the number of routes
        if activity_date in routes_done:    
            routes_done[activity_date] += len(activity['routes'])

    # Convert the dictionary to a list of values
    routes_done_list = list(routes_done.values())

    stats['dates'] = list(routes_done.keys())
    stats['routes_done'] = routes_done_list

    return stats

# calculates number of activities per day
def calculate_activities_stats(activities):
    # Initialize a dictionary to store the count of routes done per week
    weekly_stats = defaultdict(int)

    for activity in activities:
        # Parse the date of the activity
        activity_date = datetime.strptime(activity['date'], '%Y-%m-%d')
        
        # Find the Monday of the week for the activity date
        start_of_week = activity_date - timedelta(days=activity_date.weekday())
        
        # Increment the count of routes done for that week
        weekly_stats[start_of_week] += len(activity['routes'])

    # Convert the weekly_stats dictionary to a sorted list of tuples
    sorted_weekly_stats = sorted(weekly_stats.items())

    # Initialize the result dictionary with dates and routes_done lists
    result = {'dates': [], 'routes_done': []}

    # Populate the result dictionary
    for week_start, count in sorted_weekly_stats:
        result['dates'].append(week_start.strftime('%Y-%m-%d'))
        result['routes_done'].append(count)

    return result


@skala_api_app.get('/activities/all')
def get_activities_all():
    activities = activities_db.get_activities_all_anonymous()
    #return json.dumps(activities)
    return activities


@skala_api_app.post('/activity')
@login_required
def journey_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    data = request.get_json()
    #data = request.get_data()
    # get the data from the body of the request

    date = data.get('date')
    gym_id = data.get('gym_id')
    name = data.get('activity_name')
    comp = {}
    gym = competitionsEngine.get_gym(gym_id)
    routesid = gym.get('routesid')


    #a = Activity1(**data)

    activity_id = activities_db.add_activity(user, gym, routesid, name, date)
    activity = activities_db.get_activity(activity_id)
    # journey_id = user.get('journey_id')
    
    #journeys = activities_db.get_activities(user.get('id'))
    return json.dumps(activity)


@skala_api_app.delete('/activity/<activity_id>')
@login_required
def delete_activity(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    activity = activities_db.get_activity(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    activities_db.delete_activity(activity_id)
    # journey_id = user.get('journey_id')

    #journeys = activities_db.get_activities(user.get('id'))
    return {}





@skala_api_app.get('/activity/<activity_id>')
@login_required
def get_activity(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    activity = activities_db.get_activity(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)
    activity = activities_db.get_activity(activity_id)
    #activity = calculate_activity_stats(activity)

    # journey_id = user.get('journey_id')
    #journeys = activities_db.get_activities(user.get('id'))
    return json.dumps(activity)
    


# add a route to an activity
@skala_api_app.post('/activity/<activity_id>')
@login_required
def add_activity_route(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    data = request.get_json()
    #data = request.get_data()
    # get the data from the body of the request

    gym_id = data.get('gym_id')
    routes_id = data.get('routes_id')
    routes = competitionsEngine.get_routes(routes_id)

    route_id = data.get('route_id')
    note = data.get('note')
    route_finish_status = data.get('route_finish_status')
    grade = data.get('grade')
    user_grade = data.get('route-grade-user')
    route = competitionsEngine.get_route(routes_id, route_id)
    
    activity = activities_db.add_activity_entry(activity_id, route, route_finish_status, note, user_grade)

    # journey_id = user.get('journey_id')
    #journeys = activities_db.get_activities(user.get('id'))
    return json.dumps(activity)


@skala_api_app.get('/activity/user/<user_id>')
@login_required
def get_activities_by_user(user_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    activity = activities_db.get_activities_by_gym_routes(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    
    # journey_id = user.get('journey_id')
    # calculate_activity_stats(activity)
    #journeys = activities_db.get_activities(user.get('id'))
    return {}



@skala_api_app.get('/activity/gym/<gym_id>/routes/<routes_id>')
def get_activities_by_gym_by_routes(gym_id, routes_id):
   
    activities = activities_db.get_activities_by_gym_routes(gym_id, routes_id)
    if (activities is None or len(activities) == 0):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    # journey_id = user.get('journey_id')
    # calculate_activity_stats(activity)
    #journeys = activities_db.get_activities(user.get('id'))
    return json.dumps(activities)


@skala_api_app.route('/journey/<journey_id>', methods=['GET'])
@login_required
def journey_session(journey_id):
    journey = activities_db.get_journey_session(journey_id)

    return journey



@skala_api_app.delete('/activity/<activity_id>/route/<route_id>')
@login_required
def delete_activity_route(activity_id, route_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    activity = activities_db.get_activity(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    activity = activities_db.delete_activity_route(activity_id, route_id)
    # journey_id = user.get('journey_id')
    
    #journeys = activities_db.get_activities(user.get('id'))
    return activity


def calculate_activity_stats(activity):
    routes = activity.get('routes')
    routes_count = len(routes)
    grades_climbed = []
    for route in routes:
        route['grade_index'] = grades.index(route['grade'])
        #route['grade_points'] = np.exp(-((route['grade_index'] - mean) / std_dev) ** 2 / 2)
        if route['status'] == 'climbed' or route['status'] == 'flashed':
            grades_climbed.append(route['grade'])
    
    avg_grade_climbed = avg_grade(routes)
    activity['stats'] = {}
    activity['stats']['routes_count'] = routes_count
    activity['stats']['avg_grade_climbed'] = avg_grade_climbed

    return activity

    


def avg_grade(routes, flash_weight=2, climb_weight=1, attempt_weight=0.1):
    if not routes:
        return None

    # Convert grades to indices and apply weights
    weighted_indices = []
    for route in routes:
        grade = route['grade']
        status = route['status']
        if status == 'flashed':
            weight = flash_weight
        elif status == 'climbed':
            weight = climb_weight
        else:  # status is 'attempted' or anything else
            weight = attempt_weight
        weighted_indices.append(grades.index(grade) * weight)

    # Calculate average index
    average_index = sum(weighted_indices) / sum(flash_weight if route['status'] == 'flashed' else climb_weight if route['status'] == 'climbed' else attempt_weight for route in routes)

    # Round to nearest integer
    average_index = round(average_index)

    # Convert index back to grade
    average_grade = grades[average_index]

    return average_grade



@skala_api_app.route('/journey/<journey_id>/add', methods=['POST'])
@login_required
def journey_session_entry_add(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    route_finish_status = request.form.get('route_finish_status')
    route_id = request.form.get('route')
    notes = request.form.get('notes')

    comp = {}

    journey = activities_db.get_journey_session(journey_id)

    journey = activities_db.add_journey_session_entry(journey_id,route_id, route_finish_status, notes)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))


    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@skala_api_app.route('/journey/<journey_id>/<route_id>/remove', methods=['GET'])
@login_required
def journey_session_remove(journey_id, route_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    journey = activities_db.get_journey_session(journey_id)

    testid = request.args.get('testid')
    if journey is None:
        return {}
    activities_db.remove_journey_session(journey_id, route_id)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return {}


@skala_api_app.route('/competition/list')
def getCompetitionDashboard():
    comps = competitionsEngine.getCompetitions()
    compsreturnd = []
    language = session.get('language', 'fr')[:2]
    # for each competition remove object climbers
    for compid in comps:
        c={}
        comps[compid]['climbers'] = None
        comps[compid]['routes'] = None
        c['title'] = comps[compid]['name'] 
        c['id'] = comps[compid]['gym_id']
        #c['start'] = comps[compid]['date']+ "T11:00:00"
        #c['end'] = comps[compid]['date']+ "T15:59:59"
        c['date'] = comps[compid]['date']
        c['extendedProps'] = comps[compid]
        c['url'] = '/competitionDetails/'+compid
        c['text'] = {}
        c['text']['status'] = competitionsEngine.reference_data['current_language'].get('competition_status_'+str(comps[compid]['status']))

        compsreturnd.append(c)
    logging.debug('setting language of competitions to '+str(language)+' session language='+str(session.get('language')))
    return json.dumps(compsreturnd)


@skala_api_app.route('/competition/<competition_id>')
def get_competition_by_id(competition_id):
    competition = competitionsEngine.getCompetition(competition_id)
    
    if competition is None:
        return {}

    for climber in competition.get('climbers').values():
        climber.pop('email', None)


    if competition is None:
        return {"error": "competition not found"}
    return competition


@skala_api_app.route('/competition/year/<year>')
def competitions_by_year(year):

    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    #print(username)

    #username = request.args.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    comp = {}
    competitionId=None
    if not year.isdigit():
        year = datetime.now().year

    user = competitionsEngine.get_user_by_email(session.get('email'))
    subheader_message = request.accept_languages
    langs = competitionsEngine.reference_data['languages']
    competitions = competitionsEngine.getCompetitions()
    #test_list = [datetime(year, 1, 1), datetime(year, 12, 31)]
    date_strt, date_end = datetime(int(year), 1, 1), datetime(int(year), 12, 31)

    input_format = "%Y-%m-%d"
    competitions2 = {}
    for competition_id in competitions:
        competition = competitions.get(competition_id)
        competition_date = competition.get('date')
        try:
            parsered_date = datetime.strptime(competition_date, input_format)
            if parsered_date >= date_strt and parsered_date <= date_end:
                res = True
                competitions2[competition['id']] = competition

        except ValueError:
            print("This is the incorrect date string format.")

    return competitions2


@skala_api_app.route('/competition/create', methods=['POST'])
@login_required
def new_competition_post():
    username = session.get('username')

    routedata = request.get_json()
    routedata = json.loads(routedata)


    #username = request.args.get('username')
    name = request.form.get('name')
    date = request.form.get('date')
    #gym = request.form.get('gym')
    routesid = request.form.get('routes')
    comp = {}
    competitionId = None

    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is None or not competitionsEngine.can_create_competition(user):
        return "{ 'error'; 'Not authorized'}"

    if name is not None and date is not None and routesid is not None:
        competitionId = competitionsEngine.addCompetition(None, name, date, routesid)
        competitionsEngine.modify_user_permissions_to_competition(user, competitionId, "ADD")
        comp = competitionsEngine.getCompetition(competitionId)
        return comp
    return "{ 'error'; 'Not created. Something missing'}"


@skala_api_app.route('/competition/<competitionId>/register')
#@login_required
def addCompetitionClimber(competitionId):
    return None


# Statistics for a competition for apex charts
@skala_api_app.route('/competition/<competitionId>/stats')
#@login_required
def getCompetitionStats(competitionId):
    competition = None

    if competitionId is not None:
        competition = competitionsEngine.recalculate(competitionId)

    if competition is None:
        return render_template('competitionDashboard.html', sortedA=None,
                            subheader_message="No competition found",
                            **session)
    elif competition is LookupError:
        return render_template('index.html', sortedA=None,
                                getPlaylistError="Playlist was not found",
                                library={},
                                **session)
    elif len(competition) == 0:
        return render_template('index.html', sortedA=None,
                                getPlaylistError="Playlist has no tracks or it was not found",
                                library={},
                                **session)

    routesid = competition.get('routesid')
    routesDict = competitionsEngine.get_routes(routesid)
    routes = routesDict['routes']

    #rankings = competitionsEngine.get_sorted_rankings(competition)
    # we need 6 categories:
    categories = ["F0","F1","F2","M0","M1","M2"]
    #category_names =  [reference_data['current_language'].ranking_diament_women,
#				reference_data['current_language'].ranking_titan_women,
#				reference_data['current_language'].ranking_senior_women,
#				reference_data['current_language'].ranking_diament_men,
#				reference_data['current_language'].ranking_titan_men,
#				reference_data['current_language'].ranking_senior_men]
	
    statistics = {}
    for category in categories:
        repeatArray = [0]*len(routes) 
        statistics[str(category)]=repeatArray

    for climber in competition['climbers'].values():

        key = str(climber.get('sex'))+str(climber.get('category'))
        stats = statistics.get(key)
        for routenum in climber.get('routesClimbed'):
            if climber.get('sex') == 'M':
                stats[routenum-1]=stats[routenum-1]+1
            else:
                stats[routenum-1]=stats[routenum-1]+1  # can make -1 to have a stacked chart with males and females

    statout = []
    for category in categories:     
        statout.append( {  #"name":category,
                           "data": statistics.get(category)})

    statresponse = { "chartdata": statout,
                    "routedata" : routes}
    
    return json.dumps(statresponse)


# Statistics for a competition for apex charts
@skala_api_app.route('/competition/<competitionId>/fullresults')
#@login_required
def getCompetitionFlatFullTable(competitionId):
    competition = None

    if competitionId is not None:
        competition = competitionsEngine.recalculate(competitionId)

    if competition is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No competition found",
                               **session)
    elif competition is LookupError:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist was not found",
                                   library={},
                                   **session)
    elif len(competition) == 0:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    routesid = competition.get('routesid')
    routesDict = competitionsEngine.get_routes(routesid)
    routes = routesDict['routes']

    #rankings = competitionsEngine.get_sorted_rankings(competition)
    # we need 6 categories:
    categories = ["F0","F1","F2","M0","M1","M2"]
    #category_names =  [reference_data['current_language'].ranking_diament_women,
#				reference_data['current_language'].ranking_titan_women,
#				reference_data['current_language'].ranking_senior_women,
#				reference_data['current_language'].ranking_diament_men,
#				reference_data['current_language'].ranking_titan_men,
#				reference_data['current_language'].ranking_senior_men]


    statistics = {}
    for category in categories:
        repeatArray = [0]*len(routes) 
        statistics[str(category)]=repeatArray
                
    statout = []
    for category in categories:     
        statout.append( {  #"name":category,
                           "data": statistics.get(category)})

    full_routes_table = []
    table_entry = {}
    for route in competition.get('routes'):
        for climber in competition['climbers'].values():
            if int(route.get('routenum')) in climber.get('routesClimbed'):
                table_entry = {}
                index = climber.get('routesClimbed').index(int(route.get('routenum')))
                if (climber.get('routesClimbed2') and climber.get('routesClimbed2')[index] and route.get('id') != climber.get('routesClimbed2')[index].get('id')):  # there is a potential bug here on routeseClimbed2 not there
                    logging.error("getCompetitionFlatFullTable route id is not matching or climber doesn't have a routeClimbed")
                points = climber.get('points_earned')[index]

                table_entry.update(route)
                table_entry['points'] = round(points,2)
                table_entry['category'] = climber.get('category')
                table_entry['firstname'] = climber.get('firstname')
                table_entry['lastname'] = climber.get('lastname')
                table_entry['club'] = climber.get('club')
                table_entry['rank'] = climber.get('rank')
                table_entry['sex'] = climber.get('sex')

                
                #full_routes_table.append(route)
                full_routes_table.append(table_entry)
    

    statresponse = { "chartdata": statout,
                    "routedata" : routes}
    
    return json.dumps(full_routes_table)
    #return full_routes_table



### USER
@skala_api_app.route('/user')
def get_user():
    if session is None or session.get('email') is None:
        return {}
    
    user = competitionsEngine.get_user_by_email(session['email'])

    if user is None:
        return {}
    

    
    return json.dumps(user)


@skala_api_app.route('/user/email')  
@admin_required
def get_users():
    if session is None or session.get('email') is None:
        return {}
    
    user = competitionsEngine.get_user_by_email(session['email'])
    
    if user is None:
        return {}

    if competitionsEngine.can_edit_users(user):
        users = skala_db.get_all_user_emails()
        return json.dumps(users)
    
    return json.dumps(user)


@skala_api_app.route('/user/email/<email>')
@admin_required
def get_user_by_email(email):
    climber = competitionsEngine.get_user_by_email(email)

    if climber is None:
        #return "{'error_code':'No such user'}", 400
        return {}
    return climber



@skala_api_app.route('/gym/<gym_id>/users')
def get_users_by_gym(gym_id):
    users=  skala_db.get_users_by_gym_id(gym_id)
    # remove email and permissions from the response
    for user in users:
        user.pop('email', None)
        #user.pop('permissions', None)
        user.pop('isgod',None)
        
        if user.get('fpictureurl') is not None:
            user['pictureurl'] = user.get('fpictureurl')
        if user.get('gpictureurl') is not None:
            user['pictureurl'] = user.get('gpictureurl')
        if user.get('fpictureurl') is None and user.get('gpictureurl') is None:
            #user['pictureurl'] = '/public/images/sentiment_satisfied_FILL0_wght600_GRAD200_opsz48.png'
            user['pictureurl'] = '/public/images/favicon.png'
        if user.get('firstname') is None:
            user['firstname'] = user.get('name') 
    return users



@skala_api_app.route('/users/search/')
def get_all_users():
    search_string = request.args.get('q')
    if search_string is None or len(search_string) < 2 or not search_string.isalnum():
        return []

    users=  skala_db.search_all_users(search_string=search_string)
    # remove email and permissions from the response
    for user in users:
        user.pop('email', None)
        #user.pop('permissions', None)
        user.pop('isgod',None)
        
        if user.get('fpictureurl') is not None:
            user['pictureurl'] = user.get('fpictureurl')
        if user.get('gpictureurl') is not None:
            user['pictureurl'] = user.get('gpictureurl')
        if user.get('fpictureurl') is None and user.get('gpictureurl') is None:
            #user['pictureurl'] = '/public/images/sentiment_satisfied_FILL0_wght600_GRAD200_opsz48.png'
            user['pictureurl'] = '/public/images/favicon.png'
        if user.get('firstname') is None:
            user['firstname'] = user.get('name') 
    #json.dumps(users)
    return json.dumps(users)



@skala_api_app.route('/updateuser')
def update_user():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No competition found",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))

    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    subheader_message = request.args.get('update_details')

    email = session.get('email')
    name = session.get('name')

    if firstname is None or sex is None or club is None or email is None:
        #subheader_message = "Update"

        return render_template('climber.html',
                               error_message = request.args.get('all_fields_required'),
                               subheader_message=subheader_message,
                               competitionId=None,
                               climber=climber,
                               reference_data=competitionsEngine.reference_data,
                               logged_email=email,
                               logged_name=name,
                               **session)

    else:
        climber = competitionsEngine.user_self_update(climber, name, firstname, lastname, nick, sex, club, category)
        subheader_message = request.args.get('details_saved')

    if name is None:
        name = ""

    return render_template('climber.html',
                           subheader_message=subheader_message,
                           competitionId=None,
                           climber=climber,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)




## RESULTS

@skala_api_app.route('/competition_results/<competitionId>')
#@login_required
def get_competition_results(competitionId):
    competition = None

    if competitionId is not None:
        competition = competitionsEngine.recalculate(competitionId)

    if competition is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_competition_found'),
                               **session)
    elif competition is LookupError:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist was not found",
                                   library={},
                                   **session)
    elif len(competition) == 0:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)
    rankings = competitionsEngine.get_sorted_rankings(competition)

    return rankings


#@skala_api_app.route('/competitionDashboard/<competitionId>/climber/<climberId>')
#@login_required
# PROBABLY NOT USED EVER!!!
def getCompetitionClimber(competitionId, climberId):
    #competitionId = request.args.get('competitionId')

    routesUpdated = []
    for i in range(100):
        routeChecked = request.args.get("route"+str(i)) != None
        if routeChecked: routesUpdated.append(i)


    #   logging.info(session['id']+' competitionId '+competitionId)
    # r = request
    # username = request.args.get('username')

    competition = None

    if climberId is not None:
        if len(routesUpdated) > 0:
            competitionsEngine.setRoutesClimbed(competitionId, climberId, routesUpdated)
            competition = competitionsEngine.getCompetition(competitionId)
            return render_template('competitionDashboard.html', sortedA=None,
                                   competition=competition,
                                   competitionId=competitionId,
                                   subheader_message=request.args.get('routes_saved'),
                                    reference_data=competitionsEngine.reference_data,
                                   **session)


        climber = competitionsEngine.getClimber(competitionId,climberId)


    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_climber_found'),
                               **session)
    elif climber is LookupError:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="error  ",
                                   library={},
                                   **session)
    elif len(climber) == 0:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    competition = competitionsEngine.getCompetition(competitionId)
    subheader_message = climber['name']+"   from "+climber['club']

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("competitionDashboard.html", climberId=climberId, climber=climber,
                           subheader_message=subheader_message,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)


@skala_api_app.route('/competition_results/<competitionId>/csv')
def get_competition_results_csv(competitionId):
    competition = competitionsEngine.getCompetition(competitionId)
    out = {}
    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(competition['climbers'])

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    data_file = open('jsonoutput.csv', 'w', newline='')
    csv_writer = csv.writer(data_file)

    count = 0
    for climberid in competition['climbers']:
        data = competition['climbers'][climberid]
        for i in range(100):
            if (i in competition['climbers'][climberid]['routesClimbed']):
                data['r' + str(i)] = 1
            else:
                data['r' + str(i)] = 0

        if count == 0:
            header = data.keys()
            csv_writer.writerow(header)
            writer.writerow(header)
            count += 1
        out = {}
        routesClimbed = flatten(data['routesClimbed'])

        csv_writer.writerow(data.values())
        writer.writerow(data.values())

    data_file.close()

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                     "attachment; filename=competitionresults.csv"})




# enter competition climbed routes for a climber and save them
@skala_api_app.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['GET'])
@login_required
def routes_climbed(competitionId, climberId):

    if climberId is not None:
        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_climber_found'),
                               **session)
    elif climber is LookupError:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="error  ",
                                   library={},
                                   **session)
    elif len(climber) == 0:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competitionId)

    if not competitionsEngine.can_update_routes(user,competition):
        return redirect(url_for('skala_api_app.competitionRoutesList', competitionId=competitionId))


    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    #routes = routes['routes']
    subheader_message = climber['name']+" - "+climber['club']

    return render_template("competitionRoutesEntry.html", climberId=climberId,
                           climber=climber,
                           routes=routes,
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)


@skala_api_app.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['POST'])
@login_required
def update_routes_climbed(competitionId, climberId):
    # generate array of marked routes from HTTP request
    routesUpdated = []
    for i in range(100):
        routeChecked = request.form.get("route"+str(i)) != None
        if routeChecked:
            routesUpdated.append(i)

    competition = None

    if climberId is not None:
        user = competitionsEngine.get_user_by_email(session['email'])
        if not competitionsEngine.has_permission_for_competition(competitionId, user):
            return render_template('competitionLogin.html')

        if len(routesUpdated) > 0:
            competitionsEngine.setRoutesClimbed(competitionId, climberId, routesUpdated)
            competition = competitionsEngine.getCompetition(competitionId)
            return render_template('competitionClimberList.html',
                                   competition=competition,
                                   competitionId=competitionId,
                                   subheader_message=request.args.get('routes_saved'),
                                    reference_data=competitionsEngine.reference_data,
                                   **session)

        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_climber_found'),
                               **session)
    elif climber is LookupError:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="error  ",
                                   library={},
                                   **session)
    elif len(climber) == 0:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    competition = competitionsEngine.getCompetition(competitionId)

    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    routes = routes['routes']
    subheader_message = climber['name']+" - "+climber['club']

    return render_template("competitionRoutesEntry.html", climberId=climberId, climber=climber,
                           routes=routes,
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)



@skala_api_app.route('/migrategyms')
def migrategyms():
    gyms = competitionsEngine.get_gyms()

    nanterre = gyms["1"]
    nanterre['logoimg'] = 'logo-ESN-HD-copy-1030x1030.png'
    nanterre['homepage'] = 'https://www.esnanterre.com/'

    competitionsEngine.update_gym("1", "667", json.dumps(nanterre))
    return {}




@skala_api_app.route('/competition_results/<competitionId>/stats')
def get_competition_stats(competitionId):
    comp = competitionsEngine.get_competition(competitionId)
    routes = competitionsEngine.get_routes(comp['routesid'])

    if comp is None:
        return {}
    
    results = {}

    pointsPerRouteM = competitionsEngine.get_route_repeats("M", comp)
    pointsPerRouteF = competitionsEngine.get_route_repeats("F", comp)

    for index, route in enumerate(routes['routes']):
        route['pointsM'] = pointsPerRouteM[index+1]
        route['pointsF'] = pointsPerRouteF[index+1]

    #grades = ["4a", "4b", "4","4c", "5a", "5b", "5c", "6a", "6a+", "6b", "6b+", "6c", "7a"] # list of french climbing grades
    #grades = ["5b", "5c", "6a"] # list of french climbing grades
    
    routes['rangeData'] = transform_json(routes)
    routes['rangeDataOld']  =transform_jsonold(routes)

    #routes['grades']
    return routes



    male_data = []
    female_data = []
    
    male_points = []
    female_points = []

    male_grades = {}
    female_grades = {}
    for route in routes["routes"]:
        grade = route['grade']
        male_points.append(int(route["pointsM"]))
        female_points.append(int(route["pointsF"]))
        
        male_grades[grade] = male_points
        female_grades[grade] = female_points
    
        male_y = [male_points-3, male_points] if male_points else [None, None]
        female_y = [female_points-3, female_points] if female_points else [None, None]
    
        male_data.append({"x": grade, "y": male_y})
        female_data.append({"x": grade, "y": female_y})

    male_data = sorted(male_data, key=lambda k: k['x'])
    female_data = sorted(female_data, key=lambda k: k['x'])

    series_json = [
        {"name": "Male", "data": male_data},
        {"name": "Female", "data": female_data}
    ]

    routes['rangeData'] = series_json

    return routes



@skala_api_app.route('/climber/stats')
@login_required
def get_myskala():
    username = session.get('username')
    stats = {}
    competitions = skala_db.get_all_competitions()
    competition_routes_total = 0
    
    for competition in competitions.values():
        #competition = skala_db.get_competition(id)
        routesid = competition.get('routesid')
        routes = competitionsEngine.get_routes(routesid)
        if routes is None:
            continue
        routes = routes.get('routes')
    
        competition_routes_total += len(routes)
        
    competition_ids = skala_db.get_competitions_for_email(username)

    user = competitionsEngine.get_user_by_email(session['email'])
    
    all_competitions = []
    stats['personalstats']={}
    stats['personalstats']['all_grades'] = []
    routes_climbed_count = 0
    
    for id in competition_ids:
        ##competition = skala_db.get_competition(id)
        #pointsEarned = competitionsEngine._calculatePointsPerClimber(id, user['id'], competition)
        competition = competitionsEngine.recalculate(id)
        routesid = competition.get('routesid')
        routes = competitionsEngine.get_routes(routesid)
        if routes is None:
            continue
        routes = routes.get('routes')
        #all_competitions.append(competition)

        climber = competition.get('climbers').get(user['id'])
        competition['climber'] = climber
        routes_climbed2 = {}
        if climber is not None:
            
            routes_climbed2=climber['routesClimbed2']
            routes_climbed_count += len(climber['routesClimbed2'] )
            #grades_climbed = []
            for idx, route in enumerate(routes_climbed2):
                route['competitionName'] = competition['name']
                route['competitionDate'] = competition['date']
                route['gym'] = competition['gym']
                grade = route.get('grade')
                points = round(climber['points_earned'][idx])
                stats['personalstats']['all_grades'].append(route.get('grade'))
                route['points'] = points
                route['rank']  = climber['rank']
                #grades_climbed.append(' '+str(grade) + ' ('+str(points)+')')
            #competition['grades_climbed'] = grades_climbed
            competition['points_earned'] = climber['points_earned']
            competition['routesClimbed2'] = routes_climbed2
            competition
        # clear unnecessary data for other
        competition.get('climbers').clear()
        all_competitions.extend(routes_climbed2)

        competition_points_per_route = {}
        
    stats['user'] = user

    stats['personalstats']['competitions_count'] = len(competition_ids)
    stats['personalstats']['total_competitions_count'] = len(competitions)
    
    stats['personalstats']['routes_climbed_count'] = routes_climbed_count
    stats['personalstats']['competition_routes_total'] = competition_routes_total

    stats['competitions'] = all_competitions
    stats['thursday'] = datetime.today().weekday() == 3
    # return well formatted json
    return json.dumps(stats, indent=4)




def transform_json_bubble(input_data):
    # Create a dictionary to hold the data for each grade
    seriesH = {'name': 'Homme', 'data': []}
    seriesF = {'name': 'Femme', 'data': []}

    # Create a dictionary to track grades and their corresponding data
    grade_data_h = {}
    grade_data_f = {}

    
    # Loop over the routes and add them to the appropriate grade
    for route in input_data['routes']:
        grade = route['grade']
        points_m = int(route['pointsM'])
        points_f = int(route['pointsF'])
        routenum = int(route['routenum'])

    # Add points_m to seriesH
        if grade not in grade_data_h:
            grade_data_h[grade] = {'x': grade, 'y': [points_m]}
        else:
            grade_data_h[grade]['y'].append(points_m)

        # Add points_f to seriesF
        if grade not in grade_data_f:
            grade_data_f[grade] = {'x': grade, 'y': [points_f]}
        else:
            grade_data_f[grade]['y'].append(points_f)

        
        #seriesH.get('data').append({'x': routenum, 'y': [points_m, points_m]})
        #seriesF.get('data').append({'x': routenum, 'y': [points_f, points_f]})
        
        seriesH.get('data').append([grade, points_m, points_m])
        seriesF.get('data').append([grade, points_f, points_f])
        
        
    #sorted_grades = sorted(grades.keys(), key=lambda x: (x  if x else 'ZZZ'))

    
    return [seriesH, seriesF]




def transform_json(input_data):
    # Create a dictionary to hold the data for each grade
    grades = {}
    
    # Loop over the routes and add them to the appropriate grade
    for route in input_data['routes']:
        grade = route['grade']
        points_m = int(route['pointsM'])
        points_f = int(route['pointsF'])
        
        # If this is the first route we've seen for this grade, create a new dictionary for it
        if grade not in grades:
            grades[grade] = {'homme': {'min': points_m, 'max': points_m, 'goals': []}, 
                             'femme': {'min': points_f, 'max': points_f, 'goals': []}}
        # Otherwise, update the min and max points for this grade
        else:
            if points_m < grades[grade]['homme']['min']:
                grades[grade]['homme']['min'] = points_m
            if points_m > grades[grade]['homme']['max']:
                grades[grade]['homme']['max'] = points_m
            if points_f < grades[grade]['femme']['min']:
                grades[grade]['femme']['min'] = points_f
            if points_f > grades[grade]['femme']['max']:
                grades[grade]['femme']['max'] = points_f
        
        # Add the route to the appropriate gender's goals list
        if points_m not in grades[grade]['homme']['goals']:
            grades[grade]['homme']['goals'].append(points_m)
        if points_f not in grades[grade]['femme']['goals']:
            grades[grade]['femme']['goals'].append(points_f)
    
    sorted_grades = sorted(grades.keys(), key=lambda x: (x  if x else 'ZZZ'))

    # Create a list of series data for each gender
    series = []
    for gender in ['homme', 'femme']:
        data = []
        for grade in sorted_grades:
            if grade in grades:
                #grade_data = {'x': grade, 'y': [grades[grade][gender]['min'], grades[grade][gender]['max']]}
                grade_data = {'x': grade, 'y': [grades[grade][gender]['min'], 1000]}
                if grades[grade][gender]['goals']:
                    goals = []
                    for goal in grades[grade][gender]['goals']:
                        goal = {'name': str(goal), 'value': goal, 'strokeColor': '#333333', 'strokeWidth': 4}
                        goals.append(goal)
                    grade_data['goals'] = goals
                data.append(grade_data)
        series.append({'name': gender.capitalize(), 'data': data})
    
    return series




def transform_jsonold(input_json):
    # Create two empty lists to store male and female data
    male_data = []
    female_data = []
    
    # Create a dictionary to store route data by grade
    data_by_grade = {}
    
    # Loop through each route in the input JSON
    for route in input_json['routes']:
        grade = route['grade']
        pointsM = int(route['pointsM'])
        pointsF = int(route['pointsF'])
        
        # Add the route to the data for its grade
        if grade not in data_by_grade:
            data_by_grade[grade] = {'goals': []}
        data_by_grade[grade]['goals'].append({
            'name': route['routenum'],
            'value': pointsM,
            'strokeColor': route['color1']
        })
        
        # Update the min and max points for male and female data
        if not any(d['x'] == grade for d in male_data):
            male_data.append({'x': grade, 'y': [pointsM, pointsM]})
        else:
            for d in male_data:
                if d['x'] == grade:
                    d['y'][0] = min(d['y'][0], pointsM)
                    d['y'][1] = max(d['y'][1], pointsM)
                    break
                
        if not any(d['x'] == grade for d in female_data):
            female_data.append({'x': grade, 'y': [pointsF, pointsF]})
        else:
            for d in female_data:
                if d['x'] == grade:
                    d['y'][0] = min(d['y'][0], pointsF)
                    d['y'][1] = max(d['y'][1], pointsF)
                    break
    
    # Sort male and female data by grade
    male_data.sort(key=lambda x: x['x'])
    female_data.sort(key=lambda x: x['x'])
    
    # Combine male and female data into the output series JSON
    series_json = [
        {'name': 'Male', 'data': male_data},
        {'name': 'Female', 'data': female_data}
    ]
    
    # Add the data for each grade to the appropriate object in the series JSON
    for grade, data in data_by_grade.items():
        for d in male_data:
            if d['x'] == grade:
                d.update(data)
                break
    
    return series_json








######## GYMS
@skala_api_app.route('/gym')
def gyms():
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    gyms = competitionsEngine.get_gyms()

    email = session.get('email')
    user = None
    if email is not None:
        user = competitionsEngine.get_user_by_email(email)
    name = session.get('name')

    if name is None:
        name = ""

    return gyms


@skala_api_app.route('/gyms')
def gyms_list(field=None, value=None):
    return gyms_list_by_field('status', 'created')



@skala_api_app.route('/gyms/names')
def gyms_names(field=None, value=None):
    return skala_db.get_all_gym_names()


@skala_api_app.route('/gyms/<field>/<value>')
def gyms_list_by_field(field=None, value=None):

    if field == 'status':
        s = competitionsEngine.reference_data.get('gym_status').get(value)
        gyms = competitionsEngine.get_gyms(status=s)
    #gyms = competitionsEngine.get_gyms()

    newgyms = []

    if gyms is None:
        return json.dumps(newgyms)
    
    for gymid in gyms:
        gym = gyms.get(gymid)
        
        if 'added_by' in gym:
            gym['added_by'] = gym['added_by'].split('@')[0]  # Remove part after @
        newgyms.append(gym)

    return json.dumps(newgyms)


@skala_api_app.route('/gym/<gymid>')
def gym_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    return gym


@skala_api_app.route('/gym/<gymid>/')
def gym_by_id_default_route(gymid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(gym.get('routesid'))

    return routes


@skala_api_app.route('/gym/<gymid>/routes')
def routes_by_gym_id(gymid):
    gym = competitionsEngine.get_gym(gymid)

    routes = competitionsEngine.get_routes(gym.get('routesid'))
    return json.dumps(routes.get('routes'))



@skala_api_app.route('/gym/<gymid>/routes/<routesid>/delete', methods=['POST'])
def delete_gym_routes(gymid, routesid):
    user = competitionsEngine.get_user_by_email(session['email'])
    gym = competitionsEngine.get_gym(gymid)
    routes_set = competitionsEngine.get_routes_by_gym_id(gymid)

    if not competitionsEngine.can_edit_gym(user, gym):
        return json.dumps({'status': 'error', 'message': 'You do not have permission to delete routes'})

    if routesid not in routes_set:
        return json.dumps({'status': 'error', 'message': 'Routes do not belong to gym {gymid}'})
    
    result = competitionsEngine.delete_routes(routesid)
    return json.dumps(result)


def compute_difficulty_rating(status_array):
    if not status_array:
        return 0

    status_values = {
        'attempted': 3,
        'climbed': 2,
        'flashed': 1
    }

    total_score = sum(status_values[status] for status in status_array if status in status_values)
    average_score = total_score / len(status_array)

    # Normalize to a scale of 0 to 4
    difficulty_rating = (average_score - 1) / 2 * 4
    return difficulty_rating


def compute_average_user_grade(user_grades, original_grade):
    if not user_grades:
        return ""

    if original_grade not in grades:
        return ""

    # Convert grades to numerical values based on their index in the grades list
    total_grade = sum(grades.index(grade) for grade in user_grades if grade in grades)
    average_grade_index = total_grade / len(user_grades)
    
    # Convert the average grade index back to a grade
    average_grade = grades[int(round(average_grade_index))]

    # Compare with the original grade
    original_index = grades.index(original_grade)
    average_index = grades.index(average_grade)
    difference = average_index - original_index

    if difference == 0:
        return "&#10003;"
    elif difference == 1:
        return "&#8593;" #up arrow
    elif difference > 1:
        return "&#8593;&#8593;"
    elif difference == -1:
        return "&#8595;"
    elif difference < -1:
        return "&#8595;&#8595;"
    else: 
        return "*"


@skala_api_app.route('/gym/<gymid>/<routesid>')
def gym_by_id_route(gymid, routesid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(routesid)

    activities = activities_db.get_activity_routes_by_gym_id(gymid)
    route_map = {}
    route_counts = {}
    total_routes = len(set(activity['route_id'] for activity in activities))

    # Count the number of times each route appears
    for activity in activities:
        route_id = activity['route_id']
        if route_id not in route_counts:
            route_counts[route_id] = 0
        route_counts[route_id] += 1

    # Create the route map and assign ranks
    for activity in activities:
        route_id = activity['route_id']
        if route_id not in route_map:
            route_map[route_id] = {
                'id': route_id,
              
                'user_grade': [],
                'status': [],
                'note': [],
                'popularity_rank': 0,
                'difficulty_rating': 0
            }

        if 'user_grade' in activity and activity['user_grade']:
            route_map[route_id]['user_grade'].append(activity['user_grade'])
        if 'status' in activity and activity['status']:
            route_map[route_id]['status'].append(activity['status'])
        if 'note' in activity and activity['note']:
            route_map[route_id]['note'].append(activity['note'])

      
    for route in routes['routes']:
        route_id = route['id']
        if route_id in route_map:
            route_data = route_map[route_id]
            route_data['average_user_grade'] = compute_average_user_grade(route_data['user_grade'], route['grade'])
            route.update(route_data)
        else:
            route['average_user_grade'] = ""
            route['user_grade'] = []

    return routes



@skala_api_app.route('/gym/<gymid>/routes/<routesid>/')
def get_gym_routes_enhanced_with_activities_stats(gymid, routesid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(routesid)

    activities = activities_db.get_activity_routes_by_gym_id(gymid)

    #routes2 = activitiy_engine.enhance_routes(routes)
    #routes2 = activitiy_engine.enhance_routes(routes)
    #routs2 = get_activity_routes_by_gym_id(gymid)



    return routes




@skala_api_app.route('/gym/<gymid>/<routesid>/add', methods=['POST'])
@login_required
def route_add(gymid, routesid):

    routedata = request.get_json()
    routedata = json.loads(routedata)

    
    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return redirect(url_for("skala_api_app.fsgtlogin"))

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    allroutes = all_routes.get(routesid)

    routeset = allroutes.get('routes')
    
    for route in routes:
        if route['id'] == routedata['id']:
            routeset.insert(routeset['routenum'], routesdata)

    return json.dumps(allroutes)


# the input is json of a single route
# the response is all the routes as they have been saved
# this should be made thread safe but it isn't right now
@skala_api_app.route('/gym/<gymid>/<routesid>/saveone', methods=['POST'])
@login_required
def route_save(gymid, routesid):

    routedata = request.get_json()
    routedata = json.loads(routedata)

    user = competitionsEngine.get_user_by_email(session.get('email'))

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return Response("{'a':'b'}", status=401, mimetype='application/json')

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    routeset = all_routes.get(routesid)

    logging.info("routesid: "+routedata['id'])
    routes = routeset.get('routes')
    if routedata['id'] is None or routedata['id'] == '':
        routedata['id'] = str(uuid.uuid4().hex)
    
    #idx = 0
    #while idx < int(routedata['routenum']):
    renumerate = False

    for idx, x in enumerate(routes):
            
        if x['id'] == routedata['id']:
            if routedata['routenum'] == '-1':
                routes.pop(idx)
            else:
                x.update(routedata)
            break
        # check if routenum is 3.5
        if float(routedata['routenum']) > float(x['routenum']) and float(routedata['routenum']) < float(x['routenum'])+1:
            routedata['routenum']= int(x['routenum'])+1
            routes.insert(int(x['routenum']),routedata )
           
    for idx, x in enumerate(routes):
        x['routenum']=int(idx)+1
    
    competitionsEngine.upsert_routes(routesid, gymid, routeset)

    return json.dumps(routeset)





@skala_api_app.route('/gym/<gymid>/<routesid>/rate', methods=['POST'])
@login_required
def route_rating(gymid, routesid):

    data = request.get_json()
    data = json.loads(data)

    note = data.get('notes_user')
    route_finish_status = data.get('route_finish_status')
    grade = data.get('grade_user')
    user_grade = data.get('grade_user')

    user = competitionsEngine.get_user_by_email(session['email'])
    gym = competitionsEngine.get_gym(gymid)

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    allroutes = all_routes.get(routesid)

    routeset = allroutes.get('routes')
    
    today = datetime.today().date()
    today = today.strftime('%Y-%m-%d')

    route = None
    for route in routeset:
        if route['id'] == data['id']:
            route = route
            break

    activities = activities_db.get_activities_by_date_by_user(today, user['id'])
    
    rating_activity_name = competitionsEngine.reference_data['current_language']['rating_activity_name']

    activity_id = None
    if (len(activities) == 0):
        activity_id = activities_db.add_activity(user, gym, routesid, rating_activity_name, today)
    else:
        for activity in activities:
            if activity.get('gym_id') == gymid:
                activity = activity
                activity_id = activity.get('id')
                break
        if activity_id is None:
            activity_id = activities_db.add_activity(user, gym, routesid, rating_activity_name, today)
    #activity = activities_db.get_activity(activity_id)

    activity = activities_db.add_activity_entry(activity_id, route, route_finish_status, note, user_grade)

    
    return json.dumps(activity)


@skala_api_app.route('/activity/gym/<gym_id>', methods=['GET'])
def get_activity_routes_by_gym_id(gym_id):
    # Assuming activities is a list of all activities
    activities = activities_db.get_activity_routes_by_gym_id(gym_id)

    # List to store matching session entries
    matching_entries = []

    # Iterate through all activities
    #return json.dumps(activities)
    return activities
   


@skala_api_app.route('/gym/<gymid>/save', methods=['POST'])
@login_required
def gym_save(gymid):

    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    body = request.data
    bodyj = request.json

    routeid = formdata['routeid']
    routeline = formdata['routeline']
    color1 = formdata['color1']
    #iscolor2same = formdata['iscolor2same']
    color_modifier = formdata['color_modifier']
    routegrade = formdata['routegrade']
    routename = formdata['routename']
    openedby = formdata['openedby']
    opendate = formdata['opendate']
    notes = formdata['notes']
    routesname = formdata['name'][0]
    permissioned_user = formdata['permissioned_user'][0]

    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return redirect(url_for("skala_api_app.fsgtlogin"))

    routes = []
    for i, routeline1 in enumerate(routeline):
        print (i)
        if routeid[i] == '0':
            routeid[i]=str(uuid.uuid4().hex)
        oneline = competitionsEngine._get_route_dict(routeid[i], str(i+1), routeline[i], color1[i],
                                                     color_modifier[i], routegrade[i],
                                           routename[i], openedby[i], opendate[i], notes[i])
        routes.append(oneline)

    routes_dict = {}
    routes_dict['id'] = gym['routesid']
    routes_dict['name'] = routesname
    routes_dict['routes'] = routes

    gym['routes'] = []

    competitionsEngine.update_gym(gym['id'], gym)
    competitionsEngine.update_routes(gym['routesid'], routes_dict)

    gym = competitionsEngine.get_gym(gym['id'])
    gym['routes'] = []
    routes = competitionsEngine.get_routes(gym['routesid'])

    return routes




@skala_api_app.route('/gyms/<gymid>/<routesid>/save', methods=['POST'])
@login_required
def gym_routes_save(gymid, routesid):
    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    body = request.data
    bodyj = request.json

    routeid = formdata['routeid']
    routeline = formdata['routeline']
    color1 = formdata['color1']
    #iscolor2same = formdata['iscolor2same']
    color_modifier = formdata['color_modifier']
    routegrade = formdata['routegrade']
    routename = formdata['routename']
    openedby = formdata['openedby']
    opendate = formdata['opendate']
    notes = formdata['notes']
    routesname = formdata['name'][0]

    delete = formdata.get('delete')
    save = formdata.get('save')
    copy = formdata.get('copy')

    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return Response("{'a':'b'}", status=401, mimetype='application/json')

    routes = []
    for i, routeline1 in enumerate(routeline):
        if routeid[i] == '0':
            routeid[i]=str(uuid.uuid4().hex)
        oneline = competitionsEngine._get_route_dict(routeid[i], str(i+1), routeline[i], color1[i],
                                                     color_modifier[i], routegrade[i],
                                           routename[i], openedby[i], opendate[i], notes[i])
        routes.append(oneline)

    routes_dict = {}
    routes_dict['id'] = routesid
    routes_dict['name'] = routesname
    routes_dict['routes'] = routes

    if copy is not None:
        newroutesid = str(uuid.uuid4().hex)
        routes_dict['id'] = newroutesid
        routes_dict['name'] = routes_dict['name']+' copy'
        competitionsEngine.upsert_routes(newroutesid, gymid, routes_dict)
        return redirect(f'/gyms/{gymid}/{newroutesid}/edit')

    competitionsEngine.update_routes(routesid, routes_dict)

    # pickup the default routes to be rendered
    routes = competitionsEngine.get_routes(gym.get('routesid'))

    return routes








@skala_api_app.route('/gyms/<gym_id>/update', methods=['POST'])
@login_required
def gyms_update(gym_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    formdata = request.form.to_dict(flat=False)
    gym = competitionsEngine.get_gym(gym_id)

    if not competitionsEngine.has_permission_for_gym(gym_id, user):
        return " { '7788':'no permission to edit gym' }"

    body = request.data
    bodyj = request.json
    files = request.files
    delete = formdata.get('delete')
    save = formdata.get('save')

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if file1.filename is not None and len(file1.filename) > 0:
            imgfilename = gym_id
            imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
            file1.save(imgpath)

    gymName = formdata['gymName'][0]
    #numberOfRoutes = formdata['numberOfRoutes'][0]
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]
    permissioned_user = request.form.get('permissioned_user')

    routesidlist = formdata.get('default_routes')
    if routesidlist is not None:
        routesid = formdata['default_routes'][0]

    if delete is not None:
        competitionsEngine.delete_gym(gym_id)
        competitionsEngine.remove_user_permissions_to_gym(user, gym_id)
        if gym.get('logo_img_id') is not None and len(gym.get('logo_img_id')) > 0:  
            os.remove(os.path.join(UPLOAD_FOLDER, gym['logo_img_id']))
        return redirect(url_for('skala_api_app.gyms'))

    if routesid is None or len(routesid)==0:
        routesid = gym['routesid']

    if len(permissioned_user)>2:
        newuser = competitionsEngine.get_user_by_email(permissioned_user)
        if newuser is not None:
            competitionsEngine.add_user_permissions_to_gym(newuser, gym_id)

    
    gym_json = competitionsEngine.get_gym_json(gym_id, routesid, gymName, None, imgfilename, url, address, organization, None)

    gym.update((k, v) for k, v in gym_json.items() if v is not None)
    competitionsEngine.update_gym(gym_id, gym)

    return


# this doesn't work so well... there is a main_app_ui version that works better
@skala_api_app.route('/image/<img_id>')
def image_route(img_id):
    #bytes_io = competitionsEngine.get_img(img_id)
    #return send_file(bytes_io, mimetype='image/png')

    return send_from_directory(UPLOAD_FOLDER, img_id, mimetype=mime_type)


