import base64
from xml.etree.ElementTree import tostring
from flask import Flask, render_template, redirect, request, url_for
import sqlite3
app = Flask(__name__)

@app.route('/', methods = ['POST', 'GET'])
def profile():
    if request.method == 'POST':
        usr = request.form.get('username')
        pw = request.form.get('password')
        conn = sqlite3.connect('proj.db')
        c = conn.cursor()
        c.execute("SELECT ID FROM USER WHERE NAME like ? AND PASSWORD like ?", (usr, pw))
        m = [row[0] for row in c] [0]
        return redirect(url_for("images", id = m))
    else:
        return render_template('login.html')
    


@app.route('/images/<id>')
def images(id):    
    print('b4 id')
    print(id)
    conn = sqlite3.connect('proj.db')
    c = conn.cursor()
    imgs = c.execute("SELECT * FROM PICTURE WHERE USER_ID LIKE ?", (id)) 
    data = []
    for img in imgs:
        
        #Base64 Encoding
        
        #base64_encoded= base64.b64encode(x[1])
        #base64_encoded_string= base64_encoded.decode('utf-8')


        data.append("data:image/png;charset=UTF-8;base64," + base64.b64encode(img[1]).decode('utf-8'))
        #data.append('iVBORw0KGgoAAAANSUhEUgAAAAoAAAAJCAIAAACExCpEAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAASSURBVChTY5DutMGDRqZ0pw0A4ZNOwQNf')
    c.close()
    conn.close()    
    #print(data)
    return render_template('dbImage.html', imgs = data)




if __name__ == "__main__":
    app.run(debug=True)