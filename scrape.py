from lib import *

class ScrapeClient(dc.Client):
    """Discord bot client for scraping messages.
    When activated with initBot() it will automatically scrape the channels specified in config.json.
    """
    config = getConfig()
    names = getNames()
    guildID = config["guildID"]
    channelIDs = config["channelIDs"]
    
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Guild: "{self.get_guild(self.guildID)}"')
        print('------')
        
        print('Connecting to database...')
        (con, cur) = initDB()
        print('Channels to scrape:')
        for channel in self.channelIDs:
            print(f'\t{self.get_channel(channel)}')
        print('------')
        
        for channel in self.channelIDs:
            chan = self.get_channel(channel)
            print(f'({chan}) Fetching most recent msg in db...')
            # Fetch most recent message in db for this channel
            mostRecentMsg = getMostRecent(con, cur, channel)
            if mostRecentMsg != None:
                mostRecentMsg = await chan.fetch_message(mostRecentMsg)
            msgBatch = []
            count = 0
            print(f'({chan}) Scraping message history (this may take a while)...')
            async for message in chan.history(limit=10000, after=mostRecentMsg, oldest_first=True):
                # check if this message references another message.
                reference = None
                try:
                    reference = message.reference.message_id
                except:
                    reference = None
                msg = (message.id,
                        message.channel.id,
                        message.channel.name,
                        message.author.id,
                        message.author.name,
                        str(message.created_at),
                        message.content,
                        reference,
                        -1, # conversid of -1 means we have not yet assigned this message to a conversation
                        1)
                msgBatch.append(msg)
                count += 1
            print(f'({chan}) Saving {count} messages to db...')
            try:    # try inserting new rows, then commit
                cur.executemany("INSERT INTO Message (messageid, channelid, channelname, userid, username, sent, content, replyid, conversid, isFirstInConvers) " +
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", msgBatch)
                con.commit()
            except: # rollback if this fails
                print("WARNING - Failed to write to database")
                con.rollback()
            print(f'({chan}) Done!')
        print('------')
        
        print(f'Cleaning up messages...')
        cleanAllData(con, cur)
        print('------')
        
        print(f'Generating conversations...')
        generateConversations(con, cur)
        print('------')
        cur.close()
        con.close()


# ----- Helper functions for ScrapeClient ----- 

def cleanAllData(con : sqlite3.Connection, cur : sqlite3.Cursor):
    """Handles cleaning & updating all message contents in db

    Args:
        `con` : Connection to database
        `cur` : Cursor for connected database
    """
    # Create a second cursor temporarily so we can update as we iterate over the first cursor.
    # This saves us from having to load the entire database into memory at once.
    updCur = con.cursor()
    
    # Load both json files
    names = getNames()
    config = getConfig()
    
    cleanCount = 0
    delCount = 0
    cur.execute("SELECT * FROM Message ORDER BY sent ASC;")
    for row in cur:     # for each message in db...
        msg = Message(row)
        newContent = cleanMsg(msg.content, msg.userid, names, config, isTrainingData = True) # clean the contents
        if newContent == "":        # If the message has no content, delete it from the database. (current version keeps empty messages for testing)
            updCur.execute("UPDATE Message SET content = ? WHERE messageID = ?;", (newContent, msg.messageid))
            #updCur.execute("DELETE FROM Message WHERE messageID = ?;", (row[0],))
            delCount += 1
        elif newContent != msg.content:  # Otherwise, update it with the cleaned content if it has changed
            updCur.execute("UPDATE Message SET content = ? WHERE messageID = ?;", (newContent, msg.messageid))
            cleanCount += 1
    print(f"Cleaned and updated {cleanCount} messages in Message.db")
    print(f"There are {delCount} empty messages in Message.db")
    con.commit()
    updCur.close()  # close temporary cursor



def generateConversations(con : sqlite3.Connection, cur : sqlite3.Cursor):
    """Handles assigning conversids to each message in db that is not currently in a conversation.
    Messages are in the same conversation if they are in the same channel and are sent less than 8 hours apart (or are replying to a message).

    Args:
        `con` : Connection to database
        `cur` : Cursor for connected database
    """
    # Create a second cursor temporarily so we can update as we iterate over the first cursor.
    # This saves us from having to load the entire database into memory at once.
    updCur = con.cursor()
    
    # Load both json files
    names = getNames()
    config = getConfig()
    
    # We first need to know the highest ID used for an existing Conversation, so we don't re-use the same ID for a new one
    cur.execute("SELECT conversid " +
                "FROM Message " +
                "ORDER BY conversid DESC;")
    biggestConversID = cur.fetchone()[0]
    
    # We want to iterate through messages in each channel separately, since a conversation will never span multiple channels.
    for channelID in config["channelIDs"]:
        cur.execute("SELECT * " +
                    "FROM Message " +
                    "WHERE channelid = ? " +
                    "ORDER BY sent ASC;",
                    (channelID,))
        sortedMsgCount = 0              # Keeps track of how many messages have been successfully sorted into a conversation
        newConversCount = 0             # Keeps track of how many new conversations have been made
        
        prevMsg : Message = None                # Keeps track of the previous message
        prevMsgFromOtherUser : Message = None   # Keeps track of the previous message sent by a different user
        prevMsgConversID : int = None           # Keeps track of the conversid of prevMsg. Must be tracked separately since we don't commit changes until the end.
        
        # for each message in this channel, starting w/ the oldest...
        for row in cur:
            msg = Message(row)
            # If this message has already been assigned to a conversation, skip it.
            if msg.conversid != -1:
                prevMsg = msg
                prevMsgFromOtherUser = msg
                continue
            # If this is the first message in this channel, make a new conversID for it.
            elif prevMsg == None:
                biggestConversID += 1
                updCur.execute("UPDATE Message SET conversid = ?, isFirstInConvers = 1 WHERE messageid = ?;", (biggestConversID, msg.messageid))
                prevMsg = msg
                prevMsgFromOtherUser = msg
                prevMsgConversID = biggestConversID
                sortedMsgCount += 1
                newConversCount += 1
            else:
                # If the previous message is sent by a different user than the current message, update prevMsgFromOtherUser.
                if msg.userid != prevMsg.userid:
                    prevMsgFromOtherUser = prevMsg
                
                # If the last message from another user was more than 8 hours ago (and this message isn't a reply), make a new conversation ID for it.
                if (msg.replyid == None) & (getDateTime(prevMsgFromOtherUser) < (getDateTime(msg) - datetime.timedelta(hours=8))):
                    biggestConversID += 1
                    updCur.execute("UPDATE Message SET conversid = ?, isFirstInConvers = 1 WHERE messageid = ?;", (biggestConversID, msg.messageid))
                    prevMsg = msg
                    prevMsgConversID = biggestConversID
                    prevMsgFromOtherUser = msg
                    sortedMsgCount += 1
                    newConversCount += 1
                # If it is a reply message, add it to the same conversation as the message it replied to.
                elif (msg.replyid != None):
                    updCur.execute("SELECT conversid FROM Message WHERE messageid = ?;", (msg.replyid,))
                    conversID = updCur.fetchone()[0]
                    updCur.execute("UPDATE Message SET conversid = ?, isFirstInConvers = 0 WHERE messageid = ?;", (conversID, msg.messageid))
                    prevMsg = msg
                    prevMsgConversID = conversID
                    sortedMsgCount += 1
                # Otherwise, add it to the same conversation as the previous message.
                else:
                    updCur.execute("UPDATE Message SET conversid = ?, isFirstInConvers = 0 WHERE messageid = ?;", (prevMsgConversID, msg.messageid))
                    prevMsg = msg
                    sortedMsgCount += 1
        print(f"({names[str(channelID)]}) Sorted {sortedMsgCount} messages into {(newConversCount)} conversations in Message.db")
    con.commit()
    updCur.close()  # close temporary cursor



# Code for running scrape bot
def runScrapeBot():
    intents = dc.Intents.default()
    intents.message_content = True

    client = ScrapeClient(intents=intents)
    initBot(client)

runScrapeBot()