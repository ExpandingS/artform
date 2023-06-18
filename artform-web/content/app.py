from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy

# Libraries for securely storing passwords, and defanging filenames.
from hashlib import sha256
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "password1234"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:abcde123@db:3306/artform"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()
db.init_app(app)

class users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String)
    password = db.Column("password", db.String)
    posts = db.Column("posts", db.JSON)
    submissions = db.Column("submissions", db.JSON)
    
    def __init__(self, name, password, posts, submissions):
        self.name = name
        self.password = password
        self.posts = posts
        self.submissions = submissions
class posts(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    title = db.Column("title", db.String)
    description = db.Column("description", db.String)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.TIMESTAMP)
    duration_hours = db.Column("duration", db.Integer)

    def __init__(self, title, description, created_by, duration_hours):
        self.title = title
        self.description = description
        self.created_by = created_by
        self.created_at = db.func.current_timestamp()
        self.duration_hours = duration_hours

class submissions(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    title = db.Column("title", db.String)
    description = db.Column("description", db.String)
    link_id = db.Column("link_id", db.String)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.TIMESTAMP)

    def __init__(self, title, description, link_id, created_by):
        self.title = title
        self.description = description
        self.link_id = link_id
        self.created_by = created_by
        self.created_at = db.func.current_timestamp()
 
    

@app.route("/")
def index():
    return "<p>Hello, World! What's up?</p> <a href=\"/login\">login</a>"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.permanent = True
        user = request.form["username"]

        found_user = users.query.filter_by(name=user).first()
        if found_user:
            print(found_user.password, flush=True)
            if sha256(request.form["password"].encode('utf-8')).hexdigest() != found_user.password:
                flash("Incorrect Password!")
                return redirect(url_for("login"))
            
            session["user"] = found_user.name
            session["user_id"] = found_user.id
        else: # Move to create user page
            new_user = users(
                user,
                sha256(request.form["password"].encode('utf-8')).hexdigest(),
                [])
            db.session.add(new_user)
            db.session.commit()
            flash("Account Created!")
            session["user"] = new_user.name
            return redirect(url_for("user"))

        flash("Login Successful!")
        return redirect(url_for("user"))
    else:
        if "user" in session:
            flash("Already logged in!")
            return redirect(url_for("user"))
    return render_template("login.html")

@app.route("/user")
def user():
    if "user" in session:
        user = session["user"]
        return render_template("user.html", name=user)
    else:
        flash("You are not logged in!")
        return redirect(url_for("login"))

@app.route("/create-post", methods=["GET","POST"])
def create_post():
    if "user" not in session:
        flash("You need to be logged in to do this")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        new_post = posts(request.form["title"],
                         request.form["description"],
                         session["user_id"],
                         request.form["duration"])
        return redirect(url_for("user")) # Replace with post page
    else:
        return render_template("create-post.html")
    
@app.route("/post/<id>")
def view_post(id):
    post = posts.query.filter_by(id=id).first()
    return render_template("view-post.html",
                           title=post.title,
                           description=post.description,
                           created_by=post.created_by,
                           created_at=post.created_at,
                           duration=post.duration_hours)

@app.route("/add-submission", methods=["GET","POST"])
def add_post():
    if "user" not in session:
        flash("You are not currently logged in.")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        f = request.files['file']
        f.save('/code/content/static/user-content/' + secure_filename(f.filename))
        new_submission = submissions(request.form["title"],
                         request.form["description"],
                         f.filename,
                         session["user_id"])
        db.session.add(new_submission)
        db.session.commit()
        flash("Submission Added!")
        return redirect(url_for("user")) # Replace with post page
    else:
        return render_template("add-submission.html")
    
@app.route("/view-submission/<id>")
def view_submission(id):
    submission = submissions.query.filter_by(id=id).first()
    return render_template("view-submission.html",
                           image_link="/static/user-content/" + submission.link_id,
                           title=submission.title,
                           description=submission.description) # Add link to user



@app.route("/logout")
def logout():
    flash("You have been logged out!", "info")
    session.pop("user", None)
    return redirect(url_for("login"))