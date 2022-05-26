import base64
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
    conn = sqlite3.connect('proj.db')
    c = conn.cursor()
    fiveMostRecent = c.execute("SELECT DATA,DATE,ESP_NAME FROM PICTURE  WHERE USER_ID LIKE ? ORDER BY DATE desc LIMIT 5", (id,))
    #    GROUP BY USER_ID 
    #imgs = c.execute("SELECT * FROM PICTURE WHERE USER_ID LIKE ?", (id)) 
    data = []
    names = []
    dates = []
    for img in fiveMostRecent:
        #Base64 Encoding
        
        #base64_encoded= base64.b64encode(x[1])
        #base64_encoded_string= base64_encoded.decode('utf-8')
        #print("printing img1")
        #print(img[1])
        #with open(img[0] + '.png','wb') as f:
        #    f.write(img[1])
        data.append("data:image/png;charset=UTF-8;base64," + base64.b64encode(img[0]).decode('utf-8'))
        #data.append('iVBORw0KGgoAAAANSUhEUgAAAAoAAAAJCAIAAACExCpEAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAASSURBVChTY5DutMGDRqZ0pw0A4ZNOwQNf')
        dates.append(img[1])#.split(".")[0]) #split to remove miliseconds
        names.append(img[2])
    
    
    c.close()
    conn.close()    
    #print(data)
    return render_template('dbImage.html', imgs = data, dates = dates, esps = names)




if __name__ == "__main__":
    app.run(debug=True)