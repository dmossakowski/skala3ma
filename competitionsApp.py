import json
import os
import io
import glob
import random
from datetime import datetime, date, time, timedelta
import competitionsEngine
import csv
from functools import wraps

from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context, g

import logging
from dotenv import load_dotenv

from flask import Blueprint
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

#fsgtapp = Blueprint('fsgtapp', __name__)

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

languages = {}

load_dotenv()

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
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

fsgtapp = Blueprint('fsgtapp', __name__)

fsgtapp.debug = True
fsgtapp.secret_key = 'development'
oauth = OAuth(fsgtapp)

genres = {"test": "1"}
authenticated = False

comps = {}
climbers = {}

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





fsgtapp.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# User session management setup
# https://flask-login.readthedocs.io/en/latest

@fsgtapp.before_request
def x(*args, **kwargs):
    if not session.get('language'):
        #kk = competitionsEngine.supported_languages.keys()
        session['language'] = request.accept_languages.best_match(competitionsEngine.supported_languages.keys())
        print ("setting language to "+str(request.accept_languages)+" ->"+str(session['language']))
        ##return redirect('/en' + request.full_path)


@fsgtapp.route('/language/<language>')
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
            now = int(datetime.now().timestamp())
            #expiresAt = session['expires_at']
            expiresAtLocaltime = session['expires_at_localtime']

            if expiresAtLocaltime < now:
                session["wants_url"] = request.url
                if session['authsource'] == 'facebook':
                    return redirect(url_for("facebook"))
                if session['authsource'] == 'google':
                    return redirect(url_for("googleauth"))

                #return redirect(url_for("fsgtapp.fsgtlogin"))
            else:
                return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("fsgtapp.fsgtlogin"))
    return decorated_function



def admin_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and session.get('name') == 'David Mossakowski':
            now = int(datetime.now().timestamp())
            #expiresAt = session['expires_at']
            expiresAtLocaltime = session['expires_at_localtime']
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("fsgtapp.fsgtlogin"))
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
            return redirect(url_for("fsgtapp.fsgtlogin"))
    return decorated_function


@fsgtapp.route("/aa")
def index():
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





@fsgtapp.route('/competitionRawAdmin', methods=['GET'])
@login_required
def fsgtadminget():
    edittype = request.args.get('edittype')
    id = request.args.get('id')
    action = request.args.get('action')
    jsondata = request.args.get('jsondata')
    jsonobject = None

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@fsgtapp.route('/competitionRawAdmin', methods=['POST'])
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
            competitionsEngine.update_competition(jsonobject['id'],jsonobject)
        if jsonobject is not None  and action == 'delete':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.delete_competition(jsonobject['id'])
        if id is not None and action == 'find':
            jsonobject = competitionsEngine.getCompetition(id)
        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_competition_ids()

    elif edittype == 'gym':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.update_gym(jsonobject['id'],jsonobject)

        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_gym(id)

    elif edittype == 'routes':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.upsert_routes(id, jsonobject)

        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_routes(id)

    else :
        jsonobject = {"error": "choose edit type" }

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)





@fsgtapp.route('/competition_admin/<competition_id>', methods=['GET'])
@login_required
def competition_admin_get(competition_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competition_id)

    user_list = competitionsEngine.get_all_user_emails()
    if user is None or competition is None or not competitionsEngine.can_edit_competition(user,competition):
        session["wants_url"] = request.url
        return redirect(url_for('fsgtapp.getCompetition', competitionId=competition['id']))

    return render_template('competitionAdmin.html',
                           user=user,
                           competition=competition,
                           user_list=user_list,
                           competitionId=competition_id,
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@fsgtapp.route('/competition_admin/<competition_id>', methods=['POST'])
@login_required
def competition_admin_post(competition_id):
    remove_climber = request.form.get('remove_climber')
    update_status = request.form.get('update_status')
    permission_user = request.form.get('permission_user')

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
        return redirect(url_for("fsgtapp.fsgtlogin"))

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

    user_list = competitionsEngine.get_all_user_emails()

    return render_template('competitionAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           user=user,
                           competition=competition,
                           user_list=user_list,
                           competitionId=competition_id,

                           reference_data=competitionsEngine.reference_data,
                           id=id)








@fsgtapp.route('/fsgtadmin/<edittype>')
def fsgtadminedit(edittype):
    j = request.args.get('jsondata')

    if edittype == 'user' and j['email'] is not None:
        competitionsEngine.upsert_user(j)


    return render_template('competitionRawAdmin.html',
                           reference_data=competitionsEngine.reference_data)



@fsgtapp.route('/fsgtlogin')
def fsgtlogin():
    return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data
                           )


