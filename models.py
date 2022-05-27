from decimal import Decimal
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Boolean, DECIMAL
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.sql.functions import count

# For using locally
database_name = 'realestate'
database_path = "mysql+mysqlconnector://{}@{}/{}".format('root:root', 'localhost', database_name)

# For production
#database_path = os.environ['CLEARDB_DATABASE_URL']

db = SQLAlchemy()

'''
    setup_db(app)
    binds a flask application and a SQLAlchemy service
'''


def setup_db(app, database_path=database_path):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'connect_args': {
        'connect_timeout': 28800,
    }
}
    db.app = app
    db.init_app(app)
    db.create_all()


'''
Gender
'''


class Gender(db.Model):
    ___tablename__ = 'gender'

    gender_id = Column(Integer, primary_key=True)
    type = Column(String(100))
    employees = db.relationship('Employees', backref='gender', lazy='dynamic')

    def __init__(self, type):
        self.type = type

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'gender_id': self.gender_id,
            'type': self.type,
        }

'''
Source
'''


class Source(db.Model):
    ___tablename__ = 'source'

    source_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    leads = db.relationship('Leads', backref='source', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'source_id': self.source_id,
            'name': self.name,
        }


'''
Status
'''


class Status(db.Model):
    ___tablename__ = 'status'

    status_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    leads = db.relationship('Description', backref='status', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'source_id': self.source_id,
            'name': self.name,
        }


'''
Jobs
'''


class Jobs(db.Model):
    ___tablename__ = 'jobs'

    jobs_id = Column(Integer, primary_key=True)
    job_title = Column(String(100))

    employees = db.relationship('Employees', backref='jobs', lazy='dynamic')
    job_history = db.relationship('Job_History', backref='jobs', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'jobs_id': self.jobs_id,
            'job_title': self.job_title,
        }


'''
Job_History
'''


class Job_History(db.Model):
    ___tablename__ = 'job_history'

    job_history_id = Column(Integer, primary_key=True)
    start_date = Column(Date)
    end_date = Column(Date)
    employee_id = Column(Integer, ForeignKey('employees.employees_id'))
    job_id = Column(Integer, ForeignKey('jobs.jobs_id'))


    def __init__(self, start_date, end_date, employee_id, job_id):
        self.start_date = start_date
        self.end_date = end_date
        self.employee_id = employee_id
        self.job_id = job_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'job_history_id': self.job_history_id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'employee_id': self.employee_id,
            'job_id': self.job_id,
        }



'''
Employees
'''


class Employees(db.Model):
    ___tablename__ = 'employees'

    employees_id = Column(Integer, primary_key=True)
    ssn = Column(DECIMAL(14))
    f_name = Column(String(50))
    l_name = Column(String(50))
    phone_number = Column(String(50))
    qualifications = Column(String(100))
    address = Column(String(120))
    salary = Column(Integer)
    gender_id = Column(Integer, ForeignKey('gender.gender_id'))
    job_id = Column(Integer, ForeignKey('jobs.jobs_id'), nullable=True)
    
    credential = db.relationship('Credentials', backref='employees')
    job_history = db.relationship('Job_History', backref='employees', lazy='dynamic')
    deals = db.relationship('Deals', backref='employees', lazy='dynamic')
    leads = db.relationship('Leads', backref='employees', lazy='dynamic')
    description = db.relationship('Description', backref='employees', lazy='dynamic')



    def __init__(self, ssn, f_name, l_name, phone_number, qualifications, address, salary, job_id, gender_id):
        self.f_name = f_name
        self.ssn = ssn
        self.l_name = l_name
        self.phone_number = phone_number
        self.address = address
        self.qualifications = qualifications
        self.salary = salary
        self.job_id = job_id
        self.gender_id = gender_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'id': self.id,
            'ssn': self.ssn,
            'f_name': self.f_name,
            'l_name': self.l_name,
            'phone_number': self.phone_number,
            'qualifications': self.qualifications,
            'address': self.address,
            'salary': self.salary,
            'job_id': self.job_id,
            'gender': self.gender_id
        }


'''
Credentials
'''

class Credentials(UserMixin, db.Model):
    ___tablename__ = 'credentials'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True)
    password = Column(String(150))
    role = Column(String(50), nullable=True)
    employee_id = Column(Integer, ForeignKey('employees.employees_id'))

    def __init__(self, username, password, role, employee_id):
        self.username = username
        self.password = password
        self.role = role
        self.employee_id = employee_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,
            'role': self.role,
            'employee_id': self.employee_id,
        }


'''
Developers
'''


