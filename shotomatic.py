# -*- coding: utf-8 -*-
"""
    Shot-O-matic
    ~~~~~~

    A simple screenshot upload/showcase website,
    using the Flask microframework (http://flask.pocoo.org).

    :copyright: (c) 2010 by Aljoscha Krettek.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

import os
import shutil
import glob
import sqlite3
from contextlib import closing
# for our decorators
from functools import wraps 

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, send_file
from werkzeug import SharedDataMiddleware
from werkzeug import secure_filename
from werkzeug import generate_password_hash, check_password_hash
from werkzeug.contrib.sessions import FilesystemSessionStore

# configuration
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.debug = config.DEBUG


################################################################################
# DB stuff
def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(config.DATABASE)

def query_db(query, args=(), one=False, db=None):
    if db is None:
        db = g.db
    cur = db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

def user_exists(name):
    user = query_db('select * from users where name=?', [name], one=True)
    if user is None:
        return False
    else:
        return True

def _create_user(name, password, admin=False, db=None):
    if db is None:
        db = g.db

    db.execute('insert into users VALUES(?, ?, ?, NULL)',
               [name, generate_password_hash(password),admin])
    user = query_db("select * from users where name=?", [name], one=True,
                                                                db=db)
    screenshots_dir = user['name']
    abs_path = os.path.join(config.SCREENSHOTS_DIR, screenshots_dir)
    if not os.path.exists(abs_path):
        os.mkdir(abs_path)
    db.execute("update users set screenshots_dir = ? where name=?",
               [screenshots_dir, name])
    db.commit()

def _delete_user(name, db=None):
    if db is None:
        db = g.db

    user = query_db("select * from users where name=?", [name], one=True,
                                                                db=db)
    if user is None:
        return

    abs_path = os.path.join(config.SCREENSHOTS_DIR, user['screenshots_dir'])
    if os.path.exists(abs_path):
        shutil.rmtree(abs_path)

    db.execute('delete from users where name=?', [name])
    db.commit()


def init_db():
    """Creates the database tables."""
    print "Creating database in '{0}'".format(config.DATABASE)
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        _create_user(config.DEFAULT_USERNAME,
                    config.DEFAULT_PASSWORD,
                    admin=True,
                    db=db)


################################################################################
# Per request stuff
@app.before_request
def before_request():
    """
    Make sure we are connected to the database each request and also
    do the session handling.
    
    """
    g.db = connect_db()
    session_store = FilesystemSessionStore(config.SESSIONS_DIR)
    if 'sid' in session:
        sid = session.get('sid')
        g.session = session_store.get(sid)
        if 'user' in g.session:
            g.user = g.session['user']
        else:
            g.user = None
    else:
        g.session = session_store.new()
        g.user = None

@app.after_request
def after_request(response):
    """
    Closes the database again at the end of the request and store the
    session if neccessary.
    
    """
    session_store = FilesystemSessionStore(config.SESSIONS_DIR)
    if g.session.should_save:
        session_store.save(g.session)
        session['sid'] = g.session.sid
        session.permanent = True
        # we have to do this because Flask
        # stores the SecureCookie containing the "Session"
        # before calling the "after_request" functions
        app.save_session(session, response)
    g.db.close()
    return response


################################################################################
# Decorators
def admin_required(message="Admin status required to acccess this section."):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None or not g.user['admin']:
                flash(message, 'error')
                return redirect(url_for('show_screenshots'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(message="You must be logged in to access this section."):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                # allow for direct file upload with client
                if (request.form.get('username', False) and
                        request.form.get('password', False)):
                    user = query_db('select * from users where name = ?',
                                    [request.form['username']],
                                    one=True)
                    if user and check_password_hash(user['password'],
                                                    request.form['password']):
                        g.user = user
                        return f(*args, **kwargs)
                flash(message, 'notice')
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


################################################################################
# Views
@app.route('/<user>')
@app.route('/')
def show_screenshots(user=None):
    users = glob.glob(os.path.join(config.SCREENSHOTS_DIR, '*'))
    users = [os.path.basename(name) for name in users]
    screenshots = []
    for user in users:
        user_shots = glob.glob(os.path.join(config.SCREENSHOTS_DIR, user, '*'))
        for user_shot in user_shots:
            screenshots.append((user, os.path.basename(user_shot)))
    screenshots.sort(reverse=True, cmp=lambda x,y: cmp(x[1], y[1]))
    show_all = request.args.get('all', 0)
    if show_all == 0:
        screenshots = screenshots[:10]
    return render_template('show_screenshots.html', screenshots=screenshots)

@app.route('/<user>/shot/<shot>')
def screenshot(user, shot):
    user = secure_filename(user)
    shot = secure_filename(shot)
    filename = os.path.join(config.SCREENSHOTS_DIR, user, shot)
    if not os.path.exists(filename):
        flash("User {0} has not uploaded {1}.".format(user, shot), 'error')
        return redirect(url_for('show_screenshots'))
    
    return send_file(filename)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST', 'GET'])
@login_required("You need to be logged in in order to upload screenshots.")
def upload_screenshot():
    if request.method == 'POST':
        file = request.files['screenshot']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(config.SCREENSHOTS_DIR,
                                   g.user['screenshots_dir'],
                                   filename))
            flash('Screenshot uploaded.', 'success')
            return redirect(url_for('show_screenshots'))
        else:
            flash('Uploads of this filetype not allowed.', 'error')
    return render_template('upload_screenshot.html')

@app.route('/<user>/delete/<shot>')
@login_required("You need to be logged in in order to delete screenshots.")
def delete_screenshot(user, shot):
    user = secure_filename(user)
    shot = secure_filename(shot)
    filename = os.path.join(config.SCREENSHOTS_DIR, user, shot)
    if not g.user['admin'] and user != g.user['name']:
        flash("You can only delete your own screenshots.", 'notice')
        return redirect(url_for('show_screenshots'))
    if not os.path.exists(filename):
        flash("Screenshot '{0}' does not exist.".format(shot), 'error')
        return redirect(url_for('show_screenshots'))
    os.remove(filename)
    flash('Screenshot removed.', 'success')
    return redirect(url_for('show_screenshots'))

@app.route('/users')
@login_required()
@admin_required()
def show_users():
    users = query_db('select * from users')
    return render_template('show_users.html', users=users) 

@app.route('/users/add', methods=['POST'])
@login_required()
@admin_required()
def add_user():
    _create_user(request.form['name'], request.form['password'])
    flash('User added.', 'success')
    return redirect(url_for('show_users'))

@app.route('/users/delete/<name>', methods=['POST', 'GET'])
@login_required()
@admin_required()
def delete_user(name):
    user = query_db('select * from users where name=?', [name])
    if len(user) <= 0:
        flash('User does not exist.', 'error')
    else:
        _delete_user(name)
        flash('User deleted.', 'success')
    return redirect(url_for('show_users'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = query_db('select * from users where name = ?',
                        [request.form['username']],
                        one=True)
        if user is None:
            error = 'Invalid username.'
        elif not check_password_hash(user['password'],request.form['password']):
            error = 'Invalid password.'
        else:
            g.session['user'] = user
            flash('You were logged in.', 'success')
            if 'next' in request.args:
                return redirect(request.args['next'])
            else:
                return redirect(url_for('show_screenshots'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('sid', None)
    flash('You were logged out.', 'success')
    return redirect(url_for('show_screenshots'))

if __name__ == '__main__':
    app.debug = True
    app.run()
