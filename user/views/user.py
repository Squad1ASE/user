
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
        print(users)
        print(type(users))
        if len(users) == 0:
            return connexion.problem(404, "Not Found", "Wrong email. User doesn't exist")

    else:
        users = db_session.query(User).with_entities(User.email, User.phone, User.firstname, User.lastname).all()

    return users


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

    # TODO add quarantine status, to avoid another call when user wants to place a booking
    # he can't if he still positive
    user_dict = dict(
        id=user.id,
        email=user.email,
        phone=user.phone,
        firstname=user.firstname,
        lastname=user.lastname,
        dateofbirth=user.dateofbirth,
        role=user.role,
        is_admin=user.is_admin,
        is_anonymous=user.is_anonymous
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
        startdate = datetime.today()
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


    startdate = datetime.today()
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
        notification.email = data['email']
        notification.date = now
        notification.type_ = data['notiftype']
        timestamp = data['date']
        ############# retrieving user id if the email is a registered user (customer or owner) #############
        user = db_session.query(User).filter(User.email == data['email']).first()
        if user is not None:
            notification.user_id = user.id
            notification.email = user.email
            # TODO this if must be removed since after mark positive
            # USER microservice will send email to RESERVATION which will reply
            # withouth the positive user
            '''
            # the positive must not be alerted to have come into contact with itself
            if positive.id == user.id:
                continue
            '''
        if data['notiftype'] == "contact_with_positive":
            if(data['role'] == "customer"):
                notification.message = 'On ' + timestamp + ' you have been in contact with a positive. Get into quarantine!'
            else:
                notification.message = 'On ' + timestamp + ' there was a positive in your restaurant!'

        if data['notiftype'] == "reservation_canceled":
            notification.message = 'The reservation of the ' + data['tablename'] + ' table for the date ' + data['reservationdate'] + ' has been canceled'
        
        if data['notiftype'] == "reservation_with_positive":
            message = 'The reservation of ' + timestamp + ' at table "' + data['tablename'] + '" of restaurant "' + data['restaurantname'] + '" has a positive among the guests.'
            message = message + ' Contact the booker by email "' + data['bookeremail'] + '" or by phone ' + data['bookerphone']
            notification.message = message



        # check user deleted
        if 'invalid_email' not in notification.email:
            db_session.add(notification)
    
    db_session.commit()
    return "OK"

# TODO get notifiche utente
# TODO users/{user_id}