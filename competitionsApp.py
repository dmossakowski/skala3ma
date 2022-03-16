

import json
import os
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
    name = request.args.get('name')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    comp = competitionsEngine.getCompetition(competitionId)
    subheader_message = 'Please register for ' + comp['name'] + ' on ' + comp['date']

    climber=None

    if name is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.get_climber_by_email(email)


        climber = competitionsEngine.addClimber(None, competitionId, email, name, club, sex, category)
        competitionsEngine.user_registered_for_competition(climber['id'], name, email, climber['sex'],
                                                           climber['club'], climber['category'])
        comp = competitionsEngine.getCompetition(competitionId)

        subheader_message = 'You have been registered! Thanks!'
    else:
        comp=None # this is to not show the list of climbers before registration

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
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)




@fsgtapp.route('/climber')
def update_climber():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No competition found",
                               **session)

    climber = competitionsEngine.get_climber_by_email(session.get('email'))

    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    subheader_message = 'Update your details'

    if fullname is not None and sex is not None and club is not None and email is not None:
        climber = competitionsEngine.user_self_update(climber, fullname, nick, sex, club, category)
        subheader_message = 'Your details were saved'
    else:
        iemail = session.get('email')
        comp = None # this is to not show the list of climbers before registration

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


