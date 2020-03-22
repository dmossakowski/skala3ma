#!/usr/bin/env python
# -*- coding: utf-8 -*-

#       _                              
#      | |                             
#    __| |_ __ ___  __ _ _ __ ___  ___ 
#   / _` | '__/ _ \/ _` | '_ ` _ \/ __|
#  | (_| | | |  __/ (_| | | | | | \__ \
#   \__,_|_|  \___|\__,_|_| |_| |_|___/ .
#
# A 'Fog Creek'–inspired demo by Kenneth Reitz™

import os
import spotipy
import spotipy.oauth2 as oauth2
import json
import spotipy.util as util
from flask import Flask, request, render_template, jsonify


# Support for gomix's 'front-end' and 'back-end' UI.
app = Flask(__name__, static_folder='public', template_folder='views')

# Set the app secret key from the secret environment variables.
app.secret = os.environ.get('SECRET')

# Dream database. Store dreams in memory for now. 
DREAMS = ['Python. Python, everywhere.']


@app.after_request
def apply_kr_hello(response):
    """Adds some headers to all responses."""
  
    # Made by Kenneth Reitz. 
    if 'MADE_BY' in os.environ:
        response.headers["X-Was-Here"] = os.environ.get('MADE_BY')
    
    # Powered by Flask. 
    response.headers["X-Powered-By"] = os.environ.get('POWERED_BY')
    return response


@app.route('/')
def homepage():
    """Displays the homepage."""
    return render_template('index.html')

@app.route('/artist')
def artistpage():
    """Displays the homepage."""
    return render_template('artist.html')


@app.route('/dreams', methods=['GET', 'POST'])
def dreams():
    """Simple API endpoint for dreams. 
    In memory, ephemeral, like real dreams.
    """
    dreamsize = DREAMS.__len__()
    DREAMS.append("request received "+str(dreamsize))
    localreq = request

    print "test "+str(dreamsize)
    # Add a dream to the in-memory database, if given. 
    if 'dream' in request.args:
        DREAMS.append(request.args['dream'])
        print "adding someting"
        usePersonalPassword()

    print "TEST 2"
    #results = useClientSecret('death')
    #jsonresults = json.dumps(results, ensure_ascii=False)
    #print 'updated'
    #print jsonresults

    # Return the list of remembered dreams. 
    return jsonify(DREAMS)
    #return jsonresults


@app.route('/callback/')
def spotifycallback():
    print 'receivedcallback'
    return render_template('artist.html')


def useClientSecret(artist):
    client_id='47821343906643e3a7a156c5a3376c6d'
    client_secret='73e4faa12b224532ac22e57b39141435'

    print 'searching...'
    credentials = oauth2.SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret)

    token = credentials.get_access_token()
    spotify = spotipy.Spotify(auth=token)

    print 'searching'
    results = spotify.search(q='artist:'+artist, type='artist')

    return results


def usePersonalPassword():
    your_username='dmossakowski'
    scope='playlist-read-private'
    client_id='47821343906643e3a7a156c5a3376c6d'
    client_secret = '73e4faa12b224532ac22e57b39141435'
    #redirect_uri='https://beta.developer.spotify.com/dashboard/applications/47821343906643e3a7a156c5a3376c6d'
    redirect_uri = 'http://localhost:5000/callback2/'


    token = util.prompt_for_user_token(
        username=your_username,
        scope=scope,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri)

    if token:
        sp = spotipy.Spotify(auth=token)
        results = sp.user_playlist(your_username)
        tracks = results['tracks']
        which = 1
        while tracks:
            for item in tracks['items']:
                track = item['track']
                print(which, track['name'], ' --', track['artists'][0]['name'])
                which += 1
            tracks = sp.next(tracks)

    else:
        print("Can't get token for", your_username)

    print 'received token '


  
if __name__ == '__main__':
    app.run()