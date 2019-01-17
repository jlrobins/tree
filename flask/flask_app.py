from flask import Flask, g, jsonify, request
from flask_socketio import SocketIO, send, emit
from os import environ as env
from functools import wraps

import jlr.db as db
import factory_model


APPLICATION_ROOT = '/api'

app = Flask(__name__)
app.config.from_object(__name__)

socketio = SocketIO(app)

db_config = 'dbname=%s user=%s host=%s' % (env['DBNAME'], env['DBUSER'], env['DBHOST'])

connection_manager = db.configure_flask_socketio(db_config, register_types=False)

connections = 0


def exceptions_to_error_emit(func):
    @wraps(func)
    def doit(*args):
        try:
            func(*args)
        except Exception as e:
            print(e)
            emit('serverside-error', {'message': 'Sorry! A server-side error happened!'})

    return doit


@socketio.on('connect') # namespace='/chat'
@connection_manager.with_transaction
def new_connection(con):
    global connections
    connections += 1

    # Broadcast new connection count.
    emit('online_count', {'online_count' : connections}, broadcast=True)

    # Return all factories in a list ordered by id
    emit('factories', {'factories': [ f._asdict() for f in factory_model.all_factories(con)]})


@socketio.on('disconnect')
def closed_connection():
    global connections
    connections -= 1

    # Broadcast new connection count.
    emit('online_count', {'online_count' : connections}, broadcast=True)

def reply_error(msg):
    emit('serverside-error', {'message': msg})
    print('reply_error: ' + msg)


def complain_about_factory_params(name, min_num, max_num):
    if type(name) != str or type(min_num) != int or type(max_num) != int:
        reply_error('Bad Parameter Types: %s(%s) %s(%s) %s(%s)' % (name, type(name), min_num, type(min_num), max_num, type(max_num)))
        return True # did indeed complain

    if len(name) >= 256:
        reply_error('Name too long')
        return True

    if min_num < 0 or min_num > 1000:
        reply_error('Lower bound out of bounds')
        return True

    if max_num < 0 or max_num > 1000 or max_num <= min_num:
        reply_error('Upper bound out of bounds')
        return True

    # no complaint ...
    return False


@socketio.on('create_factory')
@exceptions_to_error_emit
@connection_manager.with_transaction
def create_factory(con, data):

    # data: {name, min, max}
    # generates children
    # stores it
    # broadcasts it

    name, min_num, max_num = data.get('name'), data.get('min_value'), data.get('max_value')

    if complain_about_factory_params(name, min_num, max_num):
        return

    new_factory = factory_model.create_factory(con, name, min_num, max_num)
    emit('new_factory', {'factory': new_factory}, broadcast=True)


@socketio.on('delete_factory')
@exceptions_to_error_emit
@connection_manager.with_transaction
def delete_factory(con, data):
    # deletes it
    # broadcasts deletion event.
    f_id = data.get('id')
    if type(f_id) is not int:
        reply_error('Expected an int')
        return

    factory_model.delete_factory(con, f_id)
    emit('factory_deleted', {'id': f_id}, broadcast=True)

@socketio.on('edit_factory')
@exceptions_to_error_emit
@connection_manager.with_transaction
def edit_factory(con, data):
    # edits it
    # regenerates children if change to min/max
    # broadcasts it
    f_id, new_name, new_low, new_high = (data.get('id'), data.get('name'),
                                            data.get('min_value'), data.get('max_value'))

    if type(f_id) is not int:
        reply_error('Expected an int')

    if complain_about_factory_params(new_name, new_low, new_high):
        return

    updated_factory = factory_model.update_factory(con, f_id, new_name, new_low, new_high)
    emit('factory_updated', {'factory': updated_factory}, broadcast=True)


if __name__ == '__main__':
    socketio.run(app)
