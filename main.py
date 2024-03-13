from lib import *
from bot import *

# temp test code for running a bot
intents = dc.Intents.default()
intents.message_content = True

client = ChatClient(intents=intents)
initBot(client)

# temp test code for executing SQL queries
(con, cur) = initDB()
res = cur.execute("SELECT COUNT(*) FROM Message")
print(cur.fetchall())