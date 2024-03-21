import sqlite3
import os
import re
import json
import discord as dc
# Kaycee bot requires the 'message_content' intent to be enabled.

def getConfig():
    """Reads config from file and returns a config dict"""
    config = {}
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
        f.close()
    # convert IDs to ints
    config['guildID'] = int(config['guildID'])
    config['botID'] = int(config['botID'])
    channelIDs = []
    for channel in config['channelIDs']:
        channelIDs.append(int(channel))
    config['channelIDs'] = channelIDs
    return config


def getNames():
    """Reads preferred names from names.json file.
    id/name pairs in names.json can be for channels, roles, or users.
    
    Returns:
        dict[str, str]: Dict of id/name pairs
    """
    print(os.getcwd())
    idMap = {}
    with open('names.json', 'r') as f:
        idMap = json.loads(f.read())
        f.close()
    return idMap


def initBot(client):
    """Sets up a bot client using config.json and connects it to your server so you can use it.
    
    Args:
        client (Client): Discord client connection object with the corresponding code & intents for the desired behavior of the bot.
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

    async def on_message(self, message):
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
                        reference)
                msgBatch.append(msg)
                count += 1
            print(f'({chan}) Saving {count} messages to db...')
            insertMsg(con, cur, msgBatch)
            print(f'({chan}) Done!')
        print('------')
        
        print(f'Cleaning up messages...')
        cleanAllData(con, cur)
        print('------')
        

# DATABASE FUNCTIONS

def initDB():
    """
    Connects to Message.db. Also handles creating/init any missing dir, db, or tables.
    
    Returns:
        tuple[Connection, Cursor]: The Connection and Cursor objects for the connected database.
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
                    "replyid BIGINT" +
                    ");")
        print("Created 'Message' table in db")  
    return (con, cur)


def getMostRecent(con, cur, channelid):
    """Returns the most recently sent messageid with a matching channelid in connected database.
    (Recency is determined by the datetime in the "sent" column)
    
    Args:
        con (Connection): Connection to database
        cur (Cursor): Cursor for connected database
        channelid (int): ID of the channel to get the most recent message from
    Returns:
        (int | None): messageid of most recently sent message found in db. None if no messages were found in that channel.
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


def insertMsg(con, cur, newRows):
    """Inserts an array of data as several new rows into connected table.
    
    Args:
        con (Connection): Connection to database
        cur (Cursor): Cursor for connected database
        newRows (list[tuple]): List of tuples, each describing a new row to add to database
    """
    
    try:    # try inserting new rows, then commit
        cur.executemany("INSERT INTO Message VALUES (?, ?, ?, ?, ?, ?, ?, ?);", newRows)
        con.commit()
    except: # rollback if this fails
        print("WARNING - Failed to write to database")
        con.rollback()





def cleanAllData(con, cur):
    """Handles cleaning & updating all message contents in db

    Args:
        con (Connection): Connection to database
        cur (Cursor): Cursor for connected database 
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
        #print(row)
        newContent = cleanMsg(row, names, config) # clean the contents
        if newContent == "":        # If the message has no content, delete it from the database.
            updCur.execute("DELETE FROM Message WHERE messageID = ?;", (row[0],))
            # TODO: for database integrity, maybe also delete any messages replying to this deleted message. Repeat until no messages are modified.
            delCount += 1
        elif newContent != row[6]:  # Otherwise, update it with the cleaned content if it has changed
            updCur.execute("UPDATE Message SET content = ? WHERE messageID = ?;", (newContent, row[0]))
            cleanCount += 1
    print(f"Cleaned and updated {cleanCount} messages in Message.db")
    print(f"Deleted {delCount} empty messages in Message.db")
    con.commit()
    updCur.close()  # close temporary cursor


def cleanMsg(msg, names, config):
    """Handles cleaning a message's contents by doing the following:
    - Deletes messages sent by KCBot or messages starting with "/kc"
    - Removes embedded links & images
    - Replaces user/channel mentions with names specified in names.json.
    - Removes all user/channel mentions not included in names.json.
    - Removes embedded custom discord emoji

    Args:
        row (tuple): Row of db containing message to clean
        users (dict[str, str]): Dict of id/name pairs from names.json

    Returns:
        str: Cleaned message content
    """
    
    msgContent = msg[6]
    sentBy = msg[3]
    
    # Immediately delete all content if the message was sent by KCBot or starts with "/kc"
    if re.match(r"/kc", msgContent) != None or sentBy == config["botID"]:
        return ""
    # Removing embedded links & images
    msgContent = re.sub(r"http\S+|www\S+|https\S+", "", msgContent, flags=re.MULTILINE)
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