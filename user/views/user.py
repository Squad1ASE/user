
from database import User, db_session, Quarantine, Notification
from flask import request, jsonify, abort, make_response
from datetime import datetime, timedelta
import connexion


def create_user():
    r = request.json
    check_already_register = db_session.query(User).filter(User.email == r['email']).first()
            
    
    if(check_already_register is not None):
        # already registered
        return connexion.problem(409, "Conflict", "User already exists")
    

    new_user = User()
    new_user.email = r['email']
    new_user.phone = r['phone']
    new_user.firstname = r['firstname']
    new_user.lastname = r['lastname']
    new_user.set_password(r['password'])
    new_user.dateofbirth = datetime.strptime(r['dateofbirth'], "%d/%m/%Y")
    new_user.role = r['role']
    
    # TODO controllare
    # forse questo controllo può essere rimosso visto che da swagger
    # consento solo customer o owner come possibili valori, altrimenti
    # connexion restituisce un BAD REQUEST
    '''
    if new_user.role != 'customer' and new_user.role != 'owner':
        return connexion.problem(403, "Forbidden", "Only customer or restaurant owner profiles are allowed")
    ''' 

    db_session.add(new_user)
    db_session.commit()
    
    #return make_response('OK')
    return "OK"


def get_users():
    if 'email' in request.args:
        users = db_session.query(User)\
            .filter(User.email == request.args.get("email"))\
            .with_entities(User.email, User.phone, User.firstname, User.lastname)\
            .all()

        if len(users) == 0:
            return connexion.problem(404, "Not Found", "Wrong email. User doesn't exist")

    else:
        users = db_session.query(User).with_entities(User.email, User.phone, User.firstname, User.lastname).all()

    return users


def get_user_by_ID(user_id):
    user = db_session.query(User)\
            .filter(User.id == user_id)\
            .first()
    
    if user is None:
        return connexion.problem(404, "Not Found", "Wrong ID. User doesn't exist")

    data = dict(
        email=user.email,
        phone=user.phone,
        firstname=user.firstname,
        lastname=user.lastname
    )
    return data


def edit_user():
    r = request.json

    email = r['current_user_email']
    old_password = r['current_user_old_password']
    new_password = r['current_user_new_password']
    phone = r['user_new_phone']

    user = db_session.query(User).filter(User.email == email).first()
            
    if (user is not None and user.authenticate(old_password)):
        if(user.phone != phone):
            user.phone = phone
        if(old_password != new_password):
            user.set_password(new_password)
        db_session.commit()
        #return connexion.problem(200, "OK", "User details have been updated")
        return "OK"
    else:
        return connexion.problem(401, "Unauthorized", "Wrong password")


def login():
    r = request.json

    user = db_session.query(User).filter(User.email == r['email']).first()
            
    if user is None:
        # this shouldn't be explicitly reported in the API gateway
        # because a malicious attacker could discover if the email exists or not
        # in the DB
        return connexion.problem(404, "Not Found", "Wrong email or password")
    if user.authenticate(r['password']) is False:
        return connexion.problem(401, "Unauthorized", "Wrong email or password")
    if user.is_active is False:
        return connexion.problem(401, "Unauthorized", "This profile is going to be removed")

    user_quarantine_status = db_session.query(Quarantine)\
        .filter(
            Quarantine.user_id == user.id,
            Quarantine.in_observation == True
        ).first()

    in_observation = False
    if user_quarantine_status is not None:
        in_observation = True

    user_notification = db_session.query(Notification)\
        .filter(
            Notification.user_id == user.id
        )\
        .with_entities(Notification.message, Notification.date)\
        .all()

    '''
    print(user_notification)
    print(type(user_notification[0]))
    print(user_notification)

    user_notification_dict = [n.__dict__ for n in user_notification]
    print(user_notification_dict)
    print(type(user_notification_dict))
    print(type(user_notification_dict[0]))

    user_notification_dict = sorted(user_notification_dict, key=lambda k: k['date'])
    print(user_notification_dict)
    '''
    notification_list = []
    for notification in user_notification:
        temp = dict()
        if isinstance(notification[0], str):
            temp['message'] = notification[0]
            temp['date'] = notification[1]
        else:
            temp['date'] = notification[0]
            temp['message'] = notification[1]

        notification_list.append(temp)

    user_dict = dict(
        id=user.id,
        email=user.email,
        phone=user.phone,
        firstname=user.firstname,
        lastname=user.lastname,
        dateofbirth=user.dateofbirth,
        role=user.role,
        is_admin=user.is_admin,
        is_anonymous=user.is_anonymous,
        in_observation=in_observation,
        notification=notification_list
    )
    return user_dict


