import sqlite3
import os


def initDB():
    """Connects to Message.db. Also handles creating/init any missing dir, db, or tables."""
    
    # Check root dir for KCBot_db. If it does not exist, create it.
    if "KCBot_db" not in os.listdir(os.path.abspath(os.sep)):
        os.mkdir(path=os.path.abspath(os.sep) + "KCBot_db")
        print("Directory KCBot_db was not found at root and was created")

    os.chdir(path=os.path.abspath(os.sep) + "KCBot_db") # Change cwd to KCBot_db
    con = sqlite3.connect(database="Message.db")    # Estabish a connection w/ database
    cur = con.cursor()                              # Create a Cursor
    print("Connected to Message.db")
    
    # Selects the "Message" table from db
    table = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = 'Message';")
    if table.fetchone() is None:  # Create the Messages table if it is empty
        cur.execute("CREATE TABLE Message(" +
                    "username VARCHAR(100)," +
                    "content VARCHAR(2000)," +
                    "sent DATETIME," +
                    "channelname VARCHAR(200)," +
                    "messageid BIGINT," +
                    "userid BIGINT," +
                    "channelid BIGINT" +
                    ");")
                    # TODO: Extra columns for stuff like replies
        print("Created 'Message' table in db")
    return (con, cur)


def getMostRecent(con, cur):
    """Returns the most recent row in connected database (determined by "sent" column).
    
    Args:
        con (Connection): Connection to database
        cur (Cursor): Cursor for connected database
    """
    
    try:    # try sorting messages by date sent and return the most recent one
        res = cur.execute("SELECT * FROM Message ORDER BY sent DESC;")
        return res.fetchone()
    except:
        print("ERROR - Failed to retrieve most recent message")
        # TODO: Error handling


def insertMsg(con, cur, newRows):
    """Inserts an array of data as several new rows into connected table.
    
    Args:
        con (Connection): Connection to database
        cur (Cursor): Cursor for connected database
        newRows (list[tuple]): List of tuples, each describing a new row to add to database
    """
    
    try:    # try inserting new rows, then commit
        cur.executemany("INSERT INTO Message VALUES (?, ?, ?, ?, ?, ?, ?);", newRows)
        con.commit()
    except: # rollback if this fails
        print("WARNING - Failed to write to database")
        con.rollback()