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
import qrcode 

from flask import Flask, redirect, url_for, session, request, render_template, send_file, send_from_directory, \
    jsonify, Response, \
    stream_with_context, copy_current_request_context, make_response

import logging

from flask import Blueprint
import activities_db as activity_engine

from io import BytesIO

from flask import send_file
import skala_api

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

#app_ui = Blueprint('app_ui', __name__)

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

import activities_db as activities_db
#from flask_openapi3 import Info, Tag, APIBlueprint
#from flask_openapi3 import OpenAPI

languages = {}

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
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

#tag = Tag(name="UI operations", description='UI operations which return HTML pages - competitionsApp.py')
#app_ui = APIBlueprint('app_ui', __name__, abp_tags=[tag])
app_ui = Blueprint('app_ui', __name__, static_folder='public')

app_ui.debug = True
app_ui.secret_key = 'development'
oauth = OAuth(app_ui)

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





app_ui.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

UPLOAD_FOLDER = os.path.join(DATA_DIRECTORY,'uploads')

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

#app_ui.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# User session management setup
# https://flask-login.readthedocs.io/en/latest



@app_ui.before_request
def x(*args, **kwargs):
    if not session.get('language'):
        #kk = competitionsEngine.supported_languages.keys()
        session['language'] = request.accept_languages.best_match(competitionsEngine.supported_languages.keys())
        print ("setting language to "+str(request.accept_languages)+" ->"+str(session['language']))
        ##return redirect('/en' + request.full_path)


@app_ui.route('/language/<language>')
def set_language(language=None):
    session['language'] = language

    #competitionsEngine.reference_data['current_language'] = session['language']

    langpack = competitionsEngine.reference_data['languages'][language]
    competitionsEngine.reference_data['current_language'] = langpack

    return redirect('/')
    #return redirect(url_for('getCompetitionDashboard'))


def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and session.get('expires_at') is not None:
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("app_ui.fsgtlogin"))
    return decorated_function



def admin_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and (session.get('name') == 'David Mossakowski' or 
            session.get('name') == 'Sebastiao Correia'):
            now = int(datetime.now().timestamp())
            #expiresAt = session['expires_at']
            expiresAtLocaltime = session['expires_at_localtime']
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("app_ui.fsgtlogin"))
    return decorated_function



@app_ui.get("/aa")
def index11():
    if session.get('username'):
        return '<a class="button" href="/login">logged in </a>'+session.get('username')

    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'





@app_ui.route('/competitionRawAdmin', methods=['GET'])
@login_required
@admin_required
def fsgtadminget():
    """
    Load Admin page from competitionRawAdmin.html
    """
    edittype = request.args.get('edittype')
    id = request.args.get('id')
    action = request.args.get('action')
    jsondata = request.args.get('jsondata')
    jsonobject = None

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.post('/competitionRawAdmin')
@login_required
@admin_required
def fsgtadmin():
    """
    
    Do admin action

    This is an admin action
    """
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


    elif edittype == 'activities':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            # None is gymid but this is ok as the routes id will be found
            # competitionsEngine.upsert_routes(id, None, jsonobject)
            return

        if id is not None and action == 'find':
            jsonobject = activities_db.get_activities(id)

        if id is not None and action == 'findall':
            jsonobject = activities_db.get_activities(id)

    else :
        jsonobject = {"error": "choose edit type" }

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.route('/competition_admin/<competition_id>', methods=['GET'])
#, summary='returns competitionAdmin.html', 
 #           responses={"default": {"description": "Render template competitionAdmin.html"}})