@fsgtapp.route('/skala3ma-privacy')
def privacy():
    return render_template('skala3maprivacy.html')



@fsgtapp.route('/main')
def main():
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


@fsgtapp.route('/competitionDashboard')
@login_required
def getCompetitionDashboard():

    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    print(username)

    #username = request.args.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    comp = {}
    competitionId=None

    user = competitionsEngine.get_user_by_email(session['email'])
    subheader_message = request.accept_languages

    langs = competitionsEngine.reference_data['languages']

    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           langpack=languages['en_US'],
                            **session
                           )



@fsgtapp.route('/newCompetition', methods=['GET'])
@login_required
def newCompetition():

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



    #competitions= competitionsEngine.getCompetitions()

    return render_template('newCompetition.html',
                           competitionName=None,
                           session=session,
                           reference_data=competitionsEngine.reference_data,
                            **session)


@fsgtapp.route('/newCompetition', methods=['POST'])
@login_required
def create_new_competition():
    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    #print(username)

    #username = request.args.get('username')
    name = request.form.get('name')
    date = request.form.get('date')
    gym = request.form.get('gym')
    comp = {}
    competitionId=None

    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is None or not competitionsEngine.can_create_competition(user):
        return redirect(url_for('fsgtapp.fsgtlogin', competitionId=competitionId))

    if name is not None and date is not None and gym is not None:
        competitionId = competitionsEngine.addCompetition(None, name, date, gym)
        competitionsEngine.modify_user_permissions_to_competition(user, competitionId, "ADD")
        comp = getCompetition(competitionId)
        return redirect(url_for('fsgtapp.getCompetition', competitionId=competitionId))

    subheader_message='Welcome '
    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           reference_data=competitionsEngine.reference_data,
                            **session)


@fsgtapp.route('/addCompetitionPermission', methods=['GET'])
@login_required
def add_competition_permission():
    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    #print(username)

    #username = request.args.get('username')
    name = request.form.get('name')
    date = request.form.get('date')
    gym = request.form.get('gym')
    comp = {}
    competitionId=None

    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is None or not competitionsEngine.can_create_competition(user):
        return redirect(url_for('fsgtapp.fsgtlogin', competitionId=competitionId))

    if name is not None and date is not None and gym is not None:
        competitionId = competitionsEngine.addCompetition(None, name, date, gym)
        competitionsEngine.modify_user_permissions_to_competition(user, competitionId, "ADD")
        comp = getCompetition(competitionId)
        return redirect(url_for('fsgtapp.getCompetition', competitionId=competitionId))

    subheader_message='Welcome '
    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           reference_data=competitionsEngine.reference_data,
                            **session)




@fsgtapp.route('/competitionDashboard/<competitionId>/register')
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
    form_user = competitionsEngine.get_user_by_email(email)

    error_code=competitionsEngine.can_register(user, comp)
    climber = None

    if user is not None and form_user is not None and (
            form_user.get('fname') is not None and form_user.get('gname') is not None):
        error_code = "User with this email is known and they should login and register themselves"

    if not error_code and firstname is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.get_climber_by_email(email)
        name = firstname + " " + lastname

        try:
            if club not in competitionsEngine.clubs.values():
                club = otherclub
            climber = competitionsEngine.addClimber(None, competitionId, email, name, firstname, lastname, club, sex, category)
            competitionsEngine.user_registered_for_competition(climber['id'], name, firstname, lastname, email, climber['sex'],
                                                               climber['club'], climber['category'])
            comp = competitionsEngine.getCompetition(competitionId)
            competitionName = comp['name']
            #subheader_message = 'You have been registered! Thanks!'
            return redirect(url_for('fsgtapp.getCompetition', competitionId=competitionId))

        except ValueError:
            error_code = email+' is already registered!'

    ##   comp=None # this is to not show the list of climbers before registration

    #competitions = competitionsEngine.getCompetitions()
    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('competitionClimber.html',
                           error_code=error_code,
                           competition=comp,
                           competitionId=competitionId,
                           climber=climber,
                           user = user,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)


@fsgtapp.route('/user')
def get_user():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               reference_data=competitionsEngine.reference_data,
                               subheader_message="No user found",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))

    subheader_message = 'Update your details'

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


@fsgtapp.route('/updateuser')
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




@fsgtapp.route('/competitionDetails/<competitionId>')
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



@fsgtapp.route('/competitionResults/<competitionId>')
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



    return render_template("competitionResults.html", competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           rankings = rankings,
                           **session)


