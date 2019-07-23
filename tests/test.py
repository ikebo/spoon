# coding: utf8

from spoon import Spoon
from spoon import request
from spoon import _request_ctx_stack

app = Spoon()

import sys


@app.route('/', methods=['GET'])
def index():
    1/0
    return "Hello, Index!"


def print_request(rq):
    for index, item in enumerate(rq):
        sys.stdout.write('%s, ' % item)
        if index % 7 == 0:
            print '\n'


@app.route('/spoon/<int:spoon_id>', methods=['POST', 'GET'])
def spoon(spoon_id):
    print("method: ", request.method)
    print(dir(request))
    print_request(dir(request))
    print("ctx: ", dir(_request_ctx_stack.top.request))
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