@login_required
def competition_admin_get(competition_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competition_id)

    user_list = competitionsEngine.get_all_user_emails()
    if user is None or competition is None or not competitionsEngine.can_edit_competition(user,competition):
        session["wants_url"] = request.url
        return redirect(url_for('app_ui.getCompetition', competitionId=competition['id']))

    all_routes = competitionsEngine.get_routes_by_gym_id(competition['gym_id'])

    return render_template('competitionAdmin.html',
                           user=user,
                           competition=competition,
                           user_list=user_list,
                           competitionId=competition_id,
                           all_routes = all_routes,
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.route('/competition_admin/<competition_id>', methods=['POST'])
@login_required
def competition_admin_post(competition_id):
    remove_climber = request.form.get('remove_climber')
    update_status = request.form.get('update_status')
    permission_admin_user = request.form.get('permission_admin_user')
    permission_scorer_user = request.form.get('permission_scorer_user')
    max_participants = request.form.get('max_participants')
    # get climber id in competition admin table (not none when a change is saved)
    climber_id = request.form.get('update_climber')


    competition_update_button = request.form.get('competition_update_button')
    delete_competition_button = request.form.get('delete_competition_button')
    change_poster_button = request.form.get('change_poster_button')

    edittype = request.form.get('edittype')
    permissioned_user = request.form.get('permissioned_user')

    id = request.form.get('id')
    action = request.form.get('action')
    competition_status = request.form.get('competition_status')

    jsondata = request.form.get('jsondata')
    comp = {}
    jsonobject = None

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if file1.filename is not None and len(file1.filename) > 0:
            imgfilename = competition_id
            imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
            file1.save(imgpath)

    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competition_id)

    if user is None or competition is None or not competitionsEngine.can_edit_competition(user,competition):
        session["wants_url"] = request.url
        return redirect(url_for("app_ui.fsgtlogin"))


    
    
    # add this competition to another user's permissions
    # remove this competition from another users permissions
    # change the state of a competition
    # remove climber from a competition

    if permission_admin_user is not None:
        user2 = competitionsEngine.get_user_by_email(permissioned_user)
        competitionsEngine.modify_user_permissions_to_competition(user2, competition_id)
        competitionsEngine.add_user_permission_edit_competition(user2)


    if permission_scorer_user is not None:
        user2 = competitionsEngine.get_user_by_email(permissioned_user)
        competitionsEngine.modify_user_permissions_to_competition(user2, competition_id)
        competitionsEngine.add_user_permission_update_routes(user2)


    if update_status is not None:
        competition['status'] = int(competition_status)
        competitionsEngine.update_competition(competition_id, competition)

    if remove_climber is not None:
        competition['climbers'].pop(remove_climber)
        competitionsEngine.update_competition(competition['id'], competition)

    if climber_id is not None:
        competition['climbers'][climber_id]['name'] = request.form.get('name_'+ climber_id)
        competition['climbers'][climber_id]['sex'] = request.form.get('sex_'+ climber_id)
        competition['climbers'][climber_id]['club'] = request.form.get('club_'+ climber_id)
        competition['climbers'][climber_id]['email'] = request.form.get('email_'+ climber_id)
        try:
            # Attempt to retrieve the category from the form data and convert it to an integer
            competition['climbers'][climber_id]['category'] = int(request.form.get('category_' + str(climber_id)))
        except (ValueError, TypeError):
            # Handle the exception if the conversion fails
            print("The provided category is not a valid integer for climber " + competition['climbers'][climber_id]['name'])
            # Set to a default value or handle the error as appropriate
            competition['climbers'][climber_id]['category'] = 0  # Replace default_value with whatever default you wish to use
        competitionsEngine.update_competition(competition['id'], competition)

    if competition_update_button is not None:
        competition_name = request.form.get('competition_name')
        competition_date = request.form.get('competition_date')
        competition_routes = request.form.get('competition_routes')
        max_participants = request.form.get('max_participants')
        # update gym name in the competition if Gym Name is changed somewhere else
        gym = competitionsEngine.get_gym(competition['gym_id'])
        if gym is not None:
            if gym['name'] != competition['gym']:
                competition['gym']=gym['name']
        competition['max_participants']=max_participants

        competitionsEngine.update_competition_details(competition, competition_name, competition_date, competition_routes)


    if delete_competition_button is not None:
        if competitionsEngine.competition_can_be_deleted(competition):
            competitionsEngine.delete_competition(competition['id'])
            return redirect(f'/competitionDashboard')


    if change_poster_button is not None and imgfilename is not None:
        competitionsEngine.update_competition(competition['id'], competition)


    user_list = competitionsEngine.get_all_user_emails()
    all_routes = competitionsEngine.get_routes_by_gym_id(competition['gym_id'])
            


    return render_template('competitionAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           user=user,
                           competition=competition,
                           user_list=user_list,
                           competitionId=competition_id,
                           all_routes = all_routes,
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.route('/fsgtadmin/<edittype>')
def fsgtadminedit(edittype):
    j = request.args.get('jsondata')

    if edittype == 'user' and j['email'] is not None:
        competitionsEngine.upsert_user(j)

    return render_template('competitionRawAdmin.html',
                           reference_data=competitionsEngine.reference_data)


@app_ui.route('/loginchoice')
def fsgtlogin():
    return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data
                           )






@app_ui.route('/activities', methods=['GET'])
@login_required
def activities():
    user = competitionsEngine.get_user_by_email(session['email'])

    return render_template('activities.html',
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           today=date.today()
                           )


