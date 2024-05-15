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
                    "output": msg.content,
                })
    print(f"{len(trainingOutput)} sets of training data created from {len(allConversIDs)} conversations")
    return trainingOutput