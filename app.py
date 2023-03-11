#!/usr/bin/env python3

from datetime import date
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
from validate import validate_insertion_csv_fields, validate_query_csv_fields

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.secret_key = '98d31240f9fbe14c8083586db49c19c3a8d3f726'

db: SQLAlchemy = SQLAlchemy(app)
migrate = Migrate(app, db)

BaseModelForm = model_form_factory(FlaskForm)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


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
        if "admin" not in session:
            return redirect(url_for("admin_login"))
        else:
            return None


def object_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


class Chemical(db.Model):
    query: db.Query
    id = db.Column(db.Integer, primary_key=True)
    # all fields after here are included in the database
    chemical_db_id = db.Column(db.String)
    library = db.Column(db.String)
    # important fields
    name = db.Column(db.String, nullable=False)
    formula = db.Column(db.String, nullable=False)
    mass = db.Column(db.Float, nullable=False)

    pubchem_cid = db.Column(db.Integer)
    pubmed_refcount = db.Column(db.Integer)
    standard_class = db.Column(db.String)
    inchikey = db.Column(db.String)
    inchikey14 = db.Column(db.String)

    final_mz = db.Column(db.Float, nullable=False)
    final_rt = db.Column(db.Float, nullable=False)

    final_adduct = db.Column(db.String)
    adduct = db.Column(db.String)
    detected_adducts = db.Column(db.String)
    adduct_calc_mz = db.Column(db.String)
    msms_detected = db.Column(db.Boolean)
    msms_purity = db.Column(db.Float)

    # serialized into datetime.date
    createdAt = db.Column(db.Date)


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
        username, pw = request.form.get(
            'username'), request.form.get('password')
        if username is None or pw is None:
            return render_template("register.html", fail="Invalid Input.")
        elif db.session.execute(db.select(Admin).filter_by(username=username)).fetchone():
            return render_template("register.html", fail="Username already exists.")
        else:
            db.session.add(
                Admin(username=username, password=Admin.generate_password(pw)))
            db.session.commit()
            return render_template("register.html", success=True)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username, pw = request.form.get(
            'username', ''), request.form.get('password', '')
        if Admin.authenticate(username, pw):
            return render_template("login.html", success=True)
        else:
            return render_template("login.html", fail="Could not authenticate.")
    else:
        return render_template("login.html")


@app.route('/admin/logout', methods=['GET'])
def admin_logout():
    if "admin" in session:
        session.pop('admin')
    return redirect(url_for('home'))


@app.route("/")
def home():
    if Admin.exists():
        return render_template("index.html")
    else:
        return redirect(url_for("admin_create"))

# Routes for CRUD operations on chemicals


@app.route("/chemical/create", methods=['GET', 'POST'])
def chemical_create():
    if not session.get('admin'):
        abort(403)
    if request.method == "POST":
        form = ChemicalForm(**request.form)
        if form.validate():
            new_chemical = Chemical(**form.data)
            db.session.add(new_chemical)
            db.session.commit()
            return render_template("create_chemical.html", form=ChemicalForm(), success=True)
        else:
            return render_template("create_chemical.html", form=form, invalid=True), 400
    else:
        form = ChemicalForm()
        return render_template("create_chemical.html", form=form)


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
                    "name": x.name, "mz": x.final_mz, "rt": x.final_rt})
    return jsonify(data)


# Utilities for doing add and search operations in batch
# no file over 3MB is allowed.
app.config['MAX_CONTENT_LENGTH'] = 3 * 1000 * 1000


@app.route("/chemical/batchadd", methods=["GET", "POST"])
def batch_add_request():
    if not session.get('admin'):
        abort(403)
    if request.method == "POST":
        if "csv" not in request.files or request.files["csv"].filename == '':
            return render_template("batchadd.html", invalid="Blank file included")
        # save the file to RAM
        file = request.files["csv"]
        os.makedirs("/tmp/walkerdb", exist_ok=True)
        filename = os.path.join("/tmp/walkerdb", str(uuid4()))
        file.save(filename)
        # perform cleanup regardless of what happens.
        def cleanup(): return os.remove(filename)
        # read it as a csv
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            results, error = validate_insertion_csv_fields(reader)
            if error:
                cleanup()
                return render_template("batchadd.html", invalid=error)
            else:
                chemicals = [Chemical(**result) for result in results]
                db.session.add_all(chemicals)
                db.session.commit()
                cleanup()
                return render_template("batchadd.html", success=True)
    else:
        return render_template("batchadd.html")


@app.route("/chemical/batch", methods=["GET", "POST"])
def batch_query_request():
    if not session.get('admin'):
        abort(403)
    if request.method == "POST":
        if "csv" not in request.files or request.files["csv"].filename == '':
            return render_template("batchadd.html", invalid="Blank file included")
        # save the file to RAM
        file = request.files["csv"]
        os.makedirs("/tmp/walkerdb", exist_ok=True)
        filename = os.path.join("/tmp/walkerdb", str(uuid4()))
        file.save(filename)
        # perform cleanup regardless of what happens.
        def cleanup(): return os.remove(filename)
        # read it as a csv
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            queries, error = validate_query_csv_fields(reader)
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
                    # date_filter = query["date"] >= Chemical.createdAt
                    result = Chemical.query.filter(
                        and_(mz_filter, rt_filter)
                    ).limit(5).all()
                    hits = []
                    for x in result:
                        hits.append({"url": url_for("chemical_view", id=x.id),
                                    "name": x.name, "mz": x.final_mz, "rt": x.final_rt})
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