#@app_ui.route('/activities/<activity_id>', methods=['GET'], description='returns activity-detail.html')
@app_ui.route('/activities/<activity_id>', methods=['GET'])
#@login_required
def activity_detail(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    activity = activity_engine.get_activity(activity_id)
    gym = competitionsEngine.get_gym(activity['gym_id'])

    #gym = competitionsEngine.get_gym(journey['gym_id'])

    if activity.get('routes_id') is None:
        routes = competitionsEngine.get_routes("7134a8ef-fa2e-4672-a247-115773183bcd")  # should return  Nanterre routes
    else:
        routes = competitionsEngine.get_routes(activity['routes_id'])

    return render_template('activity-detail.html',
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           activity=activity,
                           routes=routes,
                           gym=gym,
                           today=date.today(),
                           activity_id=activity_id,
                           )


@app_ui.route('/activities/dialog', methods=['GET'])
#@login_required
def activity_detail_dialog():

    user = competitionsEngine.get_user_by_email(session['email'])
    activity = activity_engine.get_activity(activity_id)
    gym = competitionsEngine.get_gym(activity['gym_id'])


    return render_template('activity-detail.html',
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           activity=activity,
                           routes=routes,
                           gym=gym,
                           today=date.today(),
                           activity_id=activity_id,
                           )
 

@app_ui.route('/journey/add', methods=['POST'])
@login_required
def journey_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    date = request.form.get('date')
    gym_id = request.form.get('gym_id')
    comp = {}
    gym = competitionsEngine.get_gym(gym_id)

    journey = activity_engine.add_journey_session(user,gym_id, gym.get('routesid'), date)
    #journey_id = user.get('journey_id')

    #if journey_id is None:
    #    journey = activity_engine.add_journey(user, description)

    journeys = activity_engine._get_journey_sessions_by_user_id(user.get('id'))
    return render_template('skala-journey.html',
                           user=user,
                           journeys=journeys,
                           journey=journey,
                           reference_data=competitionsEngine.reference_data
                           )


@app_ui.route('/journey/<journey_id>', methods=['GET'])
@login_required
def journey_session(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    journey = activity_engine.get_journey_session(journey_id)

    #gym = competitionsEngine.get_gym(journey['gym_id'])

    if journey.get('routes_id') is None:
        routes = competitionsEngine.get_routes("7134a8ef-fa2e-4672-a247-115773183bcd")  # should return  Nanterre routes
    else:
        routes = competitionsEngine.get_routes(journey['routes_id'])

    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@app_ui.route('/journey/<journey_id>/add', methods=['POST'])
@login_required
def journey_session_entry_add(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    route_finish_status = request.form.get('route_finish_status')
    route_id = request.form.get('route')
    notes = request.form.get('notes')

    comp = {}

    journey = activity_engine.get_journey_session(journey_id)

    journey = activity_engine.add_journey_session_entry(journey_id,route_id, route_finish_status, notes)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@app_ui.route('/journey/<journey_id>/<route_id>/remove', methods=['GET'])
@login_required
def journey_session_remove(journey_id, route_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    journey = activity_engine.get_journey_session(journey_id)

    activity_engine.remove_journey_session(journey_id, route_id)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )



@app_ui.route('/privacy')
def privacy():
    return render_template('privacy.html',
                           reference_data=competitionsEngine.reference_data
                           )



@app_ui.route('/')
def index():
    langs = competitionsEngine.reference_data['languages']

    user = competitionsEngine.get_user_by_email(session.get('email'))
    competitions= competitionsEngine.getCompetitions()

    return render_template('skala3ma.html',
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           langpack=languages['en_US'],
                            **session
                           )


@app_ui.route('/main')
def main():
    return redirect("/")


@app_ui.route('/competitionDashboard')
def getCompetitionDashboard():
    # select season year depending on current month;
    # e.g. if 2023-10-01 then season is 2023-24 
    # if 2023-05-01 then season is 2022-23
    current_year = datetime.now().year
    current_month = datetime.now().month
    season = current_year if current_month >= 9 else current_year-1 
    return competitions_by_year(str(season))


@app_ui.route('/competitions/year/<year>')
def competitions_by_year(year):

    username = session.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    if not year.isdigit():
        year = datetime.now().year
    can_create_competition = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is not None:
        can_create_competition = competitionsEngine.can_create_competition(user)
    subheader_message = request.accept_languages
    langs = competitionsEngine.reference_data['languages']
    
    competitions3 = competitionsEngine.get_competitions_by_year(year)
    
    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions3,
                           competitionName=None,
                           session=session,
                           user=user,
                           year=year,
                           reference_data=competitionsEngine.reference_data,
                           langpack=languages['en_US'],
                           can_create_competition=can_create_competition,
                            **session
                           )


@app_ui.route('/newCompetition', methods=['GET'])
@login_required
def new_competition():

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

    all_gyms = competitionsEngine.get_gyms()

    clubs = []

    for gymid in all_gyms:
        gymname = all_gyms[gymid]['name']
        routes = competitionsEngine.get_routes_by_gym_id(gymid)
        for routeid in routes:
            clubs.append ({'gymname':gymname, 'gymid':gymid, 'routesid':routeid, 'routesname':routes[routeid]['name']})


    return render_template('newCompetition.html',
                           competitionName=None,
                           session=session,
                           gyms=gyms,
                           clubs=clubs,
                           reference_data=competitionsEngine.reference_data,

                            **session)


# method to add a new competition
@app_ui.route('/newCompetition', methods=['POST'])
@login_required
def new_competition_post():
    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    #print(username)

    #username = request.args.get('username')
    name = request.form.get('name')
    date = request.form.get('date')
    #gym = request.form.get('gym')
    routesid = request.form.get('routes')
    competition_type = request.form.get('competition_type')
    max_participants = request.form.get('max_participants')

    comp = {}
    competitionId = None

    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is None or not competitionsEngine.can_create_competition(user):
        return redirect(url_for('app_ui.fsgtlogin', competitionId=competitionId))

    if name is not None and date is not None and routesid is not None and max_participants is not None:
        competitionId = competitionsEngine.addCompetition(None, name, date, routesid, max_participants,
                                                          competition_type=competition_type)
        # now if an image was provided, save it under the competition id
        # there is only one main image allowed per competition for now
        # any new image will overwrite the previous one
        if 'file1' in request.files:
            file1 = request.files['file1']
            if file1.filename is not None and len(file1.filename) > 0:
                imgpath = os.path.join(UPLOAD_FOLDER, competitionId)
                file1.save(imgpath)


        competitionsEngine.modify_user_permissions_to_competition(user, competitionId, "ADD")
        comp = getCompetition(competitionId)
        return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))

    subheader_message='Welcome '
    competitions= competitionsEngine.getCompetitions()


    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           reference_data=competitionsEngine.reference_data,
                            **session)




