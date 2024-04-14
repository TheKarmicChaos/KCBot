import sqlite3
import os
import re
import json
import discord as dc
import datetime
# Kaycee bot requires the 'message_content' intent to be enabled.

def getConfig() -> dict[str, (str | int | list[int])]:
    """Reads config from file and returns a config dict"""
    config = {}
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
        f.close()
    # convert IDs to ints
    config['guildID'] = int(config['guildID'])
    config['botID'] = int(config['botID'])
    config['userToImpersonateID'] = int(config['userToImpersonateID'])
    channelIDs = []
    for channel in config['channelIDs']:
        channelIDs.append(int(channel))
    config['channelIDs'] = channelIDs
    return config


def getNames() -> dict[str, str]:
    """Reads preferred names from names.json file.
    id/name pairs in names.json can be for channels, roles, or users.
    
    Returns dict of id/name pairs.
    """
    idMap = {}
    with open('names.json', 'r') as f:
        idMap = json.loads(f.read())
        f.close()
    return idMap




def initBot(client : dc.Client):
    """Sets up a bot client using config.json and connects it to your server so you can use it.
    
    Args:
        client : Discord client connection object with the corresponding code & intents for the desired behavior of the bot.
    """
    
    config = getConfig()
    try:
        client.run(config["botToken"])
    except:
        print("Could not load config.json properly. Perhaps you forgot to replace the placeholders?")


