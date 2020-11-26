from conftest import test_app
from database import db_session, User
from sqlalchemy import exc
from datetime import datetime, timedelta
from utilities import customers_example, restaurant_owner_example
from utilities import create_user_EP, user_login_EP, edit_user_EP, get_users_EP, get_user_by_ID_EP, wrong_edit_user_EP
from utilities import get_patient_EP, insert_admin, mark_patient_EP, delete_user_EP
from utilities import notification_contact_with_positive_customer
from utilities import notification_contact_with_positive_owner
from utilities import notification_reservation_canceled_owner
from utilities import notification_reservation_with_positive_owner
from utilities import set_notification_EP
from werkzeug.security import generate_password_hash, check_password_hash
from unittest import mock
from unittest.mock import patch
from app import launch_contact_tracing, del_inactive_users


def test_create(test_app):
    app, test_client = test_app
    
    customer = customers_example[0]

    user = User()
    user.email = customer['email']
    user.phone = customer['phone']
    user.firstname = customer['firstname']
    user.lastname = customer['lastname']
    user.set_password(customer['password'])
    user.dateofbirth = datetime.strptime(customer['dateofbirth'], "%d/%m/%Y")
    user.role = customer['role']

    db_session.add(user)
    db_session.commit()

    getuser = db_session.query(User).filter(User.email == customer['email']).first()
    assert getuser is not None
    assert getuser.email == customer['email']
    assert getuser.phone == customer['phone']
    assert getuser.firstname == customer['firstname']
    assert getuser.lastname == customer['lastname']
    assert getuser.authenticate(customer['password']) is True
    assert getuser.dateofbirth == datetime.strptime(customer['dateofbirth'], "%d/%m/%Y").date()
    assert getuser.role == customer['role']

    duplicate_user = User()
    duplicate_user.email = customer['email']
    duplicate_user.phone = customer['phone']
    duplicate_user.firstname = customer['firstname']
    duplicate_user.lastname = customer['lastname']
    duplicate_user.set_password(customer['password'])
    duplicate_user.dateofbirth = datetime.strptime(customer['dateofbirth'], "%d/%m/%Y")
    duplicate_user.role = customer['role']

    # creation of a user with an already existing email must fail
    count_assert = 0
    try:
        db_session.add(duplicate_user)
        db_session.commit()
    except exc.IntegrityError:
        count_assert = 1
        assert True
    assert count_assert == 1


def test_component_create(test_app):
    app, test_client = test_app

    customer = customers_example[0]

    ##### PUT A NEW USER #####
    assert create_user_EP(test_client, **customer).status_code == 200

    getuser = db_session.query(User).filter(User.email == customer['email']).first()
    assert getuser is not None
    assert getuser.email == customer['email']
    assert getuser.phone == customer['phone']
    assert getuser.firstname == customer['firstname']
    assert getuser.lastname == customer['lastname']
    assert getuser.authenticate(customer['password']) is True
    assert getuser.dateofbirth == datetime.strptime(customer['dateofbirth'], "%d/%m/%Y").date()
    assert getuser.role == customer['role']
    
    ##### CANNOT INSERT DIFFERENT USERS WITH SAME EMAIL #####
    assert create_user_EP(test_client, **customer).status_code == 409

    owner = restaurant_owner_example[0]

    ##### PUT A NEW RESTAURANT OWNER #####
    assert create_user_EP(test_client, **owner).status_code == 200


