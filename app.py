from gevent import monkey

monkey.patch_all()

log_level = 'debug'

print ('monkey patching done')
worker_class = 'gevent'