class Developers(db.Model):
    ___tablename__ = 'developers'

    developers_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    phone_number = Column(String(50))
    email = Column(String(64))
    date_of_cotract = Column(Date)
    address = Column(String(120))

    projects = db.relationship('Projects', backref="developers", lazy='dynamic')

    def __init__(self, name, phone_number, email, date_of_cotract, address):
        self.name = name
        self.phone_number = phone_number
        self.email = email
        self.date_of_cotract = date_of_cotract
        self.address = address

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'developers_id': self.developers_id,
            'name': self.name,
            'phone_number': self.phone_number,
            'email': self.email,
            'date_of_cotract': self.date_of_cotract,
            'address': self.address,
        }


'''
Projects
'''


class Projects(db.Model):
    ___tablename__ = 'projects'

    projects_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    unit_price = Column(Integer)
    location = Column(String(120))
    type = Column(String(100))
    commission = Column(String(20))

    developer_id = Column(Integer, ForeignKey("developers.developers_id"))

    deals = db.relationship('Deals', backref="projects", lazy='dynamic')

    def __init__(self, name, unit_price, location, type, commission, developer_id):
        self.name = name
        self.unit_price = unit_price
        self.location = location
        self.type = type
        self.commission = commission
        self.developer_id = developer_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'projects_id': self.projects_id,
            'name': self.name,
            'unit_price': self.unit_price,
            'location': self.location,
            'type': self.type,
            'commission': self.commission,
            'developer_id': self.developer_id
        }



'''
Leads
'''


class Leads(db.Model):
    ___tablename__ = 'leads'

    leads_id = Column(Integer, primary_key=True, autoincrement=True)
    time_created = Column(Date())
    client_name = Column(String(100))
    email = Column(String(64))
    request = Column(String(100), nullable=True)
    phone = Column(String(20))
    assigned_to_id = Column(Integer, ForeignKey('employees.employees_id'), nullable=True)
    source_id = Column(Integer, ForeignKey('source.source_id'), nullable=True)
    
    
    descriptions = db.relationship('Description', backref='leads', lazy='dynamic')


    def __init__(self, time_created, client_name, email, request, phone, assigned_to_id, source_id):
        self.time_created = time_created
        self.client_name = client_name 
        self.email = email
        self.request = request
        self.phone = phone
        self.assigned_to_id = assigned_to_id
        self.source_id = source_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'leads_id': self.leads_id,
            'time_created': self.time_created,
            'client_name': self.client_name,
            'email': self.email,
            'request': self.request,
            'phone': self.phone,
            'assigned_to_id': self.assigned_to_id,
            'source_id': self.source_id
        }


'''
Deals
'''


class Deals(db.Model):
    ___tablename__ = 'deals'

    deals_id = Column(Integer, primary_key=True, autoincrement=True)
    time_created = Column(Date())
    buyer_name = Column(String(100))
    email = Column(String(64))
    down_payment = Column(Integer)
    phone = Column(String(20))
    assigned_to_id = Column(Integer, ForeignKey('employees.employees_id'))
    project_id = Column(Integer, ForeignKey('projects.projects_id'))
    
    
    descriptions = db.relationship('Description', backref='deals', lazy='dynamic')


    def __init__(self, time_created, buyer_name, email, down_payment, phone, assigned_to_id, project_id):
        self.time_created = time_created
        self.buyer_name = buyer_name 
        self.email = email
        self.down_payment = down_payment
        self.phone = phone
        self.assigned_to_id = assigned_to_id
        self.source_id = project_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'deals_id': self.deals_id,
            'time_created': self.time_created,
            'buyer_name': self.buyer_name,
            'email': self.email,
            'down_payment': self.down_payment,
            'phone': self.phone,
            'assigned_to_id': self.assigned_to_id,
            'project_id': self.project_id
        }


'''
Description
'''


class Description(db.Model):
    ___tablename__ = 'description'

    description_id = Column(Integer, primary_key=True, autoincrement=True)
    time_created = Column(Date)
    notes = Column(String(500))
    status_id = Column(Integer, ForeignKey('status.status_id'), nullable=True)
    deals_id = Column(Integer, ForeignKey('deals.deals_id'), nullable=True)
    leads_id = Column(Integer, ForeignKey('leads.leads_id'), nullable=True)
    employees_id = Column(Integer, ForeignKey('employees.employees_id'), nullable=True)


    def __init__(self, time_created, notes, status_id, deals_id, leads_id, employees_id):
        self.time_created = time_created
        self.notes = notes
        self.status_id = status_id
        self.deals_id = deals_id
        self.leads_id = leads_id
        self.employees_id = employees_id


    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def format(self):
        return {
            'description_id': self.description_id,
            'time_created': self.time_created,
            'notes': self.notes,
            'status_id': self.status_id,
            'deals_id': self.deals_id,
            'leads_id': self.leads_id,
            'employees_id': self.employees_id
        }