def test_component_login(test_app):
    app, test_client = test_app

    customer = customers_example[0]
    assert create_user_EP(test_client, **customer).status_code == 200

    ##### LOGIN WITH NOT EXISTING EMAIL AND PASSWORD #####
    assert user_login_EP(test_client, "notexisting@email.com", customer['password']).status_code == 404

    ##### LOGIN WITH CORRECT EMAIL AND WRONG PASSWORD #####
    assert user_login_EP(test_client, customer['email'], "wrongpassword").status_code == 401

    ##### LOGIN WITH CORRECT EMAIL AND PASSWORD #####
    assert user_login_EP(test_client, customer['email'], customer['password']).status_code == 200

    ##### LOGIN WITH A PROFILE NOT ACTIVE (is_active == False) #####
    customer_no_active = customers_example[1]

    user_no_active = User()
    user_no_active.email = customer_no_active['email']
    user_no_active.phone = customer_no_active['phone']
    user_no_active.firstname = customer_no_active['firstname']
    user_no_active.lastname = customer_no_active['lastname']
    user_no_active.set_password(customer_no_active['password'])
    user_no_active.dateofbirth = datetime.strptime(customer_no_active['dateofbirth'], "%d/%m/%Y")
    user_no_active.role = customer_no_active['role']
    user_no_active.is_active = False

    db_session.add(user_no_active)
    db_session.commit()

    assert user_login_EP(test_client, 
                        customer_no_active['email'], 
                        customer_no_active['password']
    ).status_code == 401


def test_component_edit(test_app):
    app, test_client = test_app

    customer = customers_example[0]
    create_user_EP(test_client, **customer)
    
    data = dict(
        user_new_phone=customer['phone'],
        current_user_old_password=customer['password'],
        current_user_new_password="new_password"
    )

    user_id = db_session.query(User).filter(User.email == customer['email']).first()

    ##### FORCE WRONG PARAMETERS #####
    assert wrong_edit_user_EP(test_client, user_id.id, **data).status_code == 400

    ##### EDIT USER PASSWORD #####
    assert edit_user_EP(test_client, user_id.id, **data).status_code == 200

    ##### LOGIN USER WITH NEW PASSWORD #####
    assert user_login_EP(test_client, 
                        customer['email'], 
                        data['current_user_new_password']
    ).status_code == 200

    ##### LOGIN USER WITH OLD PASSWORD #####
    assert user_login_EP(test_client, 
                        customer['email'], 
                        customer['password']
    ).status_code == 401

    new_phone_number = data['user_new_phone']+"1"
    ##### EDIT USER PHONE #####
    data['current_user_old_password'] = data['current_user_new_password']
    data['user_new_phone'] = new_phone_number
    assert edit_user_EP(test_client, user_id.id,  **data).status_code == 200
    
    # check if phone number really changed
    getuser = db_session.query(User).filter(User.email == customer['email']).first()
    assert getuser.phone == new_phone_number

    ##### EDIT USER WITH WRONG PASSWORD #####
    data['current_user_old_password'] = "wrongpassword"
    assert edit_user_EP(test_client, user_id.id,  **data).status_code == 401

''' THIS IS WORKING LOCALLY BUT NOT IN DOCKER
def test_component_getusers(test_app):
    app, test_client = test_app

    customer = [None] * 3
    customer[0] = customers_example[0]
    customer[1] = customers_example[1]
    customer[2] = customers_example[2]

    for i in range(0,3):
        create_user_EP(test_client, **customer[i])

    ##### GET ALL USERS #####
    getusers = get_users_EP(test_client, "")
    getusers_json = getusers.json
    
    customer = sorted(customer, key=lambda k: k['email'])
    
    ##### GET A SPECIFIC USER BY EMAIL #####
    getusers = get_users_EP(test_client, customer[1]['email'])
    getusers_json = getusers.json

    assert len(getusers_json) == 1
    assert getusers_json[0]['email'] == customer[1]['email']
    assert getusers_json[0]['phone'] == customer[1]['phone']
    assert getusers_json[0]['firstname'] == customer[1]['firstname']
    assert getusers_json[0]['lastname'] == customer[1]['lastname']
    
    ##### GET A NON EXISTING USER BY EMAIL  #####
    assert get_users_EP(test_client, "nonexisting@user.com").status_code == 404

    ##### GET A SPECIFIC USER BY ID #####
    user_ID = db_session.query(User).filter(User.email == customer[1]['email']).first()
    getusers = get_user_by_ID_EP(test_client, str(user_ID.id))
    getusers_json = getusers.json

    assert getusers_json['email'] == customer[1]['email']
    assert getusers_json['phone'] == customer[1]['phone']
    assert getusers_json['firstname'] == customer[1]['firstname']
    assert getusers_json['lastname'] == customer[1]['lastname']
    
    ##### GET A NON EXISTING USER BY ID  #####
    assert get_user_by_ID_EP(test_client, 5).status_code == 404
'''

