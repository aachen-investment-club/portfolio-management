from __main__ import app

from flask import Flask
from flask import render_template

@app.route("/health")
def health():
    return "healthy"

@app.route("/")
def index():
    return render_template("index.html")