@app_ui.route('/competitionDashboard/<competitionId>/register')
#@login_required
def addCompetitionClimber(competitionId):
    useremail = session.get('email')
    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    otherclub = request.args.get('otherclub')
    category = request.args.get('category')

    comp = competitionsEngine.getCompetition(competitionId)
    user = competitionsEngine.get_user_by_email(useremail)
    climber_id = str(uuid.uuid4().hex)
    if user is not None:
        climber_id = user['id']
    form_user = competitionsEngine.get_user_by_email(email)

    competition_accepts_registrations = competitionsEngine.competition_accepts_registrations(comp)
    error_code = ''
    if not competition_accepts_registrations:
        error_code = "error5322"
    
    is_registered = competitionsEngine.is_registered(user, comp)

    climber = None

    # check if user with this email is known and should login themselves to register
    if user is None and form_user is not None and (
            form_user.get('fname') is not None or form_user.get('gname') is not None):
        error_code = "error5316" 

    # the user found by email on form is already registered
    is_form_user_registered = competitionsEngine.is_registered(form_user, comp)
    if is_form_user_registered:
        error_code = "error5321"
    
    if not error_code and not is_registered and firstname is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.get_climber_by_email(email)
        name = firstname + " " + lastname

        try:
            if club not in competitionsEngine.clubs.values():
                club = otherclub
            climber = competitionsEngine.addClimber(climber_id, competitionId, email, name, firstname, lastname, club, sex, category)
            competitionsEngine.user_registered_for_competition(climber['id'], name, firstname, lastname, email, climber['sex'],
                                                               climber['club'], climber['category'])
            comp = competitionsEngine.getCompetition(competitionId)
            competitionName = comp['name']
            #subheader_message = 'You have been registered! Thanks!'
            #return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))
            return render_template("competitionClimberRegistered.html", 
                    competitionId=competitionId,
                    competition=comp,
                    reference_data=competitionsEngine.reference_data,
                    library=None,
                    **session)

        except ValueError:
            # this user is alrady registered
            error_code = "error5321"
            
    ##   comp=None # this is to not show the list of climbers before registration

    #competitions = competitionsEngine.getCompetitions()
    name = session.get('name')

    if name is None:
        name = ""

    can_unregister = competitionsEngine.can_unregister(user, comp)
    enable_registration = False
    if competition_accepts_registrations and not is_registered and not error_code:
        enable_registration = True

    return render_template('competitionClimber.html',
                           error_code=error_code,
                           competition=comp,
                           competitionId=competitionId,
                           climber=climber,
                           user = user,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=useremail,
                           logged_name=name,
                           can_unregister=can_unregister,
                           is_registered=is_registered,
                           enable_registration=enable_registration,
                            **session)