def test_component_get_patient(test_app):
    app, test_client = test_app

    # INSERT ADMIN
    insert_admin(db_session, app)

    customer = customers_example[0]
    create_user_EP(test_client, **customer)

    ##### GET PATIENT BY EMAIL #####
    patient = get_patient_EP(test_client, customer['email'])
    patient_json = patient.json

    startdate = datetime.today().date()
    enddate = startdate + timedelta(days=14)
    assert patient.status_code == 200
    assert patient_json['email'] == customer['email']
    assert patient_json['phone'] == customer['phone']
    assert patient_json['firstname'] == customer['firstname']
    assert patient_json['lastname'] == customer['lastname']
    assert datetime.strptime(patient_json['dateofbirth'], "%Y-%m-%d") == datetime.strptime(customer['dateofbirth'], "%d/%m/%Y")
    assert patient_json['role'] == customer['role']
    assert datetime.strptime(patient_json['startdate'], "%Y-%m-%d").date() == startdate
    assert datetime.strptime(patient_json['enddate'], "%Y-%m-%d").date() == enddate
    assert patient_json['state'] == "patient next under observation"
    
    ##### GET NOT EXISTING PATIENT BY EMAIL #####
    assert get_patient_EP(test_client, "notexisting@patient.com").status_code == 404


    ##### GET ADMIN MEDICAL RECORD AS PATIENT BY EMAIL #####
    assert get_patient_EP(test_client, "admin@admin.com").status_code == 403


def test_component_mark_patient(test_app):
    app, test_client = test_app

    # INSERT ADMIN
    insert_admin(db_session, app)

    customer = customers_example[0]
    create_user_EP(test_client, **customer)

    ##### MARK PATIENT AS POSITIVE #####
    assert mark_patient_EP(test_client, customer['email']).status_code == 200

    ##### MARK PATIENT AS POSITIVE A SECOND TIME #####
    assert mark_patient_EP(test_client, customer['email']).status_code == 403

    ##### GET A PATIENT MARKED POSITIVE BY EMAIL #####
    patient = get_patient_EP(test_client, customer['email'])
    patient_json = patient.json

    startdate = datetime.today().date()
    enddate = startdate + timedelta(days=14)
    assert patient.status_code == 200
    assert patient_json['email'] == customer['email']
    assert patient_json['phone'] == customer['phone']
    assert patient_json['firstname'] == customer['firstname']
    assert patient_json['lastname'] == customer['lastname']
    assert datetime.strptime(patient_json['dateofbirth'], "%Y-%m-%d") == datetime.strptime(customer['dateofbirth'], "%d/%m/%Y")
    assert patient_json['role'] == customer['role']
    assert datetime.strptime(patient_json['startdate'], "%Y-%m-%d").date() == startdate
    assert datetime.strptime(patient_json['enddate'], "%Y-%m-%d").date() == enddate
    assert patient_json['state'] == "patient already under observation"


    ##### MARK NOT EXISTING PATIENT AS POSITIVE #####
    assert mark_patient_EP(test_client, "notexisting@patient.com").status_code == 404

    ##### MARK ADMIN AS POSITIVE #####
    assert mark_patient_EP(test_client, "admin@admin.com").status_code == 403


    ##### LOGIN AS POSITIVE #####
    assert user_login_EP(test_client, customer['email'], customer['password']).status_code == 200
    
    ##### DO TRACING #####
    launch_contact_tracing()

