#!/bin/sh
# to kill the server.py that is still running after Ctrl+C over my_run.sh
kill $(ps aux | grep "Python /Users/scorreia/devel/git/skala3ma/server.py" | grep -v grep | awk '{print $2}')