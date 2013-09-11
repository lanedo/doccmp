import web
# DB = web.database(dbn='postgres', db='appname', user='username', pw='')
DB = web.database(dbn='sqlite', db='doccmp.db')
cache = False
