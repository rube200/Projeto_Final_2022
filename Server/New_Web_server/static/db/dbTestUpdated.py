import os
import sqlite3
import datetime
import time
#from classes import User 


#con = sqlite3.connect('users.db')

#c = con.cursor()

#DOORBELLs1 = '1.1.1.1'+','+'2.3.2.3'
#DOORBELLs2 = '4.1.1.1'+','+'4.3.2.3'+','+'1.2.3.4'

#user1 = User('Johny', 'Nippleaction', DOORBELLs1)
#user2 = User('ligma', 'Ballz', DOORBELLs2)

#print(user1.DOORBELLs)

#c.execute("""CREATE TABLE users (
#        first_name text,
#        last_name text,
#        DOORBELL text
#        )""") #the triple " allows multiple line string


#c.execute("INSERT INTO users VALUES ('Mike', 'Oxlong', '1.1.1.1')")
#c.execute("INSERT INTO users VALUES ('Moe', 'Lester', '2.2.1.1')")


#c.execute("INSERT INTO users VALUES ('{}', '{}', '{}')".format(user1.firstName, user1.lastName, user1.DOORBELLs)) <- is not safe


#c.execute("INSERT INTO users VALUES (?, ?, ?)", (user1.firstName, user1.lastName, user1.DOORBELLs))

#c.execute("INSERT INTO users VALUES (:first, :last, :DOORBELLs)", {'first': user2.firstName, 'last': user2.lastName, 'DOORBELLs': user1.DOORBELLs})# can also do like this


#c.execute("SELECT * FROM users WHERE last_name = 'Nippleaction' OR last_name = 'Ballz'")

#c.execute("UPDATE users SET DOORBELLs = '1.2.1.2' where firs_name = 'Moe'")

#c.execute("SELECT * FROM users WHERE last_name = ? OR last_name = ?", ('Nippleaction','Ballz')) # if was just one would be ('Nippleaction',)

#print(c.fetchall())

#con.commit()

#con.close()


########



#in text type use YYYY-MM-DD HH:MM:SS.SSS for date and time

conn = sqlite3.connect('static/proj.db')

query = (''' CREATE TABLE IF NOT EXISTS USER
            (ID     INTAGER     PRIMARY KEY,
            NAME    TEXT        NOT NULL,
            PASSWORD    TEXT    NOT NULL,
            EMAIL   TEXT    NOT NULL
            ); ''')

conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS DOORBELL
            (ID     INTAGER     PRIMARY KEY,
            IP    TEXT        NOT NULL,
            NAME    TEXT    NOT NULL,
            USER_ID    INTAGER    NOT NULL,
            FOREIGN KEY(USER_ID) REFERENCES USER(ID)
            ); ''')

conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS PICTURE
            (ID     INTAGER     PRIMARY KEY,
            DATA    TEXT        NOT NULL,        
            DOORBELL_ID    INTAGER    NOT NULL,
            DATE    TEXT    NOT NULL,
            FOREIGN KEY(DOORBELL_ID) REFERENCES DOORBELL(ID)
            ); ''')
            
conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS VIDEO
            (ID     INTAGER     PRIMARY KEY,
            DATA    TEXT        NOT NULL,        
            DOORBELL_ID    INTAGER    NOT NULL,
            DATE    TEXT    NOT NULL,
            FOREIGN KEY(DOORBELL_ID) REFERENCES DOORBELL(ID)
            ); ''')

conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS ALERT
            (ID     INTAGER     PRIMARY KEY,
            MSG    TEXT,        
            USER_ID    INTAGER,
            DOORBELL_ID    TEXT,
            DATE    TEXT    NOT NULL,
            NEW     INTAGER     NOT NULL CHECK(NEW IN (0, 1)),
            FOREIGN KEY(USER_ID) REFERENCES USER(ID),
            FOREIGN KEY(DOORBELL_ID) REFERENCES DOORBELL(NAME)
            ); ''')

conn.execute(query)


#code to create dirs

#insert img
"""
c = conn.cursor()
with open('add.png', 'rb') as f:
    blob = f.read()
if not os.path.isdir("3"):
    os.mkdir("3")
with open('3/output.png','wb') as f:
    f.write(blob)
"""
#end of imp code
c = conn.cursor()
c.execute(''' INSERT INTO USER (ID, NAME, PASSWORD, EMAIL) VALUES(?, ?, ?, ?)''', (3, 'sup brah', '123', 'idk@wat.where'))
c.execute(''' INSERT INTO USER (ID, NAME, PASSWORD, EMAIL) VALUES(?, ?, ?, ?)''', (4, 'kek', 'w', 'idk@wat.where'))

