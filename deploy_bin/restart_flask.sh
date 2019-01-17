#!/bin/bash


set -e
cd

if [ -f /tmp/flask.pid ]; then
	kill `cat /tmp/flask.pid`
fi

if [ -f /tmp/flask_log ]; then
	rm -f /tmp/flask_log
fi


. flask_env/bin/activate

cd deploy/flask
export FLASK_APP=flask_app

export DBNAME='tree_db'
export DBUSER='treemaster'
export DBHOST='treedb.clzcbbduzin7.us-east-2.rds.amazonaws.com'

flask run --host=0.0.0.0 >& /tmp/flask_log < /dev/null &
echo $! > /tmp/flask.pid
