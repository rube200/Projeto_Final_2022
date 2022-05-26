import base64
from distutils.log import error
from flask import Flask, flash, render_template, redirect, request, url_for, session
import sqlite3
from datetime import timedelta
app = Flask(__name__)
app.secret_key = "secret_Key.avi" #need secret key for session (can be any string)
app.permanent_session_lifetime = timedelta(hours=16)

@app.route('/login', methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        usr = request.form.get('username')
        pw = request.form.get('password')
        conn = sqlite3.connect('static/proj.db')
        c = conn.cursor()
        c.execute("SELECT ID FROM USER WHERE NAME like ? AND PASSWORD like ?", (usr, pw))
        m = [row[0] for row in c]
        session.permanent = True
        if not m:
            #session["error"] = True
            return render_template('login.html')
        session["error"] = False    
        session["user"] = int(m[0])
        return redirect(url_for("cards"))
    #if session.error:
    #    flash('Error in login')    
    return render_template('login.html')

@app.route('/register', methods = ['POST', 'GET'])
def register():
    if request.method == 'POST':
        usr = request.form.get('username')
        email = request.form.get('email')
        pw = request.form.get('password')
        if not checkUserExist(usr,pw):
            conn = sqlite3.connect('static/proj.db')
            c = conn.cursor()
            c.execute("INSERT INTO USER (ID, NAME, PASSWORD, EMAIL) VALUES(?, ?, ?, ?)", (getNewUserId(),usr, pw, email))
            c.commit()
            c.close()
            conn.close() 
            return redirect(url_for("login"))
         
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))
    
@app.route('/')
def dashboard():
    if "user" in session:
        return redirect(url_for("cards"))
    return redirect(url_for("login"))


@app.route('/doorbells')
def cards():
    if "user" in session:
        user = session["user"]
        print("happy if")
        conn = sqlite3.connect('static/proj.db')
        c = conn.cursor()
        c.execute("SELECT NAME,IP,ID FROM DOORBELL WHERE USER_ID like ?", (user,))
        esps = c.fetchall()
        names = []
        ips = []
        pic = []
        date = []
        for doorbell in esps:
            names.append(doorbell[0])
            ips.append(doorbell[1])
            c.execute("SELECT DATA,DATE FROM PICTURE WHERE DOORBELL_ID like ? ORDER BY DATE desc", (doorbell[2],))
            pics = c.fetchall()
            print(pics[0][1])
            pic.append(pics[0][0])
            date.append(pics[0][1].split(".")[0])
        c.close()
        conn.close() 
        return render_template('cards.html', name = names, ip = ips, pic = pic, date = date)
    return redirect(url_for(login))

@app.route('/addDoorbells',  methods = ['POST', 'GET'])
def addDoorbell():
    if "user" in session:
        if request.method == 'POST':
            return    
        return render_template('addDoorbell.html')
    return redirect(url_for(login))

    
@app.route('/doorbell/<id>')
def doorbell(id): 
    if "user" in session:
        conn = sqlite3.connect('static/proj.db')
        c = conn.cursor()
        c.execute("SELECT PICTURE.DATA, PICTURE.DATE, DOORBELL.NAME, DOORBELL.IP FROM PICTURE JOIN DOORBELL ON DOORBELL.ID = PICTURE.DOORBELL_ID  WHERE DOORBELL.ID LIKE ? ORDER BY DATE desc", (id,))
        pics = c.fetchall()
        data = []
        dates = []
        for img in pics:
            data.append(img[0])
            dates.append(img[1].split(".")[0]) #split to remove miliseconds  
        c.close()
        conn.close()    
        return render_template('doorbell.html', imgs = data, dates = dates, name = pics[0][2], ip = pics[0][3])
    return redirect(url_for("login")) 

@app.route('/image')
def image():
    if "user" in session:
        user = session["user"]
        conn = sqlite3.connect('static/proj.db')
        c = conn.cursor()
        c.execute("SELECT PICTURE.DATA, PICTURE.DATE, DOORBELL.NAME FROM PICTURE JOIN DOORBELL ON PICTURE.DOORBELL_ID = DOORBELL.ID WHERE DOORBELL.USER_ID LIKE ? order by PICTURE.DATE desc", (user,))
        bell_ids = c.fetchall()
        data = []
        names = []
        dates = []
        for bell in bell_ids:
            data.append(bell[0])
            dates.append(bell[1].split(".")[0]) #split to remove miliseconds
            names.append(bell[2])   
        c.close()
        conn.close()    
        #print(data)
        return render_template('imageGal.html', imgs = data, dates = dates, esps = names)
    return redirect(url_for("login"))





@app.route('/videos')
def video():
    if "user" in session:
        user = session["user"]
        conn = sqlite3.connect('static/proj.db')
        c = conn.cursor()
        c.execute("SELECT VIDEO.DATA, VIDEO.DATE, DOORBELL.NAME FROM VIDEO JOIN DOORBELL ON VIDEO.DOORBELL_ID = DOORBELL.ID WHERE DOORBELL.USER_ID LIKE ? order by VIDEO.DATE desc", (user,))
        bell_ids = c.fetchall()
        data = []
        names = []
        dates = []
        for bell in bell_ids:
            data.append(bell[0])
            dates.append(bell[1].split(".")[0]) #split to remove miliseconds
            names.append(bell[2])   
        c.close()
        conn.close()    
        return render_template('videoGal.html', vids = data, dates = dates, esps = names)
    return redirect(url_for("login"))



def getNewUserId():
    conn = sqlite3.connect('static/proj.db')
    c = conn.cursor()
    id = c.execute("SELECT MAX(ID) FROM USER")
    c.close()
    conn.close()
    print(id+1)
    return id+1

def checkUserExist(usr,pw):
    conn = sqlite3.connect('static/proj.db')
    c = conn.cursor()
    id = c.execute(" SELECT 1 FROM USER WHERE NAME LIKE ? AND PASSWORD LIKE ?", (usr,pw))
    c.close()
    conn.close()
    print(id)
    return id

if __name__ == "__main__":
    app.run(debug=True)