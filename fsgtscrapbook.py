
import sqlite3 as lite
db = lite.connect('/Users/david/dev/additive-spotify-analyzer/userdata/db/competitions.sqlite')
cursor = db.cursor()



id = 'c1'
previd= 'c1'
username = 'user2'
email = 'email2'
picture = 'picture1'

from threading import RLock
sql_lock = RLock()


cursor.execute("INSERT  INTO climbers VALUES (?,?,?,?, ?,datetime('now') ) ",
                           [str(id), str(username), str(email),str(picture), 0])

sql_lock.acquire()
cursor.execute("update climbers set name=? , email=? ,  added_at=datetime('now')  where id = ? ", [str(username), str(email),str(previd)])
sql_lock.release()

cursor.execute("select * from climbers")

db.commit()
db.close()
