import connexion, logging, database
from flask import jsonify
from celery import Celery

def create_app():
    logging.basicConfig(level=logging.INFO)
    app = connexion.App(__name__, specification_dir='static/')
    app.add_api('swagger.yml')
    database.init_db()
    return app
# set the WSGI application callable to allow using uWSGI:
# uwsgi --http :8080 -w app
app = create_app()
application = app.app

@application.teardown_appcontext
def shutdown_session(exception=None):
    database.db_session.remove()


if __name__ == '__main__':
    app.run(port=5060)

def make_celery(app):
    celery = Celery(
        app.import_name,
        #broker=os.environ['CELERY_BROKER_URL'],
        #backend=os.environ['CELERY_BACKEND_URL']
        backend='redis://localhost:6379',
        broker='redis://localhost:6379'
    )
    celery.conf.update(app.config)
    celery.conf.beat_schedule = {'test': {
        'task': 'print_hello',
        'schedule': 10.0
    }

    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)


@celery.task
def print_hello():
    print('Hello from Celery!')