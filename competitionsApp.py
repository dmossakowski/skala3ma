

import json
import os
import io
import glob
import random
from datetime import datetime, date, time, timedelta
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
import competitionsEngine
import traceback
import csv

from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context

from sklearn.cluster import KMeans

from collections import defaultdict

from matplotlib.figure import Figure
from sklearn.preprocessing import MinMaxScaler

from functools import lru_cache
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

fsgtapp = Blueprint('fsgtapp', __name__)

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError



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
fsgtapp = Blueprint('fsgtapp', __name__)


fsgtapp.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# User session management setup
# https://flask-login.readthedocs.io/en/latest











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







@fsgtapp.route('/skala3ma-privacy')
def privacy():
    return render_template('skala3maprivacy.html')




@fsgtapp.route('/competitionDashboard')
#@login_required
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


    if name is not None and date is not None and gym is not None:

        competitionId = competitionsEngine.addCompetition(None, name, date, gym)
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




@fsgtapp.route('/newCompetition')
#@login_required
def newCompetition():

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



    subheader_message='Create new competition '
    competitions= competitionsEngine.getCompetitions()

    return render_template('newCompetition.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           reference_data=competitionsEngine.reference_data,
                            **session)






@fsgtapp.route('/competitionDashboard2')
#@login_required
def getCompetitionDashboard2():

    username = request.args.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    comp = {}
    competitionId=None


    if name is not None and date is not None and gym is not None:

        competitionId = competitionsEngine.addCompetition(None, name, date, gym)
        comp = competitionsEngine.getCompetition(competitionId)
        return redirect(url_for('getCompetition', competitionId=competitionId))

    subheader_message='Create new competition '
    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           reference_data=competitionsEngine.reference_data,
                            **session)


@fsgtapp.route('/competitionDashboard/<competitionId>/register')
def addCompetitionClimber(competitionId):

    useremail = session.get('email')

    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    comp = competitionsEngine.getCompetition(competitionId)
    subheader_message = 'Register for ' + comp['name'] + ' on ' + comp['date']

    user = competitionsEngine.get_user_by_email(useremail)
    climber=None

    if firstname is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.get_climber_by_email(email)
        name = firstname + " " + lastname

        try:
            climber = competitionsEngine.addClimber(None, competitionId, email, name, firstname, lastname, club, sex, category)
            competitionsEngine.user_registered_for_competition(climber['id'], name, email, climber['sex'],
                                                               climber['club'], climber['category'])
            comp = competitionsEngine.getCompetition(competitionId)
            competitionName = comp['name']
            subheader_message = 'You have been registered! Thanks!'
        except ValueError:
            subheader_message = email+' is already registered!'

    #else:
     ##   comp=None # this is to not show the list of climbers before registration

    #competitions = competitionsEngine.getCompetitions()
    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('competitionClimber.html',
                           subheader_message=subheader_message,
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




@fsgtapp.route('/competitionDashboard/<competitionId>')
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


    subheader_message = "Competition '" + competition['name'] + "' on "+competition['date']

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("competitionDashboard.html", competitionId=competitionId,
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

    subheader_message =   competition['name'] + "  -    "+competition['date']

    rankings = competitionsEngine.get_sorted_rankings(competition)



    return render_template("competitionResults.html", competitionId=competitionId,
                           competition=competition,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data,
                           rankings = rankings,
                           **session)


@fsgtapp.route('/competitionDashboard/<competitionId>/climber/<climberId>')
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
#@login_required
def competitionRoutesList(competitionId):
    #competitionId = request.args.get('competitionId')


    competition = competitionsEngine.getCompetition(competitionId)

    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')

    subheader_message = competition['name']+"   list "+competition['gym']

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
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)



# enter competition climbed routes for a climber and save them
@fsgtapp.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>')
#@login_required
def enterRoutesClimbed(competitionId, climberId):
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
            return render_template('competitionClimberList.html',
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

    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')

    #if routesid is None:
    #    routesid = '5600717d-2167-4c9b-a72c-8aaf297bf092'

    #routes = competitionsEngine._get_routes(routesid)
    routes = competitionsEngine.get_routes(routesid)
    routes = routes['routes']
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

    subheader_message = 'Murs'

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
                           subheader_message=subheader_message,
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
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)





def user_authenticated(id, username, email, picture):
    competitionsEngine.user_authenticated(id, username, email, picture)





@fsgtapp.route('/competitionDashboard/loadData')
def loadData():
    competitionsEngine.init()
    subheader_message='data loaded'
    return render_template("competitionDashboard.html", climberId=None,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data)


