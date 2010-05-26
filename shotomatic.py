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

import os.path
import os
import glob
import sqlite3
from contextlib import closing

from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, send_file
from werkzeug import SharedDataMiddleware
from werkzeug import secure_filename
from werkzeug import generate_password_hash, check_password_hash

# configuration
import config
# create our little application :)
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.debug = config.DEBUG


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

@app.before_request
def before_request():
    """Make sure we are connected to the database each request."""
    g.db = connect_db()


@app.after_request
def after_request(response):
    """Closes the database again at the end of the request."""
    g.db.close()
    return response


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
def upload_screenshot():
    valid_credentials = False
    if not session.get('logged_in'):
        if (request.form.get('username', False) and
                request.form.get('password', False)):
            user = query_db('select * from users where name = ?',
                            [request.form['username']],
                            one=True)
            if user and request.form['password'] == user['password']:
                valid_credentials = True
    else:
        valid_credentials = True
    if not valid_credentials:
        flash('You need to be logged in in order to upload screenshots.')
        return redirect(url_for('show_screenshots'))
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
def delete_screenshot(shot):
    if not session.get('logged_in'):
        flash('You need to be logged in in order to delete screenshots.')
        return redirect(url_for('show_screenshots'))
    filename = os.path.join(config.SCREENSHOTS_DIR, shot)
    if not os.path.exists(filename):
        flash("Screenshot '{0}' does not exist".format(filename))
        return redirect(url_for('show_screenshots'))
    os.remove(filename)
    flash('Screenshot removed')
    return redirect(url_for('show_screenshots'))

@app.route('/users')
def show_users():
    if not session.get('logged_in'):
        flash('You need to be logged in for administrative functions.')
        return redirect(url_for('show_screenshots'))
    users = query_db('select * from users')
    return render_template('show_users.html', users=users) 

@app.route('/users/add', methods=['POST'])
def add_user():
    if not session.get('logged_in'):
        flash('You need to be logged in for administrative functions.')
        return redirect(url_for('show_screenshots'))
    query_db('insert into users values (NULL, ?, ?, ?)',
             [request.form['name'],
              generate_password_hash(request.form['password']),
              False])
    g.db.commit()
    flash('User added')
    return redirect(url_for('show_users'))

@app.route('/users/delete/<int:id>', methods=['POST', 'GET'])
def delete_user(id):
    if not session.get('logged_in'):
        flash('You need to be logged in for administrative functions.')
        return redirect(url_for('show_screenshots'))
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
            error = 'Invalid username'
        elif not check_password_hash(user['password'],request.form['password']):
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session.permanent = True
            flash('You were logged in')
            return redirect(url_for('show_screenshots'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_screenshots'))

if __name__ == '__main__':
    app.debug = True
    app.run()
