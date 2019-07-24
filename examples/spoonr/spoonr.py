# -*- coding: utf-8 -*-
"""
    Spoonr
    ~~~~~~

    A microblog example application written as Spoon tutorial with
    Spoon and sqlite3.

    Ctrl + C & Ctrl + V from Flaskr in examples of Flask :)
"""


from __future__ import with_statement
import sqlite3
from contextlib import closing

import sys
import os
sys.path[0] = os.path.abspath('../../')

from spoon import Spoon, request, session, g, redirect, url_for, abort, \
     render_template, flash

# configuration
DATABASE = os.path.abspath('./tmp/spoonr.db')
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Spoon(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG


def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(DATABASE)


def init_db():
    """Creates the database tables."""
    with (connect_db()) as db:
        with open('./schema.sql') as f:
            db.cursor().executescript(f.read())
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
def show_entries():
    cur = g.db.execute('select title, text from entries order by id desc')
    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    title = request.form['title']
    text = request.form['text']
    if not title or not text:
        flash('title and text is required!')
        return redirect(url_for('show_entries'))

    g.db.execute('insert into entries (title, text) values (?, ?)',
                 [request.form['title'], request.form['text']])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/login',  methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != USERNAME:
            error = 'Invalid username'
        elif request.form['password'] != PASSWORD:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run(debug=True)
