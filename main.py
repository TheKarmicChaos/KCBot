from lib import *
from bot import *

(con, cur) = initDB()
res = cur.execute("SELECT COUNT(*) FROM Message")
print(cur.fetchall())