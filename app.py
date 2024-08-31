#!/usr/bin/env python3

import os
from flask import Flask, render_template, session, request, abort, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, and_
from flask_wtf import FlaskForm
import bcrypt
from wtforms_alchemy import model_form_factory
from flask_migrate import Migrate
from uuid import uuid4
import csv
import validate
import secrets
from dotenv import load_dotenv

load_dotenv()
# from datetime import date

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"

app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
db: SQLAlchemy = SQLAlchemy()
migrate = Migrate()
db.init_app(app)
migrate.init_app(app, db)

# Helper Methods


def object_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}

# Model Forms


BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

    institution = db.Column(db.String, nullable=False)
    position = db.Column(db.String, nullable=False)

    admin = db.Column(db.Boolean)

    # for type annotations
    query: db.Query

    @classmethod
    def generate_password(cls, pw: str):
        return bcrypt.hashpw(pw, bcrypt.gensalt(12))

    @classmethod
    def authenticate(cls, username: str, pw: str):
        user = User.query.filter_by(username=username).one_or_none()
        if user and bcrypt.checkpw(pw, user.password):
            session['user'] = user.username
            if user.admin:
                session['admin'] = user.username
            return user
        else:
            return None

    @classmethod
    def admin_exists(cls):
        user = User.query.filter_by(admin=True).first()
        return True if user else False

    @classmethod
    def authorize_or_redirect(cls, admin=True):
        if (admin and "admin" not in session) or "user" not in session:
            return redirect(url_for("login"))
        else:
            return None


class Chemical(db.Model):
    query: db.Query
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, nullable=False)
    standard_grp = db.Column(db.String, nullable=False)
    # all fields after here are included in the database
    chemical_db_id = db.Column(db.String)
    library = db.Column(db.String)
    # important fields
    metabolite_name = db.Column(db.String, nullable=False)
    formula = db.Column(db.String, nullable=False)
    monoisotopic_mass = db.Column(db.Float, nullable=False)

    pubchem_cid = db.Column(db.Integer)
    pubmed_refcount = db.Column(db.Integer)
    inchikey = db.Column(db.String, nullable=False)
    inchikey14 = db.Column(db.String)

    final_mz = db.Column(db.Float, nullable=False)
    final_rt = db.Column(db.Float, nullable=False)

    final_adduct = db.Column(db.String, nullable=False)
    detected_adducts = db.Column(db.String)
    adduct_calc_mz = db.Column(db.String)
    msms_detected = db.Column(db.Boolean, nullable=False)
    msms_purity = db.Column(db.Float)

    mode = db.Column(db.String)

    # serialized into datetime.date
    createdAt = db.Column(db.Date, default=db.func.now(),
                          onupdate=db.func.now())


class ChemicalForm(ModelForm):
    class Meta:
        csrf = False
        model = Chemical

# Error Handlers


@app.errorhandler(404)
def handler_404(msg):
    return render_template("errors/404.html")


@app.errorhandler(403)
def handler_403(msg):
    return render_template("errors/403.html")


# Admin routes
@app.route('/dashboard')
def admin_root():
    user = User.query.filter_by(username=session.get('user')).one_or_404()
    if 'admin' in session:
        result = Chemical.query.order_by(
            Chemical.createdAt.desc()).first()
        return render_template("admin.html", user=user, lastcreated=result)
    if 'user' in session:
        return render_template("user.html", user=user)
    return User.authorize_or_redirect(admin=False) or ""


@app.route('/accounts/create', methods=['GET', 'POST'])
def accounts_create():
    if User.admin_exists():
        if login := User.authorize_or_redirect():
            return login
    if request.method == "GET":
        return render_template("register.html")
    else:
        username, pw = request.form.get(
            'username'), request.form.get('password')
        if username is None or pw is None:
            return render_template("register.html", fail="Invalid Input.")
        elif db.session.execute(db.select(User).filter_by(username=username)).fetchone():
            return render_template("register.html", fail="Username already exists.")
        else:
            # because the IDE complains about type mismatches
            form = {} | request.form
            form['password'] = User.generate_password(pw)
            form['admin'] = (True if form.get('admin') == 'y' else False)
            form.pop('reconfirm')
            user = User(**form)
            db.session.add(user)
            db.session.commit()
            return render_template("register.html", success=True)


