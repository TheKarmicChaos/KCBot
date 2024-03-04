import sqlite3
import os

def initDB():
    """_summary_
    Connects to Message.db. Also handles creating/initializing any missing directories, databases, or tables.
    Returns tuple (con, cur) containing the Connection & Cursor objects.
    """
    
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
        print("Created Message table in db")
    return (con, cur)


def insertMsg(con, cur, newMsg):
    """_summary_
    Inserts newMsg as a new row into connected table.
    """

# con.commit() # THIS COMMITS INSERTS TO DB, LEAVE COMMENTED FOR NOW