@app_ui.route('/competitionDashboard/<competitionId>/unregister')
@login_required
def unregister(competitionId):
    if session.get('email') is not None:
        climber = competitionsEngine.get_user_by_email(session.get('email'))
        if climber is not None:
            competitionsEngine.removeClimber(climber['id'], competitionId)
            return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))
        
    return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))



@app_ui.route('/user')
def get_user():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               reference_data=competitionsEngine.reference_data,
                               subheader_message="No user found",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))

    subheader_message = request.args.get('update_details')

    email = session.get('email')
    name = session.get('name')

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


@app_ui.route('/updateuser')
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
                               error_message = "All fields are required",
                               subheader_message=subheader_message,
                               competitionId=None,
                               climber=climber,
                               reference_data=competitionsEngine.reference_data,
                               logged_email=email,
                               logged_name=name,
                               **session)

    else:
        climber = competitionsEngine.user_self_update(climber, name, firstname, lastname, nick, sex, club, category)
        subheader_message = 'Your details were saved'

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





@app_ui.route('/myresultats')
@login_required
def myskala():
    subheader_message = "My skala"
    
    competition={}


    return render_template("myskala.html", 
                           subheader_message=subheader_message,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           library=None,
                           **session)




@app_ui.route('/competitionDetails/<competitionId>')
#@login_required
def getCompetition(competitionId):
    #competitionId = request.args.get('competitionId')


    #   logging.info(session['id']+' competitionId '+competitionId)
    # r = request
    # username = request.args.get('username')

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


    subheader_message = "CompetitionDetails '" + competition['name'] + "' on "+competition['date']

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))



    return render_template("competitionDetails.html", competitionId=competitionId,
                           competition=competition,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data,
                           library=None,
                           **session)



@app_ui.route('/competitionResults/<competitionId>')
#@login_required
def getCompetitionResults(competitionId):
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


    rankings = competitionsEngine.get_sorted_rankings(competition)



    return render_template("competitionResults.html", 
                           competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           rankings = rankings,
                           **session)



# Statistics for a competition
@app_ui.route('/competitionStats/<competitionId>')
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

    rankings = competitionsEngine.get_sorted_rankings(competition)


    return render_template("competitionStats.html", competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           rankings = rankings,
                           **session)



#@app_ui.route('/competitionDashboard/<competitionId>/climber/<climberId>')
#@login_required
# THIS IS NOT USED PROBABLY!!!!
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
                                   subheader_message="Climber routes saved",
                                    reference_data=competitionsEngine.reference_data,
                                   **session)


        climber = competitionsEngine.getClimber(competitionId,climberId)


    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No climber found",
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




@app_ui.route('/competitionResults/<competitionId>/download')
def downloadCompetitionCsv(competitionId):

    competition = competitionsEngine.getCompetition(competitionId)
    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    if routes is not None:
        routes = routes.get('routes')



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
        data['grades'] = ""
        grades = []
        for routenum in competition['climbers'][climberid]['routesClimbed']:
            grades.append(routes[routenum-1]['grade'])
        
        #data['grades'] = data['grades']+ routes[routenum-1]['grade'] + " "
        #grades.append(routes[routenum-1]['grad e'])
        grades = sorted(grades)
        data['grades'] = ' '.join(grades)
        data['newscore'] = competitionsEngine.calculate_score(grades)

        for i in range(100):
            data.pop('id', None)
            data.pop('email', None)
            data.pop('name',None)
            data.pop('routesClimbed2',None)

            data.pop('AAAAAA',None)

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



@app_ui.route('/competitionRoutesEntry/<competitionId>')
@login_required
def competitionRoutesList(competitionId):
    #competitionId = request.args.get('competitionId')

    user = competitionsEngine.get_user_by_email(session['email'])

    competition = competitionsEngine.getCompetition(competitionId)

    error_code = ""
    if not competitionsEngine.can_update_routes(user,competition):
        error_code = "error5314"

    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')

    if len(competition.get('climbers').values())>0 and 'lastname' in list(competition.get('climbers').values())[0].keys():
        sorted_data = dict(sorted(competition.get('climbers').items(), key=lambda x: x[1]['lastname'].upper()))
        competition['climbers']= sorted_data

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("competitionClimberList.html",
                           error_code=error_code,
                           user=user,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)



