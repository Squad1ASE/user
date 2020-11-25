import connexion, logging, database
from database import User, Quarantine
from flask import jsonify
from celery import Celery
import requests
from api_call import RESERVATION_contact_tracing

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

def make_celery(application):
    celery = Celery(
        application.import_name,
        #broker=os.environ['CELERY_BROKER_URL'],
        #backend=os.environ['CELERY_BACKEND_URL']
        backend='redis://localhost:6379',
        broker='redis://localhost:6379'
    )
    celery.conf.update(application.config)
    celery.conf.beat_schedule = {
        'del_inactive_users': 
        {
        'task': 'app.del_inactive_users',
        'schedule': 30.0
        },
        'launch_contact_tracing': 
        {
        'task': 'app.launch_contact_tracing',
        'schedule': 30.0
        }

    }

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with application.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(application)

# TODO chiamata a reservation, basta che passo booker_id, start_date e end_date per i 14 giorni
@celery.task
def del_inactive_users():

    users_to_delete = database.db_session.query(User).filter(
        User.is_active == False,
        User.firstname != 'Anonymous').all()

    for user in users_to_delete:
        # TODO contatta servizio RESERVATION per cancellare prenotazioni, questo solo se fatto in automatico
        # TODO contatta servizio RESTAURANT per cancellare ristoranti
        # if condizioni di prima soddisfatte: (spostare di un tab)

        # after 14 days from its last computed reservation  
        inobservation = database.db_session.query(Quarantine).filter(
            Quarantine.user_id == user.id,
            Quarantine.in_observation == True).first()

        if inobservation is None:
            # TODO verifica che non ci siano prenotazioni negli ultimi 14 giorni
            user.email = 'invalid_email' + str(user.id) + '@a.b'
            user.phone = 0
            user.firstname = 'Anonymous'
            user.lastname = 'Anonymous'
            user.password = 'anonymouspassword'
            user.dateofbirth = None 
            database.db_session.commit()

@celery.task
def launch_contact_tracing():

    quarantine_users_no_contact = database.db_session.query(Quarantine).filter(
        Quarantine.contact_tracing_done == False).all()

    for user in quarantine_users_no_contact:
        # TODO check if this is a post, get ecc
        # reply = RESERVATION_contact_tracing(user.email)
        user.contact_tracing_done = True
    
    database.db_session.commit()

if __name__ == '__main__':
    app.run(port=5060)