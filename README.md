# Passport Inc.'s 'tree' challenge

## James Robinson


Implemented using react.js for UI and python/flask-socketio for the websocket server.

Deployed on a free-tier ec2 node with rds PostgreSQL as datastore,
with an unused project domain name [jurisolver.com](http://jurisolver.com/).

## Production Topology
http -> ec2 node answered by haproxy reverse proxy on :80 to either apache (static content) or flask (websocket). Flask then talks through to RDS postgres instance.

## Devel Topology
http -> localhost answered by haproxy reverse proxy on :8000 to either node / flask devel server or flask (/socketio websocket). Flask then talks through to postgresql on localhost.



Contents:
  * [sql](sql/): annotated database schema and user permissioning. Ran from a PG superuser account.
  * [bin](bin/): development-side scripts
  * [deploy_bin](deploy_bin/): production-side scripts
  * [etc](etc/): configuration files (haproxy configs, python virtualenv conf)
  * [flask](flask/): python code specific to this project, plus also [jlr/](../jlr/) sub-reposistory for some of my utility code. If checking out remotely, be sure to do a recursive checkout.
  * [html](html/): edited results from `create-react-app`.

Enjoy!

