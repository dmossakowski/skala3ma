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


def fetch_token():
    #log.info('fetch_token')
    logging.info ("fetching token... ")
    return session.get('token')


def update_token(name, token, refresh_token=None, access_token=None):
    #log.info('update_token')
    logging.info ("updating token... ")
    session['token'] = token
    return session['token']


googleAuth = oauth.register(
    name='google',
    client_id=FSGT_APP_ID,
    client_secret=FSGT_APP_SECRET,
    #consumer_key=SPOTIFY_APP_ID,
    #consumer_secret=SPOTIFY_APP_SECRET,
    # Change the scope to match whatever it us you need
    # list of scopes can be found in the url below
    access_token_params=None,
    #scope = 'playlist-read-private user-library-read	 user-top-read',
    base_url='https://accounts.spotify.com/',
    #request_token_url='https://accounts.spotify.com/api/token',
    access_token_url='https://accounts.spotify.com/api/token',
    refresh_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    fetch_token=fetch_token,
    update_token=update_token,
    client_kwargs = {
            'scope': 'user-library-read user-top-read playlist-read-private playlist-read-collaborative'
    #'scope': 'playlist-read-private  user-library-read  user-top-read'
    }
)




@app.route('/fsgtlogin/authorized')
def spotify_authorized():
    logging.info("spotify is calling /login/authorized ...")
    try:
        error = request.args.get('error')
        logging.info(str(request))

        if str(error) == 'access_denied':
            logging.info ("access is denied ",error)
            return render_template('index.html', subheader_message="Not authorized", library={}, **session)

        #acc = spotify.fetch_access_token(scope='user-library-read')
        resp = googleAuth.authorize_access_token()
        logging.info ("spotify calls us now " + str(resp))
        if resp is None:
            return 'Access denied: reason={0} error={1}'.format(
                request.args['error_reason'],
                request.args['error_description']
            )
        #if isinstance(resp, OAuthException):
        #    return 'Access denied: {0}'.format(resp.message)

        session['token'] = resp
        session['access_token'] = (resp['access_token'], '')
        session['refresh_token'] = (resp['refresh_token'], '')
        session['expires_at'] = resp['expires_at']
        session['expires_in'] = resp['expires_in']
        session['expires_at_localtime'] = int(datetime.datetime.now().timestamp()+int(resp['expires_in'])-1000)
        session.dataLoadingProgressMsg = ''

        #
        # me = spotify.get('/v1/me')
        #getPlaylists(session['oauth_token'], 'dmossakowski')

        global authenticated
        authenticated = True
            #print me.data



        if session.get("wants_url") is not None:
            return redirect(session["wants_url"])
        else:
            return redirect("/")

    except OAuthError as e:
        logging.info(" error in authentication ", traceback.format_exc())
        return render_template('index.html',
                               subheader_message="Authentication error "+str(traceback.format_exc()),
                               library={},
                               **session)




@fsgtapp.route('/login')
def login():
    logging.info ("doing login "+str(request.referrer)+" client_id "+str(SPOTIFY_APP_ID))

    callback = url_for('spotify_authorized', _external=True)

    #print(" request.referrer " + request.referrer)
    #print(" request.args.get('next') ="+request.args.get('next'))

    callback2 = url_for(
        'spotify_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    return spotify.authorize_redirect(callback)


@fsgtapp.route('/competitionDashboard')
#@login_required
def getCompetitionDashboard():

    username = request.args.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    comp = {}
    competitionId=None


    if name is not None and date is not None and gym is not None:

        competitionId = competitionsEngine.addCompetition(None, name, date, gym)
        comp = getCompetition(competitionId)
        return redirect(url_for('getCompetition', competitionId=competitionId))

    subheader_message='Create new competition '
    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                            **session)





@fsgtapp.route('/competitionDashboard/<competitionId>/register')
def addCompetitionClimber(competitionId):

    username = request.args.get('username')
    name = request.args.get('name')
    sex = request.args.get('sex')
    club = request.args.get('club')

    comp = competitionsEngine.getCompetition(competitionId)
    subheader_message = 'Please register for ' + comp['name'] + ' on ' + comp['date']

    climber=None


    if name is not None and sex is not None and club is not None:
        climber = competitionsEngine.addClimber(None, competitionId, name, club, sex)
        subheader_message = 'You have been registered! Thanks!'
    else:
        comp=None # this is to not show the list of climbers before registration

    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionClimber.html',
                           subheader_message=subheader_message,
                           competition=comp,
                           competitionId=competitionId,
                           climber=climber,
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
        competitionsEngine.recalculate(competitionId)
        competition = competitionsEngine.getCompetition(competitionId)

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

    return render_template("competitionDashboard.html", competitionId=competitionId, competition=competition,
                           subheader_message=subheader_message,
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
                           **session)




