import sqlite3
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

conn = sqlite3.connect('proj.db')

query = (''' CREATE TABLE IF NOT EXISTS USER
            (ID     INTAGER     PRIMARY KEY,
            NAME    TEXT        NOT NULL,
            PASSWORD    TEXT    NOT NULL
            ); ''')

conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS ESP
            (ID     INTAGER     PRIMARY KEY,
            IP    TEXT        NOT NULL,
            USER_ID    INTAGER    NOT NULL,
            FOREIGN KEY(USER_ID) REFERENCES USER(ID)
            ); ''')

conn.execute(query)

query = (''' CREATE TABLE IF NOT EXISTS PICTURE
            (ID     INTAGER     PRIMARY KEY,
            DATA    BLOB        NOT NULL,
            USER_ID    INTAGER    NOT NULL,
            FOREIGN KEY(USER_ID) REFERENCES USER(ID)
            ); ''')

conn.execute(query)



#insert img
c = conn.cursor()
#with open('clouds.png', 'rb') as f:
#    blob = f.read()
#c.execute(''' INSERT INTO USER (ID, NAME, PASSWORD) VALUES(?, ?, ?)''', (3, 'sup brah', '123'))

#c.execute(''' INSERT INTO PICTURE (ID, DATA, USER_ID) VALUES(?, ?, ?)''', (1, blob, 3))
m = c.execute("SELECT ID FROM USER WHERE NAME LIKE ? AND PASSWORD LIKE ?", ('sup brah', '123'))
#to retreive img

#m = c.execute("SELECT * FROM PICTURE")

#for x in m:
#    data = x[1] # x[0] is id, 1 is blob and 2 is user_id

#with open('output.png','wb') as f:
#    f.write(data)
m = [row[0] for row in c]
print('b4 m')


print(m)
print('after m')
conn.commit()
c.close()
conn.close()

#generate random string for img name
def get_random_string(length):
    # Random string with the combination of lower and upper case
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))