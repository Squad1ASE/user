import connexion, logging, database
from flask import jsonify


logging.basicConfig(level=logging.INFO)
database.init_db()
app = connexion.App(__name__, specification_dir='static/')
app.add_api('swagger.yml')

# set the WSGI application callable to allow using uWSGI:
# uwsgi --http :8080 -w app
application = app.app

@application.teardown_appcontext
def shutdown_session(exception=None):
    database.db_session.remove()


if __name__ == '__main__':
    app.run(port=5060)