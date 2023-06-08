#!/bin/bash

# Exit early on errors
set -eu

# Python buffers stdout. Without this, you won't see what you "print" in the Activity Logs
export PYTHONUNBUFFERED=true

# Install Python 3 virtual env
VIRTUALENV=.venv

# create certificate and key file:
# openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem

# mkdir userdata

#create venv
python -m venv $VIRTUALENV

if [ ! -d $VIRTUALENV ]; then
  #virtualenv -p python3 $VIRTUALENV
  source $VIRTUALENV/bin/activate
fi

# Install the requirements
$VIRTUALENV/bin/pip install -r requirements.txt

# Run a glorious Python 3 server
$VIRTUALENV/bin/python3 server.py


# create localhost certificats:
# openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem

# allow chrome to open self signed https localhost:
# chrome://flags/#allow-insecure-localhost


#deactivate