#@fsgtapp.route('/competitionDashboard/<competitionId>/climber/<climberId>')
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




@fsgtapp.route('/competitionResults/<competitionId>/download')
def downloadCompetitionCsv(competitionId):

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



@fsgtapp.route('/competitionRoutesEntry/<competitionId>')
@login_required
def competitionRoutesList(competitionId):
    #competitionId = request.args.get('competitionId')

    user = competitionsEngine.get_user_by_email(session['email'])

    competition = competitionsEngine.getCompetition(competitionId)

    error_code = ""
    if not competitionsEngine.can_update_routes(user,competition):
        error_code = "5314 - updating routes is not permitted"

    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')


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
@fsgtapp.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['GET'])
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
        return redirect(url_for('fsgtapp.competitionRoutesList', competitionId=competitionId))


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


@fsgtapp.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['POST'])
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



@fsgtapp.route('/migrategyms')
def migrategyms():
    gyms = competitionsEngine.get_gyms()

    nanterre = gyms["1"]
    nanterre['logoimg'] = 'logo-ESN-HD-copy-1030x1030.png'
    nanterre['homepage'] = 'https://www.esnanterre.com/'

    competitionsEngine.update_gym("1", "667", json.dumps(nanterre))
    return redirect(url_for('fsgtapp.gyms'))


@fsgtapp.route('/gyms')
def gyms():
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')


    gyms = competitionsEngine.get_gyms()

    if fullname is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.user_self_update(climber, fullname, nick, sex, club, category)
        subheader_message = 'Your details were saved'
    else:
        iemail = session.get('email')
        comp = None # this is to not show the list of climbers before registration

    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('gyms.html',
                           competitionId=None,
                           gyms=gyms,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)


@fsgtapp.route('/gyms/<gymid>')
def gym_by_id(gymid):
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')


    gym = competitionsEngine.get_gym(gymid)

    routes = competitionsEngine.get_routes(gym['routesid'])

    subheader_message = '' + str(gym['name'])

    #gyms = competitionsEngine.get_gyms()

    if fullname is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.user_self_update(climber, fullname, nick, sex, club, category)
        subheader_message = 'Your details were saved'
    else:
        iemail = session.get('email')
        comp = None # this is to not show the list of climbers before registration

    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('gyms.html',
                           subheader_message=subheader_message,
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)


@fsgtapp.route('/gyms/<gymid>/<routesid>')
def gym_by_id_route(gymid, routesid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(routesid)

    return render_template('gyms.html',
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                            **session)



@fsgtapp.route('/gyms/<gymid>/data')
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


@fsgtapp.route('/gyms/<gymid>/edit', methods=['GET'])
def gym_edit(gymid):
    gym = competitionsEngine.get_gym(gymid)

    routes = competitionsEngine.get_routes(gym['routesid'])

    return render_template('gymedit.html',
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@fsgtapp.route('/gyms/<gymid>/edit', methods=['POST'])
@login_required
def gym_save(gymid):

    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    body = request.data
    bodyj = request.json

    lineid = formdata['lineid']
    routeline = formdata['routeline']
    color1 = formdata['color1']
    color2 = formdata['color2']
    routegrade = formdata['routegrade']
    routename = formdata['routename']
    openedby = formdata['openedby']
    opendate = formdata['opendate']
    notes = formdata['notes']

    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return redirect(url_for("fsgtapp.fsgtlogin"))

    routes = []
    for i, routeline1 in enumerate(routeline):
        print (i)
        oneline = competitionsEngine._get_route_dict(lineid[i],gym['id'],i,routeline[i],color1[i],color2[i],routegrade[i],
                                           routename[i],openedby[i],opendate[i],notes[i])
        routes.append(oneline)

    gym['routes'] = []

    competitionsEngine.update_gym(gym['id'],gym['routesid'],gym)

    competitionsEngine._update_routes(gym['routesid'],routes)

    gym = competitionsEngine.get_gym(gym['id'])
    gym['routes'] = []
    routes = competitionsEngine.get_routes(gym['routesid'])

    return render_template('gymedit.html',
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@fsgtapp.route('/gyms/<gymid>/edittest')
def edit_test(gymid):
    return render_template('tabletest.html',
                           reference_data=competitionsEngine.reference_data)


def user_authenticated(id, username, email, picture):
    competitionsEngine.user_authenticated(id, username, email, picture)





@fsgtapp.route('/competitionDashboard/loadData')
def loadData():
    competitionsEngine.init()
    subheader_message='data loaded'
    return render_template("competitionDashboard.html", climberId=None,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data)


