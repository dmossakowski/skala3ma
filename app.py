from gevent import monkey

monkey.patch_all()

from server import init
import logging


log_level = 'debug'

print ('monkey patching done')
worker_class = 'gevent'


def post_fork(server, worker):
    print('Server has started. Running one time processing.')
 
    init()