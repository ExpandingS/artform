from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
app = Flask(__name__)
app.secret_key = "password1234"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:abcde123@localhost:3306"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

@app.route("/")
def index():
    return "<p>Hello, World! What's up?</p>"

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session["username"] = request.form["username"]
        return redirect(url_for("user", name=session["username"]))
    else:
        if "username" in session:
            flash("Already logged in")
            return redirect(url_for("user", name=session["username"]))
    return render_template("login.html")

@app.route("/user", methods=["POST", "GET"])
def user():
    email = None
    if "username" in session:
        user = session["username"]

        if request.method == "POST":
            email = request.form["email"]
            session["email"] = email
        return render_template("user.html", email=email, name=user)
    else:
        flash("You are not logged in")
        return redirect(url_for("login"))
    
@app.route("/logout")
def logout():
    flash("You have been logged out", "info")
    session.pop("username", None)
    session.pop("email", None)
    return redirect(url_for("login"))