def get_user_medical_record():
    #r = request.json
    r = request.args.get("email")
    user = db_session.query(User)\
        .filter(
            User.email == r
        )\
        .first()

    # email isn't correct, user doesn't exist
    if(user is None):
        return connexion.problem(404, "Not Found", "Wrong email. Patient doesn't exist")

    elif(user.role == 'ha' or user.role == 'admin'):
        return connexion.problem(403, "Forbidden", "Health authority and Admin aren't patients")

    getuserquarantine_status = db_session.query(Quarantine)\
        .filter(
            Quarantine.user_id == user.id,
            Quarantine.in_observation == True
        )\
        .first()

    # patient is in observation
    if getuserquarantine_status is not None:
        startdate = getuserquarantine_status.start_date
        enddate = getuserquarantine_status.end_date
        state = "patient already under observation"
    else:
        startdate = datetime.today().date()
        enddate = startdate + timedelta(days=14)
        state = "patient next under observation"

    user_dict = dict(
        email=user.email,
        phone=user.phone,
        firstname=user.firstname,
        lastname=user.lastname,
        dateofbirth=user.dateofbirth,
        role=user.role,
        startdate=startdate,
        enddate=enddate,
        state=state,
    )
    return user_dict


def mark_positive():
    r = request.args.get("email")

    user = db_session.query(User)\
        .filter(
            User.email == r
        )\
        .first()

    # email isn't correct, user doesn't exist
    # this happens only under a malicious attack
    if(user is None):
        return connexion.problem(404, "Not Found", "Something is not working. This email doesn't exist")

    elif(user.role == 'ha' or user.role == 'admin'):
        return connexion.problem(403, "Forbidden", "Health authority and Admin aren't patients")

    getuserquarantine_status = db_session.query(Quarantine)\
        .filter(
            Quarantine.user_id == user.id,
            Quarantine.in_observation == True
        )\
        .first()
    
    if getuserquarantine_status is not None:
        return connexion.problem(403, "Forbidden", "Can't mark a patient already under observation")


    startdate = datetime.today().date()
    enddate = startdate + timedelta(days=14)

    quarantine = Quarantine()
    quarantine.user_id = user.id
    quarantine.start_date = startdate
    quarantine.end_date = enddate
    quarantine.in_observation = True

    db_session.add(quarantine)
    db_session.commit()

    return "OK"


def delete_user():
    r = request.json

    current_user = r['current_user_email']

    user_to_delete = db_session.query(User).filter(User.email == current_user).first()

    if user_to_delete is None:
        return connexion.problem(404, "Not Found", "Something is not working. This email doesn't exist")

    # TODO waiting Emilio's microservice
    # TODO waiting Reservation microservice team
    '''
    if user_to_delete.role == 'owner':
        # delete first the restaurant and then treat it as a customer
        restaurants = db.session.query(Restaurant).filter(Restaurant.owner_id == user_to_delete.id).all()
        for res in restaurants:
            restaurant_delete(res.id)
    else:                
        # first delete future reservations               
        rs = db.session.query(Reservation).filter(
            Reservation.booker_id == user_to_delete.id,
            Reservation.date >= datetime.datetime.now()).all() 
        for r in rs: 
            deletereservation(r.id)
    '''
    user_to_delete.is_active = False
    db_session.commit()

    return make_response('OK') 

def notification():
    r = request.json
    now = datetime.now()

    for data in r:
        notification = Notification()

        if 'email' in data:
            get_id = db_session.query(User).filter(User.email == data['email']).first()

            if get_id is not None:
                notification.user_id = get_id.id

            notification.email = data['email']

        elif 'id' in data:
            get_email = db_session.query(User).filter(User.id == int(data['id'])).first()
            
            if get_email is not None:
                notification.email = get_email.email

            notification.user_id = int(data['id'])

        notification.message = data['message']
        notification.type_ = data['notiftype']
        notification.date = now

        # check user deleted
        if 'invalid_email' not in notification.email:
            db_session.add(notification)
    
    db_session.commit()
    return "OK"