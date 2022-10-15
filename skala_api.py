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

from flask import Flask, redirect, url_for, session, request, render_template, send_file, send_from_directory, jsonify, Response, \
    stream_with_context, copy_current_request_context, g

import logging
from dotenv import load_dotenv

from flask import Blueprint
import skala_journey as journeys_engine

from io import BytesIO

from flask import send_file


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

#skala_api_app = Blueprint('skala_api_app', __name__)

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

languages = {}

load_dotenv()

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

# ID, date, name, location
COMPETITIONS_TABLE = "competitions"
# ID, name, club, m/f, list of climbs
CLIMBERS_TABLE = "climbers"

FSGT_APP_ID = os.getenv('FSGT_APP_ID')
FSGT_APP_SECRET = os.getenv('FSGT_APP_SECRET')
DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

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
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

# skala_api_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# User session management setup
# https://flask-login.readthedocs.io/en/latest

@skala_api_app.before_request
def x(*args, **kwargs):
    if not session.get('language'):
        #kk = competitionsEngine.supported_languages.keys()
        session['language'] = request.accept_languages.best_match(competitionsEngine.supported_languages.keys())
        print ("setting language to "+str(request.accept_languages)+" ->"+str(session['language']))


@skala_api_app.route('/api/language/<language>')
def set_language(language=None):
    session['language'] = language

    langpack = competitionsEngine.reference_data['languages'][language]
    competitionsEngine.reference_data['current_language'] = langpack

    return language


def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session is not None and session.get('expires_at') is not None:
            now = int(datetime.now().timestamp())
            expiresAtLocaltime = session['expires_at_localtime']

            if expiresAtLocaltime < now:
                session["wants_url"] = request.url
                if session['authsource'] == 'facebook':
                    return redirect(url_for("facebook"))
                if session['authsource'] == 'google':
                    return redirect(url_for("googleauth"))

            else:
                return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("skala_api_app.fsgtlogin"))
    return decorated_function


def admin_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and session.get('name') == 'David Mossakowski':
            now = int(datetime.now().timestamp())
            expiresAtLocaltime = session['expires_at_localtime']
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("skala_api_app.fsgtlogin"))
    return decorated_function


def competition_authentication_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and (session.get('name') == 'David Mossakowski'
            or competitionsEngine.can_create_competition()):
            now = int(datetime.now().timestamp())
            #expiresAt = session['expires_at']
            expiresAtLocaltime = session['expires_at_localtime']
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("skala_api_app.fsgtlogin"))
    return decorated_function


@skala_api_app.route('/competitionRawAdmin', methods=['POST'])
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


@skala_api_app.route('/competition_admin/<competition_id>', methods=['POST'])
@login_required
def competition_admin_post(competition_id):
    remove_climber = request.form.get('remove_climber')
    update_status = request.form.get('update_status')
    permission_user = request.form.get('permission_user')

    competition_update_button = request.form.get('competition_update_button')

    edittype = request.form.get('edittype')
    permissioned_user = request.form.get('permissioned_user')

    id = request.form.get('id')
    action = request.form.get('action')
    competition_status = request.form.get('competition_status')

    jsondata = request.form.get('jsondata')
    comp = {}
    jsonobject = None

    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competition_id)

    if user is None or competition is None or not competitionsEngine.can_edit_competition(user,competition):
        session["wants_url"] = request.url
        return redirect(url_for("skala_api_app.fsgtlogin"))

    # add this competition to another user's permissions
    # remove this competition from another users permissions
    # change the state of a competition
    # remove climber from a competition

    if permission_user is not None:
        user2 = competitionsEngine.get_user_by_email(permissioned_user)
        competitionsEngine.modify_user_permissions_to_competition(user, competition_id)

    if update_status is not None:
        competition['status'] = int(competition_status)
        competitionsEngine.update_competition(competition_id, competition)

    if remove_climber is not None:
        competition['climbers'].pop(remove_climber)
        competitionsEngine.update_competition(competition['id'], competition)

    if competition_update_button is not None:
        competition_name = request.form.get('competition_name')
        competition_date = request.form.get('competition_date')
        competition_routes = request.form.get('competition_routes')
        competitionsEngine.update_competition_details(competition, competition_name, competition_date, competition_routes)

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


@skala_api_app.route('/journey', methods=['GET'])
@login_required
def journey_list():
    user = competitionsEngine.get_user_by_email(session['email'])

    journeys = journeys_engine._get_journey_sessions_by_user_id(user.get('id'))

    return json.dumps(journeys)


@skala_api_app.route('/journey/add', methods=['POST'])
@login_required
def journey_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    date = request.form.get('date')
    gym_id = request.form.get('gym_id')
    comp = {}
    gym = competitionsEngine.get_gym(gym_id)

    journey = journeys_engine.add_journey_session(user,gym_id, gym.get('routesid'), date)
    # journey_id = user.get('journey_id')

    journeys = journeys_engine._get_journey_sessions_by_user_id(user.get('id'))
    return render_template('skala-journey.html',
                           user=user,
                           journeys=journeys,
                           journey=journey,
                           reference_data=competitionsEngine.reference_data
                           )


@skala_api_app.route('/journey/<journey_id>', methods=['GET'])
@login_required
def journey_session(journey_id):
    journey = journeys_engine.get_journey_session(journey_id)

    return journey


