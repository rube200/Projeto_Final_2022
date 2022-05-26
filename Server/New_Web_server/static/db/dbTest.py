import os
import sqlite3
import datetime
#from classes import User 


#con = sqlite3.connect('users.db')

#c = con.cursor()

#esps1 = '1.1.1.1'+','+'2.3.2.3'
#esps2 = '4.1.1.1'+','+'4.3.2.3'+','+'1.2.3.4'

#user1 = User('Johny', 'Nippleaction', esps1)
#user2 = User('ligma', 'Ballz', esps2)

#print(user1.esps)

#c.execute("""CREATE TABLE users (
#        first_name text,
#        last_name text,
#        esp text
#        )""") #the triple " allows multiple line string


#c.execute("INSERT INTO users VALUES ('Mike', 'Oxlong', '1.1.1.1')")
#c.execute("INSERT INTO users VALUES ('Moe', 'Lester', '2.2.1.1')")


#c.execute("INSERT INTO users VALUES ('{}', '{}', '{}')".format(user1.firstName, user1.lastName, user1.esps)) <- is not safe


#c.execute("INSERT INTO users VALUES (?, ?, ?)", (user1.firstName, user1.lastName, user1.esps))

#c.execute("INSERT INTO users VALUES (:first, :last, :esps)", {'first': user2.firstName, 'last': user2.lastName, 'esps': user1.esps})# can also do like this


#c.execute("SELECT * FROM users WHERE last_name = 'Nippleaction' OR last_name = 'Ballz'")

#c.execute("UPDATE users SET esps = '1.2.1.2' where firs_name = 'Moe'")

#c.execute("SELECT * FROM users WHERE last_name = ? OR last_name = ?", ('Nippleaction','Ballz')) # if was just one would be ('Nippleaction',)

#print(c.fetchall())

#con.commit()

#con.close()


########



#in text type use YYYY-MM-DD HH:MM:SS.SSS for date and time

conn = sqlite3.connect('proj.db')

query = (''' CREATE TABLE IF NOT EXISTS USER
            (ID     INTAGER     PRIMARY KEY,
            NAME    TEXT        NOT NULL,
            PASSWORD    TEXT    NOT NULL,
            EMAIL   TEXT    NOT NULL
            ); ''')

conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS ESP
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
            USER_ID    INTAGER    NOT NULL,
            ESP_NAME    TEXT    NOT NULL,
            DATE    TEXT    NOT NULL,
            FOREIGN KEY(USER_ID) REFERENCES USER(ID),
            FOREIGN KEY(ESP_NAME) REFERENCES ESP(NAME)
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
c.execute(''' INSERT INTO USER (ID, NAME, PASSWORD) VALUES(?, ?, ?)''', (3, 'sup brah', '123'))

c.execute(''' INSERT INTO ESP (ID, IP, NAME, USER_ID) VALUES(?, ?, ?, ?)''', (1, "1.1.1.1", 'frontDoor', 3))


c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID, ESP_NAME,  DATE) VALUES(?, ?, ?, ?, ?)''', (1, "/static/db/3/output.png", 3, "frontDoor", datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID, ESP_NAME,  DATE) VALUES(?, ?, ?, ?, ?)''', (2, "/static/db/3/output.png", 3, "frontDoor", datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID, ESP_NAME,  DATE) VALUES(?, ?, ?, ?, ?)''', (3, "/static/db/3/output.png", 3, "frontDoor", datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID, ESP_NAME,  DATE) VALUES(?, ?, ?, ?, ?)''', (4, "/static/db/3/output.png", 3, "frontDoor", datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID, ESP_NAME,  DATE) VALUES(?, ?, ?, ?, ?)''', (5, "/static/db/3/output.png", 3, "frontDoor", datetime.datetime.now()))
c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID, ESP_NAME,  DATE) VALUES(?, ?, ?, ?, ?)''', (8, "/static/db/3/output.png", 3, "frontDoor", datetime.datetime.now()))



conn.commit()
c.close()
conn.close()

#to retreive img

#m = c.execute("SELECT * FROM PICTURE")

#for x in m:
#    data = x[1] # x[0] is id, 1 is blob and 2 is user_id

#with open('output.png','wb') as f:
#    f.write(data)
"""
m = c.execute("SELECT ID FROM USER WHERE NAME LIKE ? AND PASSWORD LIKE ?", ('sup brah', '123'))
m = [row[0] for row in c]
print('b4 m')


print(m)
print('after m')
conn.commit()
c.close()
conn.close()
"""


#generate random string for img name
#def get_random_string(length):
    # Random string with the combination of lower and upper case
#    letters = string.ascii_letters
#    return ''.join(random.choice(letters) for i in range(length))