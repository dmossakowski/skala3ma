from gevent import monkey
import gunicorn.app.base

from server import init
import logging


monkey.patch_all()

log_level = 'debug'

print ('monkey patching done')
worker_class = 'gevent'


def post_fork(server, worker):
    print('Server has started. Running one time processing.')
 
    init()