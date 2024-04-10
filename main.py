from lib import *

# temp test code for running chat bot
def runChatBot():
    intents = dc.Intents.default()
    intents.message_content = True

    client = ChatClient(intents=intents)
    initBot(client)

# temp test code for running scrape bot
def runScrapeBot():
    intents = dc.Intents.default()
    intents.message_content = True

    client = ScrapeClient(intents=intents)
    initBot(client)

# temp test code for executing SQL queries
def querySQL(query):
    (con, cur) = initDB()
    res = cur.execute(query)
    for row in cur:
        print(cur.fetchone())

runScrapeBot()