# enter competition climbed routes for a climber and save them
@app_ui.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['GET'])
@login_required
def routes_climbed(competitionId, climberId):

    if climberId is not None:
        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No climber found",
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
        return redirect(url_for('app_ui.competitionRoutesList', competitionId=competitionId))


    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)

    climber_name = climber.get('name')
    climber_club = climber.get('club')

    #routes = routes['routes']
    subheader_message = str(climber_name)+" - "+str(climber_club)

    return render_template("competitionRoutesEntry.html", climberId=climberId,
                           climber=climber,
                           routes=routes,
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)


@app_ui.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['POST'])
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
                                   subheader_message="Routes saved",
                                    reference_data=competitionsEngine.reference_data,
                                   **session)

        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No climber found",
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



@app_ui.route('/migrategyms')
def migrategyms():
    gyms = competitionsEngine.get_gyms()

    nanterre = gyms["1"]
    nanterre['logoimg'] = 'logo-ESN-HD-copy-1030x1030.png'
    nanterre['homepage'] = 'https://www.esnanterre.com/'

    competitionsEngine.update_gym("1", "667", json.dumps(nanterre))
    return redirect(url_for('app_ui.gyms'))




######## GYMS
@app_ui.route('/gyms')
def gyms():
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    gyms = competitionsEngine.get_gyms()
    can_create_gym = False
    email = session.get('email')
    user = None
    if email is not None:
        user = competitionsEngine.get_user_by_email(email)

    if user is not None:
        can_create_gym = competitionsEngine.can_create_gym(user)
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('gyms.html',
                           competitionId=None,
                           user=user,
                           gyms=gyms,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                           can_create_gym=can_create_gym,
                            **session)




@app_ui.route('/gyms/<gymid>')
def gym_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    #gym['routesid']='abc1'

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    
    #routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    routes_dict = competitionsEngine.get_routes_by_gym_id(gymid)
    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is not None:
        user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
        can_create_gym = competitionsEngine.can_create_gym(user)
     
    #routes1 = competitionsEngine.get_routes(gym['routesid'])
    routes = routes_dict.get(gym['routesid'])
    routesid = gym['routesid']
    return render_template('gym-main.html',
                           gymid=gymid,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=None,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )



@app_ui.route('/gyms/<gym_id>/<routesid>', methods=['GET'])
#@login_required
def gym_routes_new(gym_id, routesid):


    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    if user is not None:
        user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
        can_create_gym = competitionsEngine.can_create_gym(user)
        #activities = skala_api.get_activities()


    return render_template('gym-routes.html',
                           gymid=gym_id,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )







@app_ui.route('/gyms/<gymid>/data')
def gym_data(gymid):
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(gym['routesid'])
    gym['rows']=routes
    return json.dumps(gym)


@app_ui.route('/gyms/<gymid>/edit', methods=['GET'])
@login_required
def gym_edit(gymid):
    gym = competitionsEngine.get_gym(gymid)
    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    routes = all_routes.get(gym['routesid'])
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_list = competitionsEngine.get_all_user_emails()
    return render_template('gymedit.html',
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user_list=user_list,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           )


# NOT USED MOST LIKELY
@app_ui.route('/gyms/<gymid>/edit', methods=['POST'])
@login_required
def gym_save(gymid):
    raise ValueError("Not implemented")
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
    can_create_gyms = competitionsEngine.can_create_gym(user)

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return redirect(url_for("app_ui.fsgtlogin"))

    routes = []
    for i, routeline1 in enumerate(routeline):
        #print (i)
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

    return render_template('gyms.html',
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           can_create_gyms=can_create_gyms,
                           )



# this is the old HTML form routes editor
@app_ui.route('/gyms/<gym_id>/<routesid>/edit', methods=['GET'])
@login_required
def gym_routes_edit(gym_id, routesid):
    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)

    user = competitionsEngine.get_user_by_email(session.get('email'))
    return render_template('gym-routes-batch-edit.html',
                           gymid=gym_id,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           )




@app_ui.route('/gyms/<gymid>/climbers')
def gym_climbers_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    #gym['routesid']='abc1'

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    
    #routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    routes_dict = competitionsEngine.get_routes_by_gym_id(gymid)

    #routes1 = competitionsEngine.get_routes(gym['routesid'])
    routes = routes_dict.get(gym['routesid'])
    routesid = gym['routesid']
    return render_template('gym-climbers.html',
                           gymid=gymid,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=None,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )



@app_ui.errorhandler(413)
def request_entity_too_large(error):    
    print(error)
    content_length = request.content_length
    print(content_length)
    return 'Request Too Large', 413