@app.route('/accounts/edit', methods=['GET', 'POST'])
def accounts_edit():
    if login := User.authorize_or_redirect(admin=False):
        return login
    user = User.query.filter_by(
        username=session.get('user')).limit(1).one_or_404()
    if request.method == "GET":
        return render_template("account_edit.html", user=object_as_dict(user))
    else:
        dct = object_as_dict(user)
        # update all of the changes
        for key in request.form:
            if key in dct:
                setattr(user, key, request.form[key])
        db.session.commit()
        return render_template("account_edit.html", user=object_as_dict(user), success=True)


@app.route('/accounts/view')
def accounts_all():
    if "admin" not in session:
        abort(403)
    users = [object_as_dict(u) for u in User.query.all()]
    for u in users:
        u.pop("password")
    return jsonify(users)


@app.route('/accounts/view/<int:id>')
def accounts_view(id):
    user = User.query.filter_by(id=id).one_or_404()
    return render_template("account_view.html", user=object_as_dict(user))


@app.route('/accounts/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username, pw = request.form.get(
            'username', ''), request.form.get('password', '')
        if User.authenticate(username, pw):
            return render_template("login.html", success=True)
        else:
            return render_template("login.html", fail="Could not authenticate.")
    else:
        return render_template("login.html")


@app.route('/accounts/logout', methods=['GET'])
def logout():
    if "admin" in session:
        session.pop('admin')
    if "user" in session:
        session.pop('user')
    return redirect(url_for('home'))


@app.route("/")
def home():
    if User.admin_exists():
        return render_template("index.html")
    else:
        return redirect(url_for("accounts_create"))

# Routes for CRUD operations on chemicals


@app.route("/chemical/create", methods=['GET', 'POST'])
def chemical_create():
    if not session.get('admin'):
        abort(403)
    user = User.query.filter_by(username=session.get('user')).one_or_404()
    if request.method == "POST":
        form = ChemicalForm(**(request.form | {"person_id": user.id}))
        if form.validate():
            new_chemical = Chemical(**form.data)
            db.session.add(new_chemical)
            db.session.commit()
            return render_template("create_chemical.html", form=ChemicalForm(), user=object_as_dict(user), success=True)
        else:
            return render_template("create_chemical.html", form=form, invalid=True), 400
    else:
        form = ChemicalForm(person_id=user.id)
        return render_template("create_chemical.html", form=form, user=object_as_dict(user))


@app.route("/chemical/<int:id>/update", methods=['GET', 'POST'])
def chemical_update(id: int):
    if not session.get('admin'):
        abort(403)
    current_chemical: Chemical = Chemical.query.filter_by(id=id).one_or_404()
    dct = object_as_dict(current_chemical)
    if request.method == "POST":
        form = ChemicalForm(**request.form)
        if form.validate():
            # take the row with id and update it.
            for k in form.data:
                setattr(current_chemical, k, form.data[k])
            db.session.commit()
            return render_template("create_chemical.html", form=form, success=True, id=id)
        else:
            form = ChemicalForm(**dct)
            return render_template("create_chemical.html", form=form, invalid=True, id=id), 400
    else:
        form = ChemicalForm(**dct)
        return render_template("create_chemical.html", form=form, id=id)


@app.route("/chemical/<int:id>/delete")
def chemical_delete(id: int):
    if not session.get('admin'):
        abort(403)
    current_chemical: Chemical = Chemical.query.filter_by(id=id).one_or_404()
    db.session.delete(current_chemical)
    db.session.commit()
    return render_template("delete_chemical.html", id=id)


@app.route("/chemical/<int:id>/view")
def chemical_view(id: int):
    current_chemical: Chemical = Chemical.query.filter_by(id=id).one_or_404()
    dct = object_as_dict(current_chemical)
    return render_template("view_chemical.html", id=id, chemical=dct)


@app.route("/chemical/all")
def chemical_all():
    if not session.get('admin'):
        abort(403)
    result: list[Chemical] = Chemical.query.all()
    data = []
    for x in result:
        data.append({c.name: getattr(x, c.name) for c in x.__table__.columns})
    return jsonify(data)


