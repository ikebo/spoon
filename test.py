# coding: utf8

from spoon import Spoon

app = Spoon()


@app.route('/', methods=['GET'])
def index():
    return "Hello, Index!"


@app.route('/spoon', methods=['POST', 'GET'])
def spoon():
    return 'Hello, Spoon!'


app.run(
    'localhost',
    5000,
    debug=True
)
