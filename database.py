import os
from sqlalchemy import create_engine, Column, Integer, Float, Text, Unicode, CheckConstraint, ForeignKey, PickleType
from sqlalchemy import Boolean, String, Date
from sqlalchemy.orm import validates, relationship
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from static.enum import NOTIFICATION_TYPE

DATABASEURI = os.environ['DATABASE_USER_URI']
db = declarative_base()
engine = create_engine(DATABASEURI, convert_unicode=True)
#engine = create_engine('sqlite:///user.db', convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                             bind=engine))


def init_db():
    try:
        db.metadata.create_all(bind=engine)
    except Exception as e:
        print(e)


    ####### HEALTHY AUTHORITY PROFILE #######
    q = db_session.query(User).filter(User.email == 'healthauthority@ha.com')
    adm = q.first()
    
    if adm is None:
        try: 
            example = User()
            example.email = 'healthauthority@ha.com'
            example.phone = '3333333333'
            example.firstname = 'ha'
            example.lastname = 'ha'
            example.set_password('healthauthority')
            example.dateofbirth = datetime.date(2020, 10, 5)
            example.is_admin = True
            example.role = 'ha'
            db_session.add(example)
            db_session.commit()
        except Exception as e:
            print(e)
    

# the following consist of tables inside the db tables are defined using model
class User(db):
    __tablename__ = 'user'
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer, primary_key=True, autoincrement=True)

    email = Column(String, nullable=False, unique=True)  
    @validates('email')
    def validate_email(self, key, user):
        if('@' and '.' in user): #min email possible: a@b.c
            return user
        raise SyntaxError('Wrong email syntax')

    phone = Column(Unicode(128), CheckConstraint('length(phone) > 0'), nullable=False)

    firstname = Column(Unicode(128))
    lastname = Column(Unicode(128))
    password = Column(Unicode(128), nullable=False) 
    dateofbirth = Column(Date)

    role = Column(String, nullable=False) 
    @validates('role')
    def validate_role(self, key, user):
        if(user == 'admin' or user == 'customer' or user == 'owner' or user == 'ha'):
            return user
        raise SyntaxError('Wrong role assignment')

    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_anonymous = False
    
    # this is usefull when a user is going to be deleted
    delete_user_restaurant = Column(Boolean, default=False)
    delete_user_reservation = Column(Boolean, default=False)


    def __init__(self, *args, **kw):
        super(User, self).__init__(*args, **kw)
        self._authenticated = False

    def set_password(self, password):
        self.password = generate_password_hash(password)

    @property
    def is_authenticated(self):
        return self._authenticated

    def authenticate(self, password):
        checked = check_password_hash(self.password, password)
        self._authenticated = checked  # it is true if the user password is correct
        return self._authenticated

    def get_id(self):
        return self.id
    
    def serialize(self):
        return dict([(k,v) for k,v in self.__dict__.items() if k[0] != '_'])


class Notification(db):
    __tablename__ = 'notification'

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', foreign_keys='Notification.user_id')

    email = Column(Unicode(128), CheckConstraint('length(email) > 0'), nullable=False)  
    message = Column(Unicode(128), CheckConstraint('length(message) > 0'), nullable=False)
    pending = Column(Boolean, default=True)
    type_ = Column(PickleType, nullable=False)  
    # TODO check if date should be Date as used in User or Datetime (previously it was Datetime)
    date = Column(Date, nullable=False)

    @validates('user_id')
    def validate_user_id(self, key, user_id):
        if user_id is not None:
            if (user_id <= 0): raise ValueError("user_id must be > 0")
        return user_id
        
    @validates('email')
    def validate_email(self, key, email):
        if email is None: raise ValueError("type_ is None")
        if (len(email) == 0): raise ValueError("email is empty")
        if('@' and '.' in email): #min email possible: a@b.c
            return email
        raise ValueError('Wrong email syntax')

    @validates('message')
    def validate_message(self, key, message):
        if (message is None): raise ValueError("message is None")
        if (len(message) == 0): raise ValueError("message is empty")
        return message
    
    @validates('pending')
    def validate_pending(self, key, pending):
        if (pending is None): raise ValueError("pending is None")
        return pending

    @validates('type_')
    def validate_type_(self, key, type_):
        if type_ is None: raise ValueError("type_ is None")
        if type_ not in NOTIFICATION_TYPE: raise ValueError("type_ is not a Notification.TYPE")
        return type_

    @validates('date')
    def validate_date(self, key, date):
        if (date is None): raise ValueError("date is None")
        return date

class Quarantine(db):
    __tablename__ = 'quarantine'

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', foreign_keys='Quarantine.user_id')

    start_date = Column(Date)
    end_date = Column(Date)

    in_observation = Column(Boolean, default=True) #True=can't book

    contact_tracing_done = Column(Boolean, default=False)
