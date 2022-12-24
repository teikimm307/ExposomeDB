#!/usr/bin/env python3

from flask import Flask, render_template, session, request, abort, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db: SQLAlchemy = SQLAlchemy()
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.secret_key = '98d31240f9fbe14c8083586db49c19c3a8d3f726'


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    query: db.Query

    @classmethod
    def generate_password(cls, pw: str):
        return bcrypt.hashpw(pw, bcrypt.gensalt(12))

    @classmethod
    def authenticate(cls, username: str, pw: str):
        user = Admin.query.filter_by(username=username).one_or_none()
        if user and bcrypt.checkpw(pw, user.password):
            session['admin'] = user.username
            return user
        else:
            return None

    @classmethod
    def exists(cls):
        user = Admin.query.one_or_none()
        return True if user else False

    @classmethod
    def authorize(cls):
        if not session.get('admin'):
            return redirect(url_for("admin_login"))


class Chemical(db.Model):
    query: db.Query
    id = db.Column(db.Integer, primary_key=True)
    pubchem_cid = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String, nullable=False)
    formula = db.Column(db.String, nullable=False)
    mass = db.Column(db.Float, nullable=False)
    mz = db.Column(db.Float, nullable=False)
    rt = db.Column(db.Float, nullable=False)

# Error Handlers


@app.errorhandler(404)
def handler_404(msg):
    return render_template("errors/404.html")


@app.errorhandler(403)
def handler_403(msg):
    return render_template("errors/403.html")


# Admin routes
@app.route('/admin')
def admin_root():
    if login := Admin.authorize():
        return login
    return render_template("admin.html", user=session.get("admin"))


@app.route('/admin/create', methods=['GET', 'POST'])
def admin_create():
    if Admin.exists():
        if login := Admin.authorize():
            return login
    if request.method == "GET":
        return render_template("register.html")
    else:
        username, pw = request.form.get('username'), request.form.get('password')
        if username is None or pw is None:
            return render_template("register.html", fail="Invalid Input.")
        elif db.session.execute(db.select(Admin).filter_by(username=username)).fetchone():
            return render_template("register.html", fail="Username already exists.")
        else:
            db.session.add(Admin(username=username, password=Admin.generate_password(pw)))
            db.session.commit()
            return render_template("register.html", success=True)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username, pw = request.form.get('username', ''), request.form.get('password', '')
        if Admin.authenticate(username, pw):
            return render_template("login.html", success=True)
        else:
            return render_template("login.html", fail="Could not authenticate.")
    else:
        return render_template("login.html")


@app.route('/admin/logout', methods=['GET'])
def admin_logout():
    session.pop('admin')
    return redirect(url_for('home'))


@app.route("/")
def home():
    if Admin.exists():
        return render_template("index.html")
    else:
        return redirect(url_for("admin_create"))


@app.route("/search")
def search():
    return "searching url"


if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
