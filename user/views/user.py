
from database import User, db_session
from flask import request, jsonify, abort, make_response
from datetime import datetime
import connexion

def get_users():
    users = db_session.query(User).with_entities(User.email, User.phone, User.firstname, User.lastname).all()
    return users


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
