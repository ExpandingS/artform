from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import csv

# Libraries for securely storing passwords, and defanging filenames.
from hashlib import sha256
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "password1234"

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:abcde123@db:3306/artform"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()
db.init_app(app)
# db.create_all()

def sha256_pw(password):
    return sha256(password.encode('utf-8')).hexdigest()

class users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String)
    password = db.Column("password", db.String)
    
    def __init__(self, name, password):
        self.name = name
        self.password = sha256_pw(password)

class challenges(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    title = db.Column("title", db.String)
    description = db.Column("description", db.String)
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column("created_at", db.TIMESTAMP)
    ongoing = db.Column("ongoing", db.Boolean)
    winning_submission = db.Column("winning_submission", db.Integer, db.ForeignKey("submissions.id"))    

    def __init__(self, title, description, created_by):
        self.title = title
        self.description = description
        self.created_by = created_by
        self.created_at = db.func.current_timestamp()
        self.ongoing = True

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
class likes(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    submission_id = db.Column("submission_id", db.Integer, db.ForeignKey("submissions.id"))
    created_by = db.Column("created_by", db.Integer, db.ForeignKey("users.id"))
    def __init__(self, submission_id, created_by):
        self.submission_id = submission_id
        self.created_by = created_by

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
    return render_template("index.html")

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
            flash("Account doesn't exist! You may need to sign up first.")
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
            flash("Username already taken!")
            return redirect(url_for("sign_up"))
        
        if request.form["password"] != request.form["confirm_password"]:
            flash("Passwords do not match!")
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
    return redirect(url_for("index"))

@app.route("/create-challenge", methods=["GET","POST"])
def create_challenge():
    if "user" not in session:
        flash("You need to be logged in to make a challenge!")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        new_challenge = challenges(request.form["title"],
                         request.form["description"],
                         session["user_id"],)
        db.session.add(new_challenge)
        db.session.commit()
        
        # Redirect to challenge page:
        return redirect(url_for("challenge", id=new_challenge.id))
    else:
        return render_template("create-challenge.html")
    
@app.route("/export-challenge/<challenge>", methods=["POST"])
def explort_challenge(challenge):
    challenge = challenges.query.filter_by(id=challenge).first()
    if challenge is None:
        flash("Challenge not found!")
        return redirect(url_for("user"))
    
    all_submissions = submissions.query.filter_by(challenge_id=challenge.id).all()
    csv_file = open(f"/code/content/static/user-content/challenge-{challenge.id}.csv", "w")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([challenge.id, challenge.title, challenge.description])

    for submission in all_submissions:
        number_of_likes = likes.query.filter_by(submission_id=submission.id).count()
        csv_writer.writerow([submission.id, submission.title, submission.description, submission.link_id, submission.created_by, submission.created_at, number_of_likes])
    
    csv_file.close()
    return send_file(f"/code/content/static/user-content/challenge-{challenge.id}.csv", as_attachment=True)

@app.route("/challenge/<id>")
def challenge(id):
    challenge = challenges.query.filter_by(id=id).first()

    if challenge is not None:
        owner_username = users.query.filter_by(id=challenge.created_by).first().name
        all_submissions = submissions.query.filter_by(challenge_id=id).all()

        # Add fields to each submission.
        for submission in all_submissions:
            all_comments = comments.query.filter_by(submission_id=submission.id).all()
            submission.comments = all_comments
            # Get username of user who created submission
            submission.created_by_username = users.query.filter_by(id=submission.created_by).first().name

            # Check if user has already liked this submission
            submission.already_liked = likes.query.filter_by(submission_id=submission.id, created_by=session["user_id"]).first() != None
            # Get number of likes on a submission
            submission.number_of_likes = likes.query.filter_by(submission_id=submission.id).count()

        return render_template("challenge.html",
                            title=challenge.title,
                            description=challenge.description,
                            created_by=owner_username, # Show actual user name, not just number.
                            created_at=challenge.created_at,
                            ongoing=challenge.ongoing,
                            challenge_id=id,
                            submissions=all_submissions,
                            user_owns_challenge=session["user_id"] == challenge.created_by,
                            )
    else:
        flash("Oops! That challenge does not exist.")
        return redirect(url_for("error_404"))

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
        return redirect(request.referrer) # Replace with post page

@app.route("/like/<submission>", methods=["POST"])
def like(submission):
    if "user" not in session:
        flash("You are not currently logged in.")
        return redirect(url_for("login"))
    
    submission = submissions.query.filter_by(id=submission).first()

    if likes.query.filter_by(submission_id=submission.id, created_by=session["user_id"]).first() is not None:
        flash("You have already liked this submission!")
        return redirect(request.referrer)
    
    new_like = likes(submission.id, session["user_id"])
    db.session.add(new_like)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/remove_like/<submission>", methods=["POST"])
def remove_like(submission):
    if "user" not in session:
        flash("You are not currently logged in.")
        return redirect(url_for("login"))
    user_like = likes.query.filter_by(submission_id=submission, created_by=session["user_id"]).first()
    db.session.delete(user_like)
    db.session.commit()
    return redirect(request.referrer)

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
        
@app.route("/404")
def error_404():
    return render_template("404.html")

@app.errorhandler(404)
def error_404(e):
    return render_template("404.html")