class ChatClient(dc.Client):
    """Discord bot client for sending and responding to chat messages.
    When activated with initBot() it will respond to messages starting with "/kc"
    in the the channels specified in config.json.
    """
    config = getConfig()
    guildID = config["guildID"]
    channelIDs = config["channelIDs"]
    
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Guild: "{self.get_guild(self.guildID)}"')
        print('------')
        print(f'Chatbot enabled in the following channels:')
        for channel in self.channelIDs:
            print(self.get_channel(channel))
        print('------')

    async def on_message(self, message: dc.Message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return

        if message.content.startswith('/kc '):
            prompt = message.content[4:]
            (con, cur) = initDB()
            # TODO: Run the prompt through AI and send the result as a discord message.
            result = cur.execute(prompt)
            # Placeholder for when AI part of project is finished.
            await message.reply(result.fetchmany(10), mention_author=True)


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


class Message:
    def __init__(self, dbRow : list[str | int]) -> None:
        self.messageid = dbRow[0]
        self.channelid = dbRow[1]
        self.channelname = dbRow[2]
        self.userid = dbRow[3]
        self.username = dbRow[4]
        self.sent = dbRow[5]
        self.content = dbRow[6]
        self.replyid = dbRow[7]
        self.conversid = dbRow[8]
        self.isFirstInConvers = dbRow[9]
        
        
def getDateTime(message : Message) -> datetime.datetime:
    """Returns a valid datetime object for when the given message was sent.
    
    Args:
        `message` : A Message class object
    """
    message_date : datetime
    try:                # Try getting message datetime with ms
        message_date = datetime.datetime.strptime(message.sent, "%Y-%m-%d %H:%M:%S.%f%z")
    except ValueError:  # If that doesn't work, get message datetime wihtout ms
        message_date = datetime.datetime.strptime(message.sent, "%Y-%m-%d %H:%M:%S%z")
    return message_date


# DATABASE FUNCTIONS

def initDB() -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Connects to Message.db. Also handles creating/init any missing dir, db, or tables.
    
    Returns the Connection and Cursor objects for the connected database.
    """
    
    # Check for db directory. If it does not exist, create it.
    if "db" not in os.listdir():
        os.mkdir(path=os.getcwd() + os.sep + "db")
        print("Directory 'db' was not found and was created locally")

    os.chdir(path=os.getcwd() + os.sep + "db")      # Change cwd to db
    con = sqlite3.connect(database="Message.db")    # Estabish a connection w/ database
    cur = con.cursor()                              # Create a Cursor
    os.chdir(path=os.pardir)                        # Return cwd to parent dir for future operations
    print("Connected to Message.db")
    
    # Selects the "Message" table from db
    table = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'Message';")
    if table.fetchone() is None:  # Create the Message table if it is empty
        cur.execute("CREATE TABLE Message(" +
                    "messageid BIGINT," +
                    "channelid BIGINT," +
                    "channelname VARCHAR(200)," +
                    "userid BIGINT," +
                    "username VARCHAR(100)," +
                    "sent DATETIME," +
                    "content VARCHAR(2000)," +
                    "replyid BIGINT," +
                    "conversid BIGINT," +
                    "isFirstInConvers BOOLEAN);")
        print("Created 'Message' table in db")
    return (con, cur)


def getMostRecent(con : sqlite3.Connection, cur : sqlite3.Cursor, channelid : int) -> int | None:
    """Returns the most recently sent messageid with a matching channelid in connected database,
    or None if no messages were found in that channel. (Recency is determined by the datetime in the "sent" column)
    
    Args:
        `con` : Connection to database
        `cur` : Cursor for connected database
        `channelid` : ID of the channel to get the most recent message from
    """

    try:    # try sorting messages by date sent and return the most recent one
        result = cur.execute("SELECT messageid " +
                            "FROM Message " +
                            "WHERE channelid = ? " +
                            "ORDER BY sent DESC;",
                            (channelid,))
        return result.fetchone()[0]
    except:
        # If this fails, we may not have any messages for this channel in db, so return None to continue under this assumption.
        print("ERROR - Failed to retrieve most recent message for this channel.")
        return None


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


def cleanMsg(msgContent : str, sentBy : str, names : dict[str, str], config : dict[str, (str | int | list[int])], isTrainingData = False) -> str:
    """Handles cleaning a message's contents by removing embedded links/emojis, replacing IDs with names, etc.
    
    Returns cleaned message content as a string

    Args:
        `msgContent` : Content of message to clean
        `sentBy` : string of ID of user who sent this message
        `names` : dict of id/name pairs from names.json
        `config` : config dict from config.json
        `isTrainingData` = `False` : If set to True, messages starting with "/kc" and messages sent by the bot will return an empty string
    """
    
    # If this is training data, immediately delete all content if the message was sent by KCBot or starts with "/kc"
    if isTrainingData and (re.match(r"/kc", msgContent) != None or sentBy == config["botID"]):
        return ""
    # If this is not training data, delete "/kc" from the start of messages and change mentions of the botID to the userID they are attempting to mimic.
    # This WILL result in the bot believing it is that user. Messages sent by the real user are treated by the bot as if it sent those messages.
    elif not isTrainingData:
        msgContent = re.sub(str(config["botID"]), str(config["userToImpersonateID"]), msgContent)
        if re.match(r"/kc ", msgContent) != None:
            msgContent = msgContent[4:].strip()
    
    # Removing embedded links & images
    msgContent = re.sub(r"http\S+|www\S+|https\S+", "", msgContent)
    # Removing discord emoji. Unicode emojis are left unchanged.
    msgContent = re.sub(r"\<.+?:\d+\>", "", msgContent)
    
    # Replacing @ mentions & channel mentions with names specified in names.json
    mentions = re.findall(r"\<[#@].*?(\d+?)\>", msgContent)
    for id in mentions:
        if id in names: # If this user or channel mention has a specified name, replace it with the name
            msgContent = re.sub(r"\<[#@].*?" + id + r"\>", names[id], msgContent)
        else:           # Otherwise, entirely delete the mention
            msgContent = re.sub(r"\<[#@].*?" + id + r"\>", "", msgContent)
            
    # Cleaning up extra whitespace (keeping newlines)
    msgContent = re.sub(r"(?:(?!\n)\s)+", " ", msgContent)
    # Strip trailing & leading whitespace (including newlines)
    msgContent = msgContent.strip()
    
    return msgContent


def formatMsg(msgContent : str, sentBy : str, names : dict[str, str], config : dict[str, (str | int | list[int])], isTrainingData = False) -> str:
    """Formats a message into a simple string in the form of:
        "Name: Message Content"
    Example:
        "Tom: Where are my pants?"
    
    Returns the formatted message string

    Args:
        `msgContent` : Content of message to format
        `sentBy` : string of ID of user who sent this message
        `names` : dict of id/name pairs from names.json
        `config` : config dict from config.json
        `isTrainingData` = `False` : If False, messages sent by Kaycee use the name of userToImpersonateID.
         If True, messages sent by Kaycee use the name "Kaycee (Bot)"
    """
    if sentBy == config["botID"]:
        if isTrainingData:
            return f"Kaycee (Bot): {msgContent}"
        else:
            name = names[config["userToImpersonateID"]]
            return f"{name}: {msgContent}"
    else:
        return f"{names[str(sentBy)]}: {msgContent}"


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


def generateTrainingData(con : sqlite3.Connection, cur : sqlite3.Cursor) -> list[dict[str, str]]:
    """Creates and returns a list of prompt/input/output dicts to be used as training data.
    
    Args:
        `con` : Connection to database
        `cur` : Cursor for connected database
    """
    print("Creating training data dict with prompt/input/outputs")
    trainingOutput = []
    
    # Load both json files
    names = getNames()
    config = getConfig()
        
    # get a list of all get all conversations to iterate through.
    cur.execute("SELECT DISTINCT conversID FROM Message;")
    allConversIDs = cur.fetchall()
    
    name = getNames()[str(getConfig()["userToImpersonateID"])]
    prompt = f"You are {name} in a chat room with some friends. You chat unfiltered, and saying rude things, cracking jokes, and swearing are encouraged."

    for (conversID,) in allConversIDs:
        # fetch the entire conversation from db
        cur.execute("SELECT * FROM Message WHERE conversid = ? ORDER BY sent ASC;", (conversID,))
        # remember this convers as an iterable datatype (list of Message objects)
        convers = []
        for row in cur:
            convers.append(Message(row))
        # iterate over messages in this convers
        for index in range(len(convers)):
            msg : Message = convers[index]
            # skip this message if content is empty, or this is the first message in conversation, or it is not sent by the impersonated user.
            if msg.content == "" or msg.isFirstInConvers == 1 or msg.userid != config["userToImpersonateID"]:
                continue
            else:
                # get the previous 10 messages in this conversation
                recentMsgHistory : list[Message] = convers[max(0, index - 10):index]
                # if no previous message in conversation contained text, skip this message
                if all(pastMsg.content == "" for pastMsg in recentMsgHistory):
                    continue
                # convert the messages into formatted messages
                formattedMsgHistory = []
                for unformattedMsg in recentMsgHistory:
                    # Don't add empty messages to training data (these are usually images)
                    if unformattedMsg.content != "":
                        formattedMsgHistory.append(formatMsg(unformattedMsg.content, unformattedMsg.userid, names, config, True))
                # combine them into a single chat history string
                chatHistory = "\n".join(formattedMsgHistory)
                # add this to the trainingOutput list
                trainingOutput.append({
                    "instruction": prompt,
                    "input": chatHistory,
                    "output": formatMsg(msg.content, msg.userid, names, config, isTrainingData=True)
                })
    print(f"{len(trainingOutput)} sets of training data created from {len(allConversIDs)} conversations")
    return trainingOutput