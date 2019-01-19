from flask import Flask, jsonify, request
import requests
from celery import Celery
import processing as proc
import json

SERVER_GO_URL = 'http://servergo:3030'
SERVER_DB_URL = 'http://serverdb:3031'

app = Flask(__name__)
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379',
    CELERY_RESULT_BACKEND='redis://redis:6379'
)


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)


@celery.task(bind=True)
def start_process(self, req):

    self.update_state(state='PROGRESS', meta={
        "client": req['uid']
    })

    user = getUserSignatures(req['uid'])

    meta = { "client": req['uid'] }

    if(user is None):
        meta = {
            "client": req['uid'],
            "output" : 'FAILURE',
            "isAuthValid" : False,
            "msg" : "invalid user id"
        }

    else:

        try:
            meta["isAuthValid"] = proc.process(req, user)
        except:
            meta = {
                "client": req['uid'],
                "output" : 'FAILURE',
                "isAuthValid" : False,
                "msg" : "Error while computing values",
            }

    try:
        requests.post(f'{SERVER_GO_URL}/authAnswer', data=json.dumps({
            "client": req['uid'],
            "isAuthValid": meta["isAuthValid"]
        }), headers={'Content-Type': 'application/json'})

    except:
        meta = {
            "client": req['uid'],
            "output" : 'FAILURE',
            "isAuthValid": False,
            "msg": "communication with auth server failed"
        }

    finally:
        return meta


@app.route('/checkAuth', methods=['POST'])
def checkAuth():

    req = request.get_json()

    for attr in ["uid", "abs", "ord", "time"]:
        if attr not in req.keys():
            return 

    async_task = start_process.delay(req)

    return jsonify({"taskid":async_task.id})


@app.route('/status/<task_id>', methods=['GET'])
def checkStatus(task_id):

    task = start_process.AsyncResult(task_id)

    if task.info.get('output', '') != 'FAILURE':
        response = {
            'state': 'SUCCESS',
            'client': task.info.get('client')
        }
        
        if 'isAuthValid' in task.info:
            response['isAuthValid'] = task.info.get('isAuthValid', False)
    else: 
        # something went wrong in the background job
        response = {
            'state': 'FAILURE',     
            'client': task.info.get('client'),
            'msg': task.info.get('msg', ''),
            'isAuthValid': False
        }
    return jsonify(response)


def getUserSignatures(uid):

    res = requests.get(f'{SERVER_DB_URL}/user/id/{uid}')
    return res.json()[0]["signatures"]


if __name__ == '__main__':
    app.debug = True
    app.run()


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
