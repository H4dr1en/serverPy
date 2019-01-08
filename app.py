from flask import Flask
from flask import jsonify
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/checkAuth')
def checkAuth():
    return jsonify(isAuthValid=True)