@skala_api_app.route('/journey/<journey_id>/add', methods=['POST'])
@login_required
def journey_session_entry_add(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    route_finish_status = request.form.get('route_finish_status')
    route_id = request.form.get('route')
    notes = request.form.get('notes')

    comp = {}

    journey = journeys_engine.get_journey_session(journey_id)

    journey = journeys_engine.add_journey_session_entry(journey_id,route_id, route_finish_status, notes)
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
    journey = journeys_engine.get_journey_session(journey_id)

    testid = request.args.get('testid')
    if journey is None:
        return {}
    journeys_engine.remove_journey_session(journey_id, route_id)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return {}


@skala_api_app.route('/competition')
def getCompetitionDashboard():
    return competitionsEngine.getCompetitions()


@skala_api_app.route('/competition/<competition_id>')
def get_competition_by_id(competition_id):
    return competitionsEngine.getCompetition(competition_id)


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

    error_code=competitionsEngine.can_register(user, comp)
    climber = None

    if user is None and form_user is not None and (
            form_user.get('fname') is not None or form_user.get('gname') is not None):
        return "{'error_code':'User with this email is known and they should login and register themselves'}", 401

    if not error_code and firstname is not None and sex is not None and club is not None and email is not None:
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
            return redirect(url_for('skala_api_app.getCompetition', competitionId=competitionId))

        except ValueError:
            error_code = email+' is already registered!'

    ##   comp=None # this is to not show the list of climbers before registration

    #competitions = competitionsEngine.getCompetitions()
    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return comp


### USER


@skala_api_app.route('/user')
def get_user():
    climber = competitionsEngine.get_all_user_emails()
    return json.dumps(climber)


@skala_api_app.route('/user/email/<email>')
def get_user_by_email(email):

    climber = competitionsEngine.get_user_by_email(email)

    if climber is None:
        #return "{'error_code':'No such user'}", 400
        return {}

    return climber


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

    subheader_message = 'Update your details'

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




## RESULTS


@skala_api_app.route('/competition_results/<competitionId>')
#@login_required
def get_competition_results(competitionId):
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

    return rankings


#@skala_api_app.route('/competitionDashboard/<competitionId>/climber/<climberId>')
#@login_required
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



@skala_api_app.route('/migrategyms')
def migrategyms():
    gyms = competitionsEngine.get_gyms()

    nanterre = gyms["1"]
    nanterre['logoimg'] = 'logo-ESN-HD-copy-1030x1030.png'
    nanterre['homepage'] = 'https://www.esnanterre.com/'

    competitionsEngine.update_gym("1", "667", json.dumps(nanterre))
    return {}


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
def gyms_list():
    gyms = competitionsEngine.get_gyms()

    newgyms = []
    for gymid in gyms:
        newgyms.append(gyms.get(gymid))

    return json.dumps(newgyms)



@skala_api_app.route('/gym/<gymid>')
def gym_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    return gym


@skala_api_app.route('/gym/<gymid>/routes')
def routes_by_gym_id(gymid):
    gym = competitionsEngine.get_gym(gymid)

    routes = competitionsEngine.get_routes(gym.get('routesid'))
    return json.dumps(routes.get('routes'))


@skala_api_app.route('/gym/<gymid>/<routesid>')
def gym_by_id_route(gymid, routesid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(routesid)

    return routes






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
        return redirect(url_for("skala_api_app.fsgtlogin"))

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







@skala_api_app.route('/gym/add', methods=['POST'])
@login_required
def gyms_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    body = request.data
    bodyj = request.json
    files = request.files

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        random = str(uuid.uuid4().hex)
        imgfilename = random+file1.filename
        imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
        file1.save(imgpath)

    gymName = formdata['gymName'][0]
    numberOfRoutes = formdata['numberOfRoutes'][0]
    if numberOfRoutes is None or len(numberOfRoutes)==0:
        numberOfRoutes = 10  #default value of routes for a gym
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]

    gym_id = str(uuid.uuid4().hex)

    routes = competitionsEngine.generate_dummy_routes(int(numberOfRoutes))
    competitionsEngine.upsert_routes(routes['id'], gym_id, routes)
    gym = competitionsEngine.add_gym(user, gym_id, routes['id'], gymName, imgfilename, url, address, organization, [])

    return gym


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
        if len(file1.filename) > 0:
            random = str(uuid.uuid4().hex)
            imgfilename = random+file1.filename
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

    if delete is not None and gym['logo_img_id'] is not None and len(gym['logo_img_id']) > 8:
        competitionsEngine.delete_gym(gym_id)
        competitionsEngine.remove_user_permissions_to_gym(user, gym_id)
        os.remove(os.path.join(UPLOAD_FOLDER, gym['logo_img_id']))
        return redirect(url_for('skala_api_app.gyms'))

    if routesid is None or len(routesid)==0:
        routesid = gym['routesid']

    if len(permissioned_user)>2:
        newuser = competitionsEngine.get_user_by_email(permissioned_user)
        if newuser is not None:
            competitionsEngine.add_user_permissions_to_gym(newuser, gym_id)

    #gymid, routesid, name, added_by, logo_img_id, homepage, address, organization, routesA):
    gym_json = competitionsEngine.get_gym_json(gym_id, routesid, gymName, None, imgfilename, url, address, organization, None)
    gym.update((k, v) for k, v in gym_json.items() if v is not None)
    competitionsEngine.update_gym(gym_id, gym)

    return






@skala_api_app.route('/image/<img_id>')
def image_route(img_id):
    #bytes_io = competitionsEngine.get_img(img_id)
    #return send_file(bytes_io, mimetype='image/png')

    #return send_file(os.path.join(UPLOAD_FOLDER, img_id))
    return send_from_directory(UPLOAD_FOLDER, img_id)