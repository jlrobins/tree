from os import environ as env
from functools import wraps
from flask import Flask
from flask_socketio import SocketIO, emit


from jlr.db import configure_flask_socketio
import factory_model


app = Flask(__name__)
app.config.from_object(__name__)

socketio = SocketIO(app)

db_config = 'dbname=%s user=%s host=%s' % (
                    env['DBNAME'], env['DBUSER'], env['DBHOST'])

connection_manager = configure_flask_socketio(db_config, register_types=False)


# decorator to catch exceptions and report back to client.
def exceptions_to_error_emit(func):
    @wraps(func)
    def doit(*args):
        try:
            func(*args)
        except Exception as e:
            print(e)
            emit('serverside-error', {
                    'message': 'Sorry! A server-side error happened!'})

    return doit


@socketio.on('connect')
@connection_manager.with_transaction
def new_connection(con):
    # Return all factories in a list ordered by id
    emit('factories', {'factories': [
         f._asdict() for f in factory_model.all_factories(con)]})


@socketio.on('create_factory')
@exceptions_to_error_emit
@connection_manager.with_transaction
def create_factory(con, data):

    # data: {name, min, max, number_count (count of children to create)}
    # generates children
    # stores it
    # broadcasts it

    name, min_num, max_num, number_count = (
                            data.get('name'), data.get('min_value'),
                            data.get('max_value'), data.get('number_count'))

    if complain_about_factory_params(name, min_num, max_num, number_count):
        return

    new_factory = factory_model.create_factory(con, name, min_num,
                                               max_num, number_count)

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
    # regenerates children if change to min/max/number count
    # broadcasts it
    f_id, new_name, new_low, new_high, number_count = (
                        data.get('id'), data.get('name'),
                        data.get('min_value'), data.get('max_value'),
                        data.get('number_count'))

    if type(f_id) is not int:
        reply_error('Expected an int')

    if complain_about_factory_params(new_name, new_low,
                                     new_high, number_count):
        return

    updated_factory = factory_model.update_factory(con, f_id,
                                                   new_name, new_low,
                                                   new_high, number_count)

    emit('factory_updated', {'factory': updated_factory}, broadcast=True)


###
# Utilities here down, plus __main__ hook.
###


def reply_error(msg):
    emit('serverside-error', {'message': msg})
    print('reply_error: ' + msg)


def complain_about_factory_params(name, min_num, max_num, number_count):
    if type(name) != str or type(min_num) != int \
            or type(max_num) != int or type(number_count) != int:

        reply_error('Bad Parameter Types: %s(%s) %s(%s) %s(%s) %s(%s)' %
                    (name, type(name), min_num, type(min_num), max_num,
                     type(max_num), number_count, type(number_count)))

        return True  # did indeed complain

    if not name:
        reply_error('Name empty!')
        return True

    if len(name) >= 256:
        reply_error('Name too long (max 256 characters)')
        return True

    if min_num < 0 or min_num > 1000:
        reply_error('Lower bound out of bounds (0..1000)')
        return True

    if max_num < 0 or max_num > 1000 or max_num <= min_num:
        reply_error('Upper bound out of bounds (0..1000)')
        return True

    if number_count < 1 or number_count > 15:
        reply_error('Number count out of bounds (1..15)')

    # no complaint ...
    return False

if __name__ == '__main__':
    socketio.run(app)
