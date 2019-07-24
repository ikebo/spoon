# coding: utf8

import sys
import os
from datetime import datetime

sys.path[0] = os.path.abspath('../../')

from spoon import Spoon
from spoon import request
from spoon import render_template
from spoon import session

app = Spoon(__name__)
app.secret_key = "spoon"


def add(a, b):
    return a + b


def date_format(date_str):
    do = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    return do.strftime('%b %d, %Y')


app.jinja_env.globals.update(add=add, date_format=date_format)

import sys


@app.route('/', methods=['GET'])
def index():
    # session["username"] = "Joe"
    session["username"] = 'Joe'
    return render_template("index.html")


def print_request(rq):
    for index, item in enumerate(rq):
        sys.stdout.write('%s, ' % item)
        if index % 7 == 0:
            print '\n'


@app.route('/spoon/<int:spoon_id>', methods=['POST', 'GET'])
def spoon(spoon_id):
    print("method: ", request.method)
    print("headers: ", request.headers)
    return 'Hello, Spoon, NO.{}'.format(spoon_id)


@app.errorhandler(404)
def handle_404(e):
    return 'not found', 404


@app.errorhandler(500)
def handle_500(e):
    return 'server internel error', 500


app.run(
    'localhost',
    5000,
    debug=True
)
