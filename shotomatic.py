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

def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

def init_db():
    """Creates the database tables."""
    print "Creating database in '{0}'".format(config.DATABASE)
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.execute('insert into users VALUES(NULL, ?, ?, ?)',
                   [config.DEFAULT_USERNAME,
                    generate_password_hash(config.DEFAULT_PASSWORD),
                    True])
        db.commit()

################################################################################
# Decorators
def admin_required(message="Admin status required to acccess this section."):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None or not g.user['admin']:
                flash(message)
                return redirect(url_for('show_screenshots'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def login_required(message="You must be logged in to access this section."):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                flash(message)
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

################################################################################
# Per request stuff
@app.before_request
def before_request():
    """Make sure we are connected to the database each request."""
    g.db = connect_db()
    if 'user_id' in session:
        user_id = session.get('user_id')
        user = query_db('select * from users where id = ?', [user_id], one=True)
        if user:
            g.user = user
        else:
            g.user = None
    else:
        g.user = None

@app.after_request
def after_request(response):
    """Closes the database again at the end of the request."""
    g.db.close()
    return response

################################################################################
# Views
@app.route('/')
def show_screenshots():
    screenshots = glob.glob(config.SCREENSHOTS_DIR + '/*')
    screenshots = [os.path.basename(name) for name in screenshots]
    screenshots.sort(reverse=True)
    show_all = request.args.get('all', 0)
    if show_all == 0:
        screenshots = screenshots[:10]
        
    return render_template('show_screenshots.html', screenshots=screenshots)

@app.route('/shot/<shot>')
def screenshot(shot):
    shot = secure_filename(shot)
    filename = os.path.join(config.SCREENSHOTS_DIR, shot)
    if not os.path.exists(filename):
        flash("Screenshot '{0}' does not exist".format(filename))
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
            file.save(os.path.join(config.SCREENSHOTS_DIR, filename))
            flash('Screenshot uploaded.')
            return redirect(url_for('show_screenshots'))
        else:
            flash('Uploads of this filetype not allowed.')
    return render_template('upload_screenshot.html')

@app.route('/delete/<shot>')
@login_required("You need to be logged in in order to delete screenshots.")
def delete_screenshot(shot):
    filename = os.path.join(config.SCREENSHOTS_DIR, shot)
    if not os.path.exists(filename):
        flash("Screenshot '{0}' does not exist".format(filename))
        return redirect(url_for('show_screenshots'))
    os.remove(filename)
    flash('Screenshot removed')
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
    query_db('insert into users values (NULL, ?, ?, ?)',
             [request.form['name'],
              generate_password_hash(request.form['password']),
              False])
    g.db.commit()
    flash('User added')
    return redirect(url_for('show_users'))

@app.route('/users/delete/<int:id>', methods=['POST', 'GET'])
@login_required()
@admin_required()
def delete_user(id):
    user = query_db('select * from users where id=?', [id])
    if len(user) <= 0:
        flash('User does not exist')
    else:
        query_db('delete from users where id=?', [id])
        g.db.commit()
        flash('User deleted')
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
            session['user_id'] = user['id']
            session.permanent = True
            flash('You were logged in.')
            if 'next' in request.args:
                return redirect(request.args['next'])
            else:
                return redirect(url_for('show_screenshots'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You were logged out.')
    return redirect(url_for('show_screenshots'))

if __name__ == '__main__':
    app.debug = True
    app.run()
