import logging
import random
import re
from datetime import datetime

from flask import Flask, render_template

app = Flask(__name__)

# list of random gifs
images = [
   "https://i.imgur.com/OIxyhlS.gifv",
    "https://i.imgur.com/s2Qjyyo.gifv",
    "https://i.imgur.com/s2Qjyyo.gifv",
    "https://i.imgur.com/a8Fq1ex.gifv",
    ]

@app.route('/index')
def index():
    url = random.choice(images)
    return render_template('index.html', url=url)


@app.route("/")
def home():
    return render_template("home.html")

# New functions
@app.route("/about/")
def about():
    return render_template("about.html")


@app.route("/contact/")
def contact():
    return render_template("contact.html")

@app.route("/hello")
@app.route("/hello/<name>")
def hello_there(name = None):
   return render_template(
       "hello_there.html",
        name=name,
        date=datetime.now()
   )


@app.route("/api/data")
def get_data():
    logging.info("")
    return app.send_static_file("data.json")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
