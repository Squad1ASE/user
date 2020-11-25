import connexion, logging, database
from database import User, Quarantine
from flask import jsonify
from celery import Celery
import requests


RESTAURANT_SERVICE = 'http://127.0.0.1:5070/'
RESERVATION_SERVICE = 'http://127.0.0.1:5100/'
REQUEST_TIMEOUT_SECONDS = 1

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

# TODO call to reservation, booker_id is enough, start_date and end_date 14 days
@celery.task
def del_inactive_users():

    users_to_delete = database.db_session.query(User).filter(
        User.is_active == False,
        User.firstname != 'Anonymous').all()

    for user in users_to_delete:

        if user.role == 'owner' and user.delete_user_restaurant is False:

            data = dict(owner_id=user.id)

            try:
                reply = requests.delete(RESTAURANT_SERVICE+'restaurants', json=data, timeout=REQUEST_TIMEOUT_SECONDS)

                if reply.status_code == 200:
                    user.delete_user_restaurant = True

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                print("RESTAURANT_SERVICE is not available Celery will handle the task later")
        elif user.role == 'customer' and user.delete_user_reservation is False:

            data = dict(user_id=user.id)

            try:
                reply = requests.delete(RESERVATION_SERVICE+'reservations', json=data, timeout=REQUEST_TIMEOUT_SECONDS)

                if reply.status_code == 200:
                    user.delete_user_reservation = True

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                print("RESERVATION_SERVICE is not available Celery will handle the task later")

        # after 14 days from its last computed reservation  
        inobservation = database.db_session.query(Quarantine).filter(
            Quarantine.user_id == user.id,
            Quarantine.in_observation == True).first()

        if inobservation is None and user.delete_user_restaurant is True and user.delete_user_reservation is True:
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

        data = dict(
            email=user.user_id,
            start_date=str(user.start_date.strftime("%d/%m/%Y"))
        )

        try:
            reply = requests.delete(RESERVATION_SERVICE+'reservations', json=data, timeout=REQUEST_TIMEOUT_SECONDS)

            if reply.status_code == 200:
                user.contact_tracing_done = True
                database.db_session.commit()

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print("RESERVATION_SERVICE is not available Celery will handle the task later")

    

if __name__ == '__main__':
    app.run(port=5060)