#saving old type of html routes editor
@app_ui.route('/gyms/<gymid>/<routesid>/edit', methods=['POST'])
@login_required
def gym_routes_save(gymid, routesid):
    #args1 = request.args

    #body = request.data
    #bodyj = request.json

    formdata = request.form.to_dict(flat=False)

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
        return redirect(url_for("app_ui.fsgtlogin"))

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

    return redirect(f'/gyms/{gymid}/{routesid}')



@app_ui.route('/gyms/<gym_id>/<routesid>/routes_csv')
def downloadRoutesCsv(gym_id, routesid):

    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)

    filename = 'routes-'+routes['id']
    routes = routes['routes']

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    data_file = open('jsonoutput2.csv', 'w', newline='')
    csv_writer = csv.writer(data_file)

    count = 0
    for route in routes:
        route.pop('id',None)
        route.pop('colorfr',None)
        
        if count == 0:
            header = route.keys()
            csv_writer.writerow(header)
            writer.writerow(header)
            count += 1
        out = {}
        

        csv_writer.writerow(route.values())
        writer.writerow(route.values())

    data_file.close()


    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                     "attachment; filename="+filename+".csv"})







@app_ui.route('/gyms/<gym_id>/<routesid>/download')
def downloadRoutes(gym_id, routesid):

    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)

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

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    data_file = open('jsonoutput.csv', 'w', newline='')
    csv_writer = csv.writer(data_file)

    count = 0
    data = []
    header = routes['routes'][0].copy()
    header.pop('id')
    header.pop('colorfr')
    header.pop('color_modifier')
    header.pop('opendate')
    header.pop('notes')
    header.pop('openedby')
    
    data = routes['routes']
    csv_writer.writerow(header)
    writer.writerow(header)
    count += 1
    out = {}
    #rethtml="<table>"
    #rethtml="<style>p.one { border-style: solid; border-color: red;}"
    rethtml=""

    for route in routes['routes']:
        route.pop('id')
        route.pop('colorfr')
        route.pop('color_modifier')
        route.pop('opendate')
        route.pop('notes')
        route.pop('openedby')
        
        csv_writer.writerow(route.values())
        writer.writerow(route.values())
        #rethtml+="<tr><td>"+route['routenum']+"</td><td bgcolor="+route['color1']+">&nbsp;&nbsp;&nbsp;</td><td>"+route['grade']+"</td></tr>"
        rethtml+="<div style='border:1px solid "+route['color1']+"'>"+str(route['routenum'])+"</td><td bgcolor="+route['color1']+">&nbsp;&nbsp;&nbsp; "+route['grade']+" "
        rethtml+="</div>"

    #rethtml+="</table>"
    data_file.close()

    return render_template('gym-print.html',
                           gymid=gym_id,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@app_ui.route('/gyms/<gymid>/edittest')
def edit_test(gymid):
    user = competitionsEngine.get_user_by_email(session['email'])

    return render_template('tabletest.html',
                           reference_data=competitionsEngine.reference_data)


@app_ui.route('/gyms/add', methods=['GET'])
@login_required
def gyms_add_form():
    user = competitionsEngine.get_user_by_email(session['email'])

    if competitionsEngine.can_create_gym(user):
        return render_template('gym-add.html',
                           competitionId=None,
                           gyms=gyms,
                           reference_data=competitionsEngine.reference_data,
                           **session)
    else:
        return render_template('competitionNoPermission.html',
                               competitionId=None,
                               gyms=gyms,
                               reference_data=competitionsEngine.reference_data,
                               **session)


@app_ui.route('/gyms/add', methods=['POST'])
@login_required
def gyms_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    can_create_gym = competitionsEngine.can_create_gym(user)
    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    #body = request.data
    #bodyj = request.json
    files = request.files
    gym_id = str(uuid.uuid4().hex)
    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if file1.filename is not None and len(file1.filename) > 0:
            #random = str(uuid.uuid4().hex)
            imgfilename = gym_id
            imgpath = os.path.join(UPLOAD_FOLDER, gym_id)
            file1.save(imgpath)

    gymName = formdata['gymName'][0]
    numberOfRoutes = formdata['numberOfRoutes'][0]
    if numberOfRoutes is None or len(numberOfRoutes)==0:
        numberOfRoutes = 10  #default value of routes for a gym
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]

    routes = competitionsEngine.generate_dummy_routes(int(numberOfRoutes))
    competitionsEngine.upsert_routes(routes['id'], gym_id, routes)
    gym = competitionsEngine.add_gym(user, gym_id, routes['id'], gymName, imgfilename, url, address, organization, [])
    gym['routes'] = routes
    routes_id = routes['id']
    user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
    
    #competitionsEngine.update_gym(gym_id, gym)
    #gym2 = competitionsEngine.get_gym(gym_id)
    #all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    #routes=gym2['routes']
    #gyms = competitionsEngine.get_gyms()

    return render_template('gym-routes.html',
                           competitionId=None,
                           gymid=gym_id,
                           routesid=routes_id,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=session['email'],
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                            **session)



