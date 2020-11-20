import os
from sqlalchemy import create_engine, Column, Integer, Float, Text, Unicode, CheckConstraint
from sqlalchemy import Boolean, String, Date
from sqlalchemy.orm import validates
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

#DATABASEURI = os.environ['DATABASE_URI']
db = declarative_base()
#engine = create_engine(DATABASEURI, convert_unicode=True)
engine = create_engine('sqlite:///user.db', convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                             bind=engine))


def init_db():
    try:
        db.metadata.create_all(bind=engine)
    except Exception as e:
        print(e)

# the following consist of tables inside the db tables are defined using model
class User(db):
    __tablename__ = 'user'
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