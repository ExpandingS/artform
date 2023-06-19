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

def sha256_pw(password):
    return sha256(password.encode('utf-8')).hexdigest()

class users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String)
    password = db.Column("password", db.String)
    challenges = db.Column("challenges", db.JSON)
    submissions = db.Column("submissions", db.JSON)
    
    def __init__(self, name, password):
        self.name = name
        self.password = sha256_pw(password)
        self.challenges = []
        self.submissions = []
class challenges(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    title = db.Column("title", db.String)
    description = db.Column("description", db.String)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.TIMESTAMP)
    duration_hours = db.Column("duration_hours", db.Integer)

    def __init__(self, title, description, created_by, duration_hours):
        self.title = title
        self.description = description
        self.created_by = created_by
        self.created_at = db.func.current_timestamp()
        self.duration_hours = duration_hours

class submissions(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    challenge_id = db.Column("challenge_id", db.Integer, db.ForeignKey("challenges.id"))
    title = db.Column("title", db.String)
    description = db.Column("description", db.String)
    link_id = db.Column("link_id", db.String)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.TIMESTAMP)

    def __init__(self, title, description, link_id, created_by, challenge_id):
        self.challenge_id = challenge_id
        self.title = title
        self.description = description
        self.link_id = link_id
        self.created_by = created_by
        self.created_at = db.func.current_timestamp()
 
class comments(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    submission_id = db.Column("submission_id", db.Integer, db.ForeignKey("submissions.id"))
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.TIMESTAMP)
    message = db.Column("message", db.String)

    def __init__(self, submission_id, created_by, message):
        self.submission_id = submission_id
        self.created_by = created_by
        self.created_at = db.func.current_timestamp()
        self.message = message


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
            if sha256_pw(request.form["password"]) == found_user.password: #If the password 
                session["user"] = found_user.name
                session["user_id"] = found_user.id
                flash("Login Successful!")
                return redirect(url_for("user"))
            else: # Reject password 
                flash("Incorrect Password!")
                return redirect(url_for("login"))
            
        else: # Account doesn't exist.
            flash("Account doesn't exist!")
            return redirect(url_for("login"))

    else:
        if "user" in session:
            flash("Already logged in!")
            return redirect(url_for("user"))
        return render_template("login.html")

@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    if "user" in session: # Don't let user access create page if they're already logged in.
            flash("Already logged in!")
            return redirect(url_for("user"))
    
    if request.method == "POST":
        session.permanent = True
        user = request.form["username"]
        found_user = users.query.filter_by(name=user).first()
        if found_user:
            flash("Username already exists!")
            return redirect(url_for("sign_up"))
        
        # Check password length
        # if len(request.form["password"]) < 10:
        #     flash("Password must be at least 10 characters!")
        #     return redirect(url_for("sign_up"))

        # Add user to database
        new_user = users(
            user,
            request.form["password"])
        db.session.add(new_user)
        db.session.commit()

        flash("Account Created!")
        session["user"] = new_user.name
        return redirect(url_for("user"))
    else:
        return render_template("sign-up.html")

@app.route("/home")
def user():
    if "user" in session:
        user = session["user"]
        return render_template("home.html", name=user)
    else:
        flash("You are not logged in!")
        return redirect(url_for("login"))

@app.route("/create-challenge", methods=["GET","POST"])
def create_challenge():
    if "user" not in session:
        flash("You need to be logged in to make a challenge!")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        new_challenge = challenges(request.form["title"],
                         request.form["description"],
                         session["user_id"],
                         request.form["duration_hours"])
        db.session.add(new_challenge)
        db.session.commit()
        
        # Redirect to challenge page:
        return redirect(url_for("challenge", id=new_challenge.id))
    else:
        return render_template("create-challenge.html")
    
@app.route("/challenge/<id>")
def challenge(id):
    challenge = challenges.query.filter_by(id=id).first()
    all_submissions = submissions.query.filter_by(challenge_id=id).all()
    if challenge is not None:
        return render_template("challenge.html",
                            title=challenge.title,
                            description=challenge.description,
                            created_by=challenge.created_by, # Show actual user name, not just number.
                            created_at=challenge.created_at,
                            duration=challenge.duration_hours,
                            challenge_id=id,
                            submissions=all_submissions
                            )
    else: return render_template("404.html")

@app.route("/explore")
def explore():
    # Get all challenges
    all_challenges = challenges.query.all()
    return render_template("explore.html", challenges=all_challenges)

@app.route("/add-submission/<challenge>", methods=["POST"])
def add_submission(challenge):
    if "user" not in session:
        flash("You are not currently logged in.")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        f = request.files['file']
        f.save('/code/content/static/user-content/' + secure_filename(f.filename))
        new_submission = submissions(request.form["title"],
                         request.form["description"],
                         secure_filename(f.filename),
                         session["user_id"],
                         challenge)
        
        db.session.add(new_submission)
        db.session.commit()
        flash("Submission Added!")
        return redirect(url_for("challenge", id=challenge)) # Replace with post page

@app.route("/add-comment/<submission>", methods=["POST"])
def add_comment(submission):
    if "user" not in session:
        flash("You are not currently logged in.")
    new_comment = comments(submission,
                         session["user_id"],
                         request.form["message"])
    db.session.add(new_comment)
    db.session.commit()
    return redirect(request.referrer)
 
@app.route("/view-submission/<id>")
def view_submission(id):
    submission = submissions.query.filter_by(id=id).first()
    return render_template("view-submission.html",
                           image_link="/static/user-content/" + submission.link_id,
                           title=submission.title,
                           description=submission.description) # Add link to user

# @app.route("/delete-submission/<id>")
# def delete_submission(id):
#     submission = submissions.query.filter_by(id=id).first()
#     db.session.delete(submission)
#     db.sessio n.commit()
#     return redirect(url_for("post", id=submission.post_id))

@app.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method == "POST":
        flash("You have been logged out!", "info")
        session.pop("user", None)
        return redirect(url_for("login"))
    else:
        if "user" not in session:
            flash("You are not currently logged in.")
            return redirect(url_for("login"))
        else:
            return render_template("logout.html", username=session["user"])