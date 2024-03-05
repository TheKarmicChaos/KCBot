from lib import *
from bot import *

(con, cur) = initDB()
table = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'Message';")
print(cur.fetchone())