# Main method for updating gym data 
@app_ui.route('/gyms/<gym_id>/update', methods=['POST'])
@login_required
def gyms_update(gym_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    formdata = request.form.to_dict(flat=False)

    gym = competitionsEngine.get_gym(gym_id)


    if not competitionsEngine.has_permission_for_gym(gym_id, user):
        return render_template('competitionNoPermission.html',
                               error_code="error5315",
                               competitionId=None,
                               gyms=gyms,
                               reference_data=competitionsEngine.reference_data,
                               **session)

    body = request.data
    #bodyj = request.json
    files = request.files
    delete = formdata.get('delete')
    save = formdata.get('save')

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if len(file1.filename) > 0:
            #random = str(uuid.uuid4().hex)
            imgfilename = gym_id
            imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
            file1.save(imgpath)

    gymName = formdata['gymName'][0]
    #numberOfRoutes = formdata['numberOfRoutes'][0]
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]
    permissioned_user = request.form.get('permissioned_user')
    lat = formdata['lat'][0]
    lon = formdata['lon'][0]

    routesidlist = formdata.get('default_routes')
    if routesidlist is not None:
        routesid = formdata['default_routes'][0]

    if delete is not None:
        competitionsEngine.delete_gym(gym_id)
        competitionsEngine.remove_user_permissions_to_gym(user, gym_id)
        if gym.get('logo_img_id') is not None and len(gym.get('logo_img_id')) > 0:
            if os.path.exists(os.path.join(UPLOAD_FOLDER, gym['logo_img_id'])):
                os.remove(os.path.join(UPLOAD_FOLDER, gym['logo_img_id']))
        return redirect(url_for('app_ui.gyms'))

    if routesid is None or len(routesid)==0:
        routesid = gym['routesid']

    if len(permissioned_user)>2:
        newuser = competitionsEngine.get_user_by_email(permissioned_user)
        if newuser is not None:
            competitionsEngine.add_user_permissions_to_gym(newuser, gym_id)

    #gymid, routesid, name, added_by, logo_img_id, homepage, address, organization, routesA):
    gym_json = competitionsEngine.get_gym_json(gym_id, routesid, gymName, None, imgfilename, url, address, organization, None)
    competitionsEngine.update_gym_coordinates(gym_json, lat, lon)
    # 20240911 - this line is not clear as to what it does actually - some comments would be welcome here from the author
    gym.update((k, v) for k, v in gym_json.items() if v is not None)
    competitionsEngine.update_gym(gym_id, gym)

    return redirect(url_for('app_ui.gym_by_id', gymid=gym_id))







@app_ui.route('/competitionDashboard/loadData')
def loadData():
    competitionsEngine.init()
    subheader_message='data loaded'
    return render_template("competitionDashboard.html", climberId=None,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data)


@app_ui.route('/image/')
def image_route0():
    #bytes_io = competitionsEngine.get_img(img_id)
    #return send_file(bytes_io, mimetype='image/png')

    #return send_file(os.path.join(UPLOAD_FOLDER, img_id))
    #return app_ui.send_static_file("images/favicon.png")
    return app_ui.send_static_file("images/fsgt-logo-me.png")


@app_ui.route('/image/<img_id>')
def image_route(img_id):
    #bytes_io = competitionsEngine.get_img(img_id)
    #return send_file(bytes_io, mimetype='image/png')

    #return send_file(os.path.join(UPLOAD_FOLDER, img_id))

    #print('image_route', img_id)
    if (img_id is not None and os.path.exists(os.path.join(UPLOAD_FOLDER, img_id))):
        return send_from_directory(UPLOAD_FOLDER, img_id)
    else:
        #return app_ui.send_static_file("images/favicon.png")
        return app_ui.send_static_file("images/fsgt-logo-me.png")
    



@app_ui.route('/qr', methods=['GET'])
def qr():
    try:
        # Get the URL from the query string
        url = request.args.get('url')

        # Create the QR code image
        img = qrcode.make(url)

        buffer = io.BytesIO()
        img.save(buffer)
        buffer.seek(0)

        response = make_response(buffer.getvalue())
        #response.headers['Content-Disposition'] = 'attachment; filename=qr-code.png'
        response.mimetype = 'image/png' 

        return response
    except Exception as e:
        print(e)
        return 'Internal Server Error', 500