c.execute(''' INSERT INTO DOORBELL (ID, IP, NAME, USER_ID) VALUES(?, ?, ?, ?)''', (1, "1.1.1.1", 'frontDoor', 3))
c.execute(''' INSERT INTO DOORBELL (ID, IP, NAME, USER_ID) VALUES(?, ?, ?, ?)''', (2, "1.1.1.2", 'backDoor', 3))

c.execute(''' INSERT INTO DOORBELL (ID, IP, NAME, USER_ID) VALUES(?, ?, ?, ?)''', (3, "1.1.2.1", 'frontDoor', 4))
c.execute(''' INSERT INTO DOORBELL (ID, IP, NAME, USER_ID) VALUES(?, ?, ?, ?)''', (4, "1.1.2.122", 'backDoor', 4))

c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (1, "/static/db/3/ronaldo.mp4", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (2, "/static/db/3/ronaldo.mp4", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (3, "/static/db/3/ronaldo.mp4", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (4, "/static/db/3/ronaldo.mp4", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (5, "/static/db/3/ronaldo.mp4", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (6, "/static/db/3/ronaldo.mp4", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (7, "/static/db/3/ronaldo.mp4", 4, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (8, "/static/db/3/ronaldo.mp4", 4, datetime.datetime.now()))

time.sleep(5.5)

c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (9, "/static/db/3/ronaldo.mp4", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (10, "/static/db/3/ronaldo.mp4", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (30, "/static/db/3/ronaldo.mp4", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (40, "/static/db/3/ronaldo.mp4", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (50, "/static/db/3/ronaldo.mp4", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (60, "/static/db/3/ronaldo.mp4", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (70, "/static/db/3/ronaldo.mp4", 4, datetime.datetime.now()))
c.execute(''' INSERT INTO VIDEO (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (80, "/static/db/3/ronaldo.mp4", 4, datetime.datetime.now()))



c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (1, "/static/db/3/output.png", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (2, "/static/db/3/output.png", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (3, "/static/db/3/output.png", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (4, "/static/db/3/output.png", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (5, "/static/db/3/output.png", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (6, "/static/db/3/output.png", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (7, "/static/db/3/output.png", 4, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (8, "/static/db/3/output.png", 4, datetime.datetime.now()))

time.sleep(5.5)

c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (9, "/static/db/3/output.png", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (10, "/static/db/3/output.png", 1, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (30, "/static/db/3/output.png", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (40, "/static/db/3/output.png", 2, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (50, "/static/db/3/output.png", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (60, "/static/db/3/output.png", 3, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (70, "/static/db/3/output.png", 4, datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, DOORBELL_ID,  DATE) VALUES(?, ?, ?, ?)''', (80, "/static/db/3/output.png", 4, datetime.datetime.now()))




c.execute(''' INSERT INTO ALERT (ID, MSG, USER_ID, DOORBELL_ID, DATE, NEW) VALUES(?, ?, ?, ?, ?, ?)''', (8, "alert 1", 3, 2, datetime.datetime.now(), 0))
c.execute(''' INSERT INTO ALERT (ID, MSG, USER_ID, DOORBELL_ID, DATE, NEW) VALUES(?, ?, ?, ?, ?, ?)''', (9, "alert 1", 4, 2, datetime.datetime.now(), 0))
c.execute(''' INSERT INTO ALERT (ID, MSG, USER_ID, DOORBELL_ID, DATE, NEW) VALUES(?, ?, ?, ?, ?, ?)''', (1, "alert 2", 3, 2, datetime.datetime.now(), 0))
c.execute(''' INSERT INTO ALERT (ID, MSG, USER_ID, DOORBELL_ID, DATE, NEW) VALUES(?, ?, ?, ?, ?, ?)''', (2, "alert 2", 4, 2, datetime.datetime.now(), 0))


#to retreive img

#m = c.execute("SELECT * FROM PICTURE")

#for x in m:
#    data = x[1] # x[0] is id, 1 is blob and 2 is user_id

#with open('output.png','wb') as f:
#    f.write(data)

m = c.execute("SELECT ID FROM USER WHERE NAME LIKE ? AND PASSWORD LIKE ?", ('sup brah', '123'))
m = [row[0] for row in c]
print('b4 m')


print(m)
print('after m')

conn.commit()
c.close()
conn.close()



#generate random string for img name
#def get_random_string(length):
    # Random string with the combination of lower and upper case
#    letters = string.ascii_letters
#    return ''.join(random.choice(letters) for i in range(length))