def test_component_notification(test_app):
    app, test_client = test_app

    customer = [None] * 3
    customer[0] = customers_example[0]
    customer[1] = customers_example[1]
    customer[2] = customers_example[2]

    create_user_EP(test_client, **customer[0])
    create_user_EP(test_client, **customer[1])
    create_user_EP(test_client, **customer[2])


    owner = [None] * 2
    owner[0] = restaurant_owner_example[0]
    owner[1] = restaurant_owner_example[1]

    create_user_EP(test_client, **owner[0])
    create_user_EP(test_client, **owner[1])

    owner_0_id = db_session.query(User).filter(User.email == owner[0]['email']).first().id
    owner_1_id = db_session.query(User).filter(User.email == owner[1]['email']).first().id

    customer0_notification_dict = [
        dict(
            email=customer[0]['email'],
            message="On  DATE(X) you have been in contact with a positive. Get into quarantine!",
            notiftype= "contact_with_positive"
        )       
    ]

    customer01_and_owner0_notification_dict = [
        dict(
            email=customer[0]['email'],
            message="On  DATE(Y) you have been in contact with a positive. Get into quarantine!",
            notiftype= "contact_with_positive"
        ),
        dict(
            email=customer[1]['email'],
            message="On  DATE(Y) you have been in contact with a positive. Get into quarantine!",
            notiftype= "contact_with_positive"
        ),
        dict(
            id=owner_0_id,
            message="On DATE(Y) there was a positive in your restaurant!",
            notiftype= "contact_with_positive"
        )
    ]

    owner1_notification_dict = [
        dict(
            email=owner[1]['email'],
            message="The reservation of the TABLENAME(A) table for the date DATE(Z) has been canceled",
            notiftype= "reservation_canceled"
        )       
    ]

    ##### ALERT CUSTOMER 0 ABOUT POSITIVE CONTACT ON DATE(X) #####
    assert set_notification_EP(test_client, customer0_notification_dict).status_code == 200
    
    reply = user_login_EP(test_client, customer[0]['email'], customer[0]['password'])
    reply_json = reply.json

    assert reply_json['notification'][0]['message'] == customer0_notification_dict[0]['message']


    ##### ALERT CUSTOMER 0, CUSTOMER 1, OWNER 0 - ABOUT POSITIVE CONTACT ON DATE(Y) #####
    assert set_notification_EP(test_client, customer01_and_owner0_notification_dict).status_code == 200
    
    ### check notifications on CUSTOMER 0
    reply = user_login_EP(test_client, customer[0]['email'], customer[0]['password'])
    reply_json = reply.json

    assert reply_json['notification'][0]['message'] == customer0_notification_dict[0]['message']
    assert reply_json['notification'][1]['message'] == customer01_and_owner0_notification_dict[0]['message']

    ### check notifications on CUSTOMER 1
    reply = user_login_EP(test_client, customer[1]['email'], customer[1]['password'])
    reply_json = reply.json

    assert reply_json['notification'][0]['message'] == customer01_and_owner0_notification_dict[1]['message']

    ### check notifications on OWNER 0
    reply = user_login_EP(test_client, owner[0]['email'], owner[0]['password'])
    reply_json = reply.json

    assert reply_json['notification'][0]['message'] == customer01_and_owner0_notification_dict[2]['message']


    ##### ALERT OWNER 1 ABOUT CANCELED RESERVATION #####
    assert set_notification_EP(test_client, owner1_notification_dict).status_code == 200
    
    reply = user_login_EP(test_client, owner[1]['email'], owner[1]['password'])
    reply_json = reply.json

    assert reply_json['notification'][0]['message'] == owner1_notification_dict[0]['message']
   

def test_component_delete(test_app):
    app, test_client = test_app

    customer = customers_example[0]

    create_user_EP(test_client, **customer)

    not_existing_user = 50

    user_id = db_session.query(User).filter(User.email == customer['email']).first()

    assert delete_user_EP(test_client, not_existing_user, customer['password']).status_code == 404

    assert delete_user_EP(test_client, user_id.id, "wrongpassword").status_code == 401

    assert delete_user_EP(test_client, 1, "healthauthority").status_code == 401

    assert delete_user_EP(test_client, user_id.id, customer['password']).status_code == 200

    assert user_login_EP(test_client, customer['email'], customer['password']).status_code == 401

    ##### GET A NON ACTIVE USER #####
    assert get_patient_EP(test_client, customer['email']).status_code == 403


    owner = restaurant_owner_example[0]
    create_user_EP(test_client, **owner)

    user_id = db_session.query(User).filter(User.email == owner['email']).first()
    assert delete_user_EP(test_client, user_id.id, customer['password']).status_code == 200
    
    ##### GET A NON ACTIVE USER #####

    del_inactive_users()
