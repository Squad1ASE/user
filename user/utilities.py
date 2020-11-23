from database import User
import datetime
import requests

USER_SERVICE = "http://127.0.0.1:5060"

# --- UTILITIES USER ---
def insert_admin(db_session, app):
    with app.app_context():
        admin = db_session.query(User).filter_by(email='admin@admin.com').first()
        if admin is None:
            example = User()
            example.email = 'admin@admin.com'
            example.phone = '3333333333'
            example.firstname = 'Admin'
            example.lastname = 'Admin'
            example.set_password('admin')
            example.dateofbirth = datetime.date(2020, 10, 5)
            example.is_admin = True
            example.role = 'admin'
            db_session.add(example)
            db_session.commit()
'''
def insert_ha(db, app):
    with app.app_context():
        ha = db.session.query(User).filter_by(email='healthauthority@ha.com').first()
        if ha is None:
            example = User()
            example.email = 'healthauthority@ha.com'
            example.phone = '3333333333'
            example.firstname = 'ha'
            example.lastname = 'ha'
            example.set_password('ha')
            example.dateofbirth = datetime.date(2020, 10, 5)
            example.is_admin = True
            example.role = 'ha'
            db.session.add(example)
            db.session.commit()
'''
# customers
customers_example = [
    dict(
        email='userexample1@test.com',
        phone='39111111',
        firstname='firstname_test1',
        lastname='lastname_test1',
        password='password1',
        dateofbirth='05/10/2001',
        role='customer'
    ),
    dict(
        email='userexample2@test.com',
        phone='39222222',
        firstname='firstname_test2',
        lastname='lastname_test2',
        password='password2',
        dateofbirth='05/10/2002',
        role='customer'
    ),
    dict(
        email='userexample3@test.com',
        phone='39333333',
        firstname='firstname_test3',
        lastname='lastname_test3',
        password='password3',
        dateofbirth='05/10/2003',
        role='customer'
    ),
    dict(
        email='userexample4@test.com',
        phone='39444444',
        firstname='firstname_test4',
        lastname='lastname_test4',
        password='password4',
        dateofbirth='05/10/2004',
        role='customer'
    )
]       

# restaurant owner
restaurant_owner_example = [
    dict(
        email='restaurantowner1@test.com',
        phone='40111111',
        firstname='owner_firstname_test1',
        lastname='owner_lastname_test1',
        password='password1',
        dateofbirth='05/10/2001',
        role='owner'
    ),
    dict(
        email='restaurantowner2@test.com',
        phone='40222222',
        firstname='owner_firstname_test2',
        lastname='owner_lastname_test2',
        password='password2',
        dateofbirth='05/10/2002',
        role='owner'
    ),
    dict(
        email='restaurantowner3@test.com',
        phone='40333333',
        firstname='owner_firstname_test3',
        lastname='owner_lastname_test3',
        password='password3',
        dateofbirth='05/10/2003',
        role='owner'
    ),
    dict(
        email='restaurantowner4@test.com',
        phone='40444444',
        firstname='owner_firstname_test4',
        lastname='owner_lastname_test4',
        password='password4',
        dateofbirth='05/10/2004',
        role='owner'
    )
]       

# health authority
health_authority_example = dict(
    email='healthauthority@ha.com',
    phone='66666',
    firstname='Ha',
    lastname='Ha',
    password='ha',
    dateofbirth='05/10/2000',
    role='ha'
)
# admin 
admin_example = dict(
    email='badmin@admin.com',
    phone='666',
    firstname='badministrator_fn',
    lastname='badministrator_ln',
    password='badminpassw',
    dateofbirth='05/10/2001',
    role='admin'
)

########### NOTIFICATION ###########
notification_contact_with_positive_customer = dict(
    email=customers_example[0]['email'],
    notiftype="contact_with_positive",
    date="15/11/2020",
    role="customer"
)

notification_contact_with_positive_owner = dict(
    email=restaurant_owner_example[0]['email'],
    notiftype="contact_with_positive",
    date="15/11/2020",
    role="owner"
)

notification_reservation_canceled_owner = dict(
    email=restaurant_owner_example[0]['email'],
    notiftype="reservation_canceled",
    date="16/11/2020",
    role="owner",
    tablename="table X",
    reservationdate="20/11/2020"
)

notification_reservation_with_positive_owner = dict(
    email=restaurant_owner_example[0]['email'],
    notiftype="reservation_with_positive",
    date="16/11/2020",
    role="owner",
    tablename="table X",
    reservationdate="20/11/2020",
    restaurantname="Restaurant Y",
    bookeremail=customers_example[0]['email'],
    bookerphone=customers_example[0]['phone']
)

def create_user_EP(
        test_client, email=customers_example[0]['email'], phone=customers_example[0]['phone'],firstname=customers_example[0]['firstname'], 
        lastname=customers_example[0]['lastname'], password=customers_example[0]['password'], dateofbirth=customers_example[0]['dateofbirth'],
        role=customers_example[0]['role']
    ):
    data = dict(
        email=email,
        phone=phone,
        firstname=firstname,
        lastname=lastname,
        password=password,
        dateofbirth=dateofbirth,
        role=role
    )
    return test_client.put('/users', json=data, follow_redirects=True)


def user_login_EP(test_client, email=customers_example[0]['email'], password=customers_example[0]['password']):
    data = dict(
        email=email,
        password=password
    )
    return test_client.post('/login', json=data, follow_redirects=True)

def edit_user_EP(
    test_client, current_user_email, user_new_phone, current_user_old_password, current_user_new_password
):
    data = dict(
        current_user_email=current_user_email,
        user_new_phone=user_new_phone,
        current_user_old_password=current_user_old_password,
        current_user_new_password=current_user_new_password
    )
    return test_client.post('/users', json=data, follow_redirects=True)

def get_users_EP(test_client, email):

    if email == "":
        return test_client.get('/users')

    return test_client.get('/users?email='+email)

def get_user_by_ID_EP(test_client, ID):

    return test_client.get('/users/'+str(ID))

def get_patient_EP(test_client, email):

    return test_client.get('/patient?email='+email)


def mark_patient_EP(test_client, email):

    return test_client.put('/patient?email='+email)

def set_notification_EP(test_client, notificationslist):

    return test_client.put('/notification', json=notificationslist)

def delete_user_EP(test_client, current_user_email):
    
    data = dict(current_user_email=current_user_email)

    return test_client.delete('/users', json=data)