@app.route("/chemical/search", methods=["POST"])
def search_api():
    query = request.json
    if query is None:
        return jsonify([])
    for field in query:
        query[field] = float(query[field])
    mz_min, mz_max = query.get('mz_min'), query.get('mz_max')
    rt_min, rt_max = query.get('rt_min'), query.get('rt_max')
    year_max, month_max, day_max = int(query.get(
        'year_max')), int(query.get('month_max')), int(query.get('day_max'))

    try:
        mz_filter = and_(mz_max > Chemical.final_mz,
                         Chemical.final_mz > mz_min)
        rt_filter = and_(rt_max > Chemical.final_rt,
                         Chemical.final_rt > rt_min)
        # date_filter = date(year_max, month_max, day_max) >= Chemical.createdAt
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    result = Chemical.query.filter(
        and_(mz_filter, rt_filter)
    ).limit(20).all()

    data = []
    for x in result:
        data.append({"url": url_for("chemical_view", id=x.id),
                    "name": x.metabolite_name, "mz": x.final_mz, "rt": x.final_rt})
    return jsonify(data)


# Utilities for doing add and search operations in batch
# no file over 3MB is allowed.
app.config['MAX_CONTENT_LENGTH'] = 3 * 1000 * 1000


@app.route("/chemical/batchadd", methods=["GET", "POST"])
def batch_add_request():
    if not session.get('admin'):
        abort(403)
    user = User.query.filter_by(username=session.get('user')).one_or_404()
    if request.method == "POST":
        if "input" not in request.files or request.files["input"].filename == '':
            return render_template("batchadd.html", invalid="Blank file included")
        # save the file to RAM
        file = request.files["input"]
        os.makedirs("/tmp/walkerdb", exist_ok=True)
        filename = os.path.join("/tmp/walkerdb", str(uuid4()))
        file.save(filename)
        # perform cleanup regardless of what happens.
        def cleanup(): return os.remove(filename)
        # read it as a csv
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter="\t")
            results, error = validate.validate_insertion_csv_fields(reader)
            if error:
                cleanup()
                return render_template("batchadd.html", invalid=error)
            else:
                chemicals = []
                overwritten_chemicals = []
                for result in results:
                    overwritten = False
                    if request.form["overwrite"] == "y":
                        current_chemical = Chemical.query.filter_by(
                            metabolite_name=result["metabolite_name"],
                            formula=result["formula"],
                        ).first()
                        if current_chemical is not None:
                            overwritten = True
                            for k in result:
                                setattr(current_chemical, k, result[k])
                            overwritten_chemicals.append(current_chemical)
                    if not overwritten:
                        db.session.add(Chemical(**result, person_id=user.id))
                db.session.commit()
                cleanup()
                return render_template("batchadd.html", success=True, overwritten_chemicals=overwritten_chemicals)
    else:
        return render_template("batchadd.html")


# regular users can batch search.
@app.route("/chemical/batch", methods=["GET", "POST"])
def batch_query_request():
    if not session.get('user'):
        abort(403)
    if request.method == "POST":
        if "input" not in request.files or request.files["input"].filename == '':
            return render_template("batchadd.html", invalid="Blank file included")
        # save the file to RAM
        file = request.files["input"]
        os.makedirs("/tmp/walkerdb", exist_ok=True)
        filename = os.path.join("/tmp/walkerdb", str(uuid4()))
        file.save(filename)
        # perform cleanup regardless of what happens.
        def cleanup(): return os.remove(filename)
        # read it as a csv
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile, delimiter="\t")
            queries, error = validate.validate_query_csv_fields(reader)
            if error:
                cleanup()
                return render_template("batchquery.html", invalid=error)
            else:
                # generate the queries here.
                data = []
                for query in queries:
                    mz_filter = and_(query["mz_max"] > Chemical.final_mz,
                                     Chemical.final_mz > query["mz_min"])
                    rt_filter = and_(query["rt_max"] > Chemical.final_rt,
                                     Chemical.final_rt > query["rt_min"])
                    mode_filter = Chemical.mode == query["mode"]
                    # date_filter = query["date"] >= Chemical.createdAt
                    result = Chemical.query.filter(
                        and_(mz_filter, rt_filter, mode_filter)
                        if len(query["mode"]) != 0
                        else and_(mz_filter, rt_filter)
                    ).limit(5).all()
                    hits = []
                    for x in result:
                        hits.append({"url": url_for("chemical_view", id=x.id),
                                     "name": x.metabolite_name, "mz": x.final_mz, "rt": x.final_rt, "final_adduct": x.final_adduct})
                    data.append(dict(
                        query=query,
                        hits=hits,
                    ))
                cleanup()
                return render_template("batchquery.html", success=True, data=data)
    return render_template("batchquery.html")


@app.route("/search")
def search():
    return render_template("search.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
