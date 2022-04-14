import base64
from xml.etree.ElementTree import tostring
from flask import Flask, render_template, redirect, request
import sqlite3
app = Flask(__name__)

@app.route('/')
def profile():
    return render_template('login.html')

@app.route('/logon', methods = ['POST'])
def logon():
    #has to be request.form
    usr = request.form.get('usr')
    pw = request.form.get('pw')
    print(usr)
    print(pw)
    conn = sqlite3.connect('proj.db')
    c = conn.cursor()
    c.execute("SELECT ID FROM USER WHERE NAME like ? AND PASSWORD like ?", (usr, pw))
    m = [row[0] for row in c] [0]
    print(m)
    return redirect('/images/'+ str(m))


@app.route('/images/<id>')
def images(id):    
    print('b4 id')
    print(id)
    conn = sqlite3.connect('proj.db')
    c = conn.cursor()
    m = c.execute("SELECT * FROM PICTURE WHERE USER_ID LIKE ?", (id))
    file1 = open("base64.txt", "w") 
    data = []
    for x in m:
        
        #Base64 Encoding
        
        #base64_encoded= base64.b64encode(x[1])
        #base64_encoded_string= base64_encoded.decode('utf-8')


        data.append(base64.b64encode(x[1]).decode('utf-8'))

        file1.write(base64.b64encode(x[1]).decode('utf-8'))

    c.close()
    conn.close()    
    #print(data)
    return render_template('dbImage.html', imgs = data)




if __name__ == "__main__":
    app.run()