from flask import Flask, render_template
import socket
from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd

app = Flask(__name__)


@app.route("/")
def main():
    return render_template('index.html')
@app.route("/about")
def about():
    return render_template('about.html')
@app.route("/client")
def client():
    return render_template('client.html')
@app.route("/images")
def images():
    return render_template('images.html')
@app.route("/Stats")
def stats():
    Func = open("templates/stats.html","w")
    
    df = pd.DataFrame({
    "Days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday","Saturday","Sunday"],
    #"Days": [["Monday", 4], ["Tuesday", 1], ["Wednesday", 2], ["Thursday", 2], ["Friday", 3], ["Saturday", 5], ["Sunday", 9]],
    "Photos": [4,1,2,2,3,5,9],
    "Day's Averege": [3,2,3,2,7,4,1],
    #"Colours": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday","Saturday","Sunday", "Last Week's Averege","Last Week's Averege","Last Week's Averege","Last Week's Averege", "This Week's Averege", "This Week's Averege","This Week's Averege"],
    })


    df.to_html("templates/stats.html")
    #file = open("templates/stats.html").read()
    #htmlFile = file.read()
    #soup = Soup(htmlFile) 
    #headTag = soup.find('table') 
    #divTag = soup.new_tag('h2') 
    #divTag['class'] = "" 
    #headTag.insert_after(divTag)
    #print(soup) #This should print the new, modified html

    #Func.write("<a href="{{ url_for('main') }}">Return To Homepage</a>")
    return render_template('stats.html')

if __name__ == "__main__":
    app.run(debug = True, host="0.0.0.0", port = 80)




s = socket.socket()         
 
s.bind(('0.0.0.0', 45000))
s.listen(5)

print("waiting clients")
while True:
    print("accepting...")
    client, addr = s.accept()
    print("accepted")
    print(client)
    print(addr)

    while True:
        

            
        content = client.recv(32)

        if content:
            print(content)
        else:
            break
 
    print("Closing connection")
    client.close()