from lib import initDB, insertMsg

# con = Connection Obj
# cur = Cursor Obj
(con, cur) = initDB()
table = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'Message';")
print(cur.fetchone())

