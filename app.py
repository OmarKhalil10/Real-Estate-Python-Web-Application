from flask import Flask, request, redirect, render_template, jsonify, abort, session, flash
from flask_login.utils import login_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from flask_login import LoginManager, login_manager, login_user, logout_user, login_required, current_user
from datetime import datetime, timezone, timedelta
import dateutil.parser
import babel
import time
import os
import json
import pandas as pd
from sqlalchemy.sql import text
from sqlalchemy import or_, and_
from sqlalchemy.sql import func
from models import Employees, Credentials, Deals, Leads, Description, Status, Source, Projects, setup_db, db

secret_key="\x15\xd5\xafG?\x1cc?\xbe\x9b\xa9\x84<z\x92E+\xcbGW\x18\xddv\xb2"

RESULT_PER_PAGE = 10



def datetime_from_utc_to_local(utc_datetime):
    return utc_datetime + timedelta(hours=2)

def datetime_from_local_to_utc(utc_datetime):
    return utc_datetime - timedelta(hours=2)

def paginate_results(request, selection):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * RESULT_PER_PAGE
    end = start + RESULT_PER_PAGE

    results = [result.format() for result in selection]
    current_results = results[start:end]

    return current_results


def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secret_key
    # Windows
    UPLOAD_FOLDER = 'E:/public_html/static/files'
    # Linux
    # UPLOAD_FOLDER = '../public_html/static/files'
    app.config['UPLOAD_FOLDER'] =  UPLOAD_FOLDER

    setup_db(app)
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    # CORS Headers

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,true')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
        return response
    #----------------------------------------------------------------------------#
    # Filters.
    #----------------------------------------------------------------------------#
    def format_datetime(value, format='medium'):
        date = dateutil.parser.parse(value)
        if format == 'full':
            format="EEEE MMMM, d, y 'at' h:mma"
        elif format == 'medium':
            format="EE MM, dd, y h:mma"
        return babel.dates.format_datetime(date, format)

    app.jinja_env.filters['datetime'] = format_datetime
    
    @login_manager.user_loader
    def load_user(id):
        return Credentials.query.get(int(id))

    @app.route('/', methods=['GET'])
    def landing_page():
        return redirect("/login")

    @app.route('/about', methods=['GET'])
    def about_page():
        return render_template('pages/about-us.html')

    @app.route('/contact', methods=['GET'])
    def contact_page():
        return render_template('pages/contacts.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = True if request.form.get('remember') else False
            print(username)
            print(password)

            user = Credentials.query.filter(Credentials.username == username).one()
            print(user.password)
            if not user or not user.password == password:
                flash('Please check your password details and try again.')
                return redirect("/login")
            if user.role == 'gm' or user.role == 'hr' or user.role == 'it':
                login_user(user, remember=remember)
                return redirect('/employees')
            elif user.role == 'admin':
                login_user(user, remember=remember)
                return redirect('/admin/dashboard')
            elif user.role == 'teamlead':
                login_user(user, remember=remember)
                return redirect('/teamlead/dashboard')
            elif user.role == 'manager':
                login_user(user, remember=remember)
                return redirect('/manager/dashboard')
            else:
                login_user(user, remember=remember)
                return redirect('/dashboard/'+ str(user.employee_id))

            flash('Please check your login email and try again.')
            return redirect("/login")
        return render_template('pages/login.html')


    @app.route('/logout')
    def logout():
        logout_user()
        return redirect('/login')
    
    """
    Employees
    """

    @app.route('/employees')
    @login_required
    def retrieve_employees():
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            selection = Employees.query.order_by(Employees.id).all()
            current_employees = [result.format() for result in selection]
            
            return render_template('pages/general-manager/dashboard.html', data={
                'id': current_user.employees_id,
                'sucess': True,
                'employees': current_employees,
            }), 200
        elif current_user.role == 'admin':
            selection = Employees.query.order_by(Employees.id).all()
            current_employees = [result.format() for result in selection]
            
            return render_template('pages/admin/employees.html', data={
                'id': current_user.employees_id,
                'sucess': True,
                'employees': current_employees,
            }), 200
        elif current_user.role == 'manager':
            selection = Employees.query.order_by(Employees.id).all()
            current_employees = [result.format() for result in selection]
            
            return render_template('pages/manager/employees.html', data={
                'id': current_user.employees_id,
                'sucess': True,
                'employees': current_employees,
            }), 200
        else:
            abort(403)

    @app.route('/employees/new', methods=['GET'])
    @login_required
    def new_employee():
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            return render_template('pages/general-manager/add-employee.html', data={'id': current_user.id})
        elif current_user.role == 'admin':
            return render_template('pages/admin/add-employee.html', data={'id': current_user.id})
        elif current_user.role == 'manager':
            return render_template('pages/manager/add-employee.html', data={'id': current_user.id})
        else:
            abort(403)

    @app.route('/employees/add', methods=['POST'])
    @login_required
    def add_new_employee():
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it' or current_user.role == 'admin' or current_user.role == 'manager':
                new_name = request.form.get('name', None)
                new_id_number = request.form.get('id_number', None)
                new_phone = request.form.get('phone', None)
                new_date_of_birth = request.form.get('date_of_birth', None)
                new_address = request.form.get('address', None)
                new_qualifications = request.form.get('qualifications', None)
                new_job_title = request.form.get('job_title', None)
                new_id_link = request.form.get('id_link', None)
                new_criminal_record_link = request.form.get('criminal_record_link', None)
                new_birth_certificate_link = request.form.get('birth_certificate_link', None)
                new_cv_link = request.form.get('cv_link', None)

                new_username = (((new_name.lower()).split(" "))[0])+'.'+(((new_name.lower()).split(" "))[1])+'@arramproperties.com'
                if not Credentials.query.filter(Credentials.username == new_username).first():
                    new_employee = Employees(name=new_name, id_number=new_id_number, phone=new_phone, date_of_birth=new_date_of_birth, address=new_address, qualifications=new_qualifications, job_title=new_job_title, id_link=new_id_link, criminal_record_link=new_criminal_record_link, birth_certificate_link=new_birth_certificate_link, cv_link=new_cv_link, team_id=None)
                    new_employee.insert()
                    
                    new_net_salary = request.form.get('net_salary', None)
                    new_salary = Salaries(salary=new_net_salary, employees_id=new_employee.id)
                    new_salary.insert()
                    if new_job_title == 'Sales Representative':
                        new_role = 'sales'
                    elif new_job_title == 'Admin':
                        new_role = 'admin'
                    elif new_job_title == 'Team Leader':
                        new_role = 'teamlead'
                    else:
                        new_role = 'user'
                    name_lowered = ((new_name.lower()).split(" "))[0]
                    password_con = name_lowered +'2021'
                    new_password = generate_password_hash(password_con, method='pbkdf2:sha256', salt_length=16)
                    
                    new_Credentials = Credentials(username=new_username, password=new_password, role=new_role, employees_id=new_employee.id, salaries_id=new_salary.id )
                    new_Credentials.insert()

                    if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
                        return redirect('/employees')
                    elif current_user.role == 'admin':
                        return redirect('/admin/dashboard')
                    elif current_user.role == 'manager':
                        return redirect('/manager/dashboard')
                else:
                    abort(422)
        else:
            abort(403)

    @app.route('/employees/<int:id>/edit', methods=['GET','POST'])
    @login_required
    def edit_employees(id):
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            if request.method == 'POST':
                employee = Employees.query.get(id)

                if not employee:
                    abort(404)
                try:
                    new_name = request.form.get('name', None)
                    new_id_number = request.form.get('id_number', None)
                    new_phone = request.form.get('phone', None)
                    new_date_of_birth = request.form.get('date_of_birth', None)
                    new_address = request.form.get('address', None)
                    new_qualifications = request.form.get('qualifications', None)
                    new_job_title = request.form.get('job_title', None)
                    new_id_link = request.form.get('id_link', None)
                    new_criminal_record_link = request.form.get('criminal_record_link', None)
                    new_birth_certificate_link = request.form.get('birth_certificate_link', None)
                    new_cv_link = request.form.get('cv_link', None)
                    new_username = request.form.get('username', None)
                    new_salary = request.form.get('salary', None)

                    employee.name=new_name
                    employee.id_number=new_id_number
                    employee.phone=new_phone
                    employee.date_of_birth=new_date_of_birth
                    employee.address=new_address
                    employee.qualifications=new_qualifications
                    employee.job_title=new_job_title
                    employee.id_link=new_id_link
                    employee.criminal_record_link=new_criminal_record_link
                    employee.birth_certificate_link=new_birth_certificate_link
                    employee.cv_link=new_cv_link
                    employee.update()
                    db.session.close()
                    
                    Credentials = Credentials.query.filter(Credentials.employees_id==id).one()
                    Credentials.username = new_username
                    Credentials.update()
                    db.session.close()

                    
                    return redirect('/employees/'+ str(id))
                except:
                    abort(422)
            employee = Employees.query.get(id)
            Credentials = Credentials.query.filter(Credentials.employee_id==id).one()

            return render_template('pages/general-manager/edit-employees.html', data={
                'sucess': True,
                'id': current_user.id,
                'employee_id': employee.id,
                'name': employee.name,
                'username': Credentials.username,
                'id_number': employee.id_number,
                'phone': employee.phone,
                'date_of_birth': employee.date_of_birth,
                'address': employee.address,
                'qualifications': employee.qualifications,
                'job_title': employee.job_title,
                'salary': salary.salary
            }), 200
        else:
            abort(403)

    @app.route('/employees/<int:id>', methods=['GET','POST'])
    @login_required
    def get_employee(id):
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            employee = Employees.query.get(id)
            if not employee:
                abort(404)
            credential = Credentials.query.filter(Credentials.employees_id == employee.employees_id).one()
            return render_template('pages/general-manager/employee.html', data={
                'sucess': True,
                'id': current_user.id,
                'employee_id': employee.id,
                'name': employee.name,
                'username': credential.username,
                'id_number': employee.id_number,
                'phone': employee.phone,
                'date_of_birth': employee.date_of_birth,
                'address': employee.address,
                'qualifications': employee.qualifications,
                'job_title': employee.job_title
            }), 200
        elif current_user.role == 'admin':
            employee = Employees.query.get(id)
            if not employee:
                abort(404)
            credential = Credentials.query.filter(Credentials.employees_id == employee.employees_id).one()
            return render_template('pages/admin/employee-view.html', data={
                'sucess': True,
                'id': current_user.id,
                'name': employee.name,
                'username': credential.username,
                'id_number': employee.id_number,
                'phone': employee.phone,
                'date_of_birth': employee.date_of_birth,
                'address': employee.address,
                'qualifications': employee.qualifications,
                'job_title': employee.job_title
            }), 200
        elif current_user.role == 'manager':
            employee = Employees.query.get(id)
            if not employee:
                abort(404)
            Credentials = Credentials.query.filter(Credentials.employees_id == employee.employees_id).one()
            return render_template('pages/manager/employee-view.html', data={
                'sucess': True,
                'id': current_user.id,
                'name': employee.name,
                'username': Credentials.username,
                'id_number': employee.id_number,
                'phone': employee.phone,
                'date_of_birth': employee.date_of_birth,
                'address': employee.address,
                'qualifications': employee.qualifications,
                'job_title': employee.job_title
            }), 200
        else:
            abort(403)

    """
    Employee
    """

    @app.route('/employee/<int:id>', methods=['GET','POST'])
    @login_required
    def get_employee_view(id):
        if current_user.employee_id == id:
            employee = Employees.query.get(current_user.employee_id)
            if not employee:
                abort(404)
            credential = Credentials.query.filter(Credentials.employee_id == employee.employees_id).one()
            if current_user.role == 'sales':
                return render_template('pages/sales/employee-view.html', data={
                    'sucess': True,
                    'id': id,
                    'employee_id': employee.employees_id,
                    'name': employee.f_name +' '+employee.l_name,
                    'username': credential.username,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications
                }), 200
            elif current_user.role == 'admin':
                return render_template('pages/admin/employee-view-edit.html', data={
                    'sucess': True,
                    'id': id,
                    'employee_id': employee.employees_id,
                    'name': employee.f_name +' '+employee.l_name,
                    'username': credential.username,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications
                }), 200
            elif current_user.role == 'manager':
                return render_template('pages/manager/employee-view-edit.html', data={
                    'sucess': True,
                    'id': id,
                    'employee_id': employee.employees_id,
                    'name': employee.f_name +' '+employee.l_name,
                    'username': credential.username,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications
                }), 200
            elif current_user.role == 'teamlead':
                return render_template('pages/teamlead/employee-view-edit.html', data={
                    'sucess': True,
                    'id': id,
                    'employee_id': employee.employees_id,
                    'name': employee.f_name +' '+employee.l_name,
                    'username': credential.username,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications
                }), 200
        else:
            abort(403)

    @app.route('/settings/<int:id>')
    @login_required
    def settings(id):
        if current_user.employee_id == id:
            if current_user.role == 'gm':
                return render_template('pages/general-manager/settings.html', data={'id': current_user.employee_id})
            elif current_user.role == 'admin':
                return render_template('pages/admin/settings.html', data={'id': current_user.employee_id})
            elif current_user.role == 'manager':
                return render_template('pages/manager/settings.html', data={'id': current_user.employee_id})
            elif current_user.role == 'sales':
                return render_template('pages/sales/settings.html', data={'id': current_user.employee_id})
            elif current_user.role == 'teamlead':
                return render_template('pages/teamlead/settings.html', data={'id': current_user.employee_id})
        else:
            abort(403)
    
    @app.route('/security/<int:id>', methods=['GET', 'POST'])
    @login_required
    def security(id):     
        if current_user.employee_id == id or current_user.role == 'gm':
            if request.method == 'POST':
                old_password = request.form.get('old_password', None)
                new_password = request.form.get('new_password', None)
                credential = Credentials.query.filter(Credentials.employee_id == id).one()
                if not credential.password == old_password:
                    if current_user.role == 'gm':
                        flash('Please check your old password')
                        return render_template('pages/general-manager/change-password.html', data={'id': current_user.employee_id})
                    elif current_user.role == 'admin':
                        flash('Please check your old password')
                        return render_template('pages/admin/change-password.html', data={'id': current_user.employee_id})
                    elif current_user.role == 'manager':
                        flash('Please check your old password')
                        return render_template('pages/manager/change-password.html', data={'id': current_user.employee_id})
                    elif current_user.role == 'teamlead':
                        flash('Please check your old password')
                        return render_template('pages/teamlead/change-password.html', data={'id': current_user.employee_id})
                    else:
                        flash('Please check your old password')
                        return render_template('pages/sales/change-password.html', data={'id': current_user.employee_id})  
                else:
                    credential.password = new_password
                    credential.update()
                    db.session.close()
                    return redirect('/employee/'+str(id))
            else:
                if current_user.role =='gm':
                    return render_template('pages/general-manager/change-password.html', data={'id': current_user.employee_id})
                elif current_user.role == 'admin':
                    return render_template('pages/admin/change-password.html', data={'id': current_user.employee_id})
                elif current_user.role == 'manager':
                    return render_template('pages/manager/change-password.html', data={'id': current_user.employee_id})
                elif current_user.role=='sales':
                    return render_template('pages/sales/change-password.html', data={'id': current_user.employee_id})
                elif current_user.role=='teamlead':
                    return render_template('pages/teamlead/change-password.html', data={'id': current_user.employee_id})
        else:
            abort(403)
    
    @app.route('/deals/<int:id>', methods=['GET'])
    @login_required
    def get_employee_deals(id):
        if current_user.employee_id == id:
            selection = Deals.query.filter(Deals.assigned_to_id == current_user.employee_id).all()
            current_deals = [result.format() for result in selection]
            for a in current_deals:
                if a['assigned_to_id']:
                    assigned_to_name = db.session.query(Employees.employees_id, Employees.f_name, Employees.l_name).filter(Employees.employees_id == a['assigned_to_id'] ).first()
                    a['assigned_to_name'] = assigned_to_name.f_name + ' ' + assigned_to_name.l_name
                if a['project_id']:
                    project_data = db.session.query(Projects.projects_id, Projects.name, Projects.location, Projects.commission, Projects.type, Projects.unit_price).filter(Projects.projects_id == a['project_id'] ).first()
                    a['project_name'] = project_data.name
                    a['project_type'] = project_data.type
                    a['unit_price'] = project_data.unit_price
                    a['location'] = project_data.location
                    a['commission'] = project_data.commission
                if a['time_created']:
                    a['time_created'] = datetime_from_utc_to_local(a['time_created'])
            if current_user.role == 'teamlead': 
                return render_template('pages/teamlead/employee-deals.html', data={
                    'sucess': True,
                    'id': id,
                    'deals': current_deals,
                }), 200
            else:
                return render_template('pages/sales/employee-deals.html', data={
                    'sucess': True,
                    'id': id,
                    'deals': current_deals,
                }), 200
        else:
            abort(403)

    """
    Manager
    """
    @app.route('/manager/dashboard')
    @login_required
    def manager_dashboard():
        if current_user.role == 'manager':
            employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager', Employees.job_title == 'Key Account', Employees.job_title == 'Admin')).all()
            current_time = datetime.now(timezone.utc).date()
            tot_fresh = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'National').count()
            tot_new_international = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'International').count()
            tot_new_cold_international = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type == 'International').count()
            tot_new_cold = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type=='National').count()
            tot_delayed = Leads.query.filter(func.date(Leads.next_follow_up) < current_time).count()
            tot_followups = Leads.query.filter(func.date(Leads.next_follow_up) == current_time).count()
            data = {"id": current_user.employees_id, "tot_fresh": tot_fresh, "tot_new_international": tot_new_international,"tot_new_cold":tot_new_cold, 'tot_new_cold_international':tot_new_cold_international, "tot_delayed":tot_delayed,"tot_followups": tot_followups, "employees":[]}
            for employee in employees:
                num_fresh = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'New', Leads.lead_type == 'National').count()
                num_new_international = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').count()
                num_new_cold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'New Cold', Leads.lead_type=='National').count()
                num_delayed = Leads.query.filter(Leads.assigned_to == employee.id, func.date(Leads.next_follow_up) < current_time).count()
                num_followups = Leads.query.filter(Leads.assigned_to == employee.id, func.date(Leads.next_follow_up) == current_time).count()
                num_interested_follow = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Interested Follow').count()
                num_interested_hold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Interested Hold').count()
                num_promise_visit = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Promise Visit').count()
                num_eoi = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'EOI').count()
                num_waiting = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Waiting').count()
                num_meeting = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Meeting').count()
                num_pre_no_answer = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Pre No Answer').count()
                num_contact_in_future = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Contact in Future').count()
                num_won = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Won').count()
                num_lost = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Lost').count()
                num_not_interested = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Interested').count()
                num_low_budget = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Low Budget').count()
                num_not_interested_now = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Interested Now').count()
                num_no_answer = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer').count()
                num_no_answer_hold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer Hold').count()
                num_no_answer_follow = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer Follow').count()
                num_not_reached = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Reached').count()
                num_total_leads = Leads.query.filter(Leads.assigned_to == employee.id).count()
                data['employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_fresh': num_fresh,
                    'num_new_cold': num_new_cold,
                    'num_new_international': num_new_international,
                    'num_followups': num_followups,
                    'num_delayed': num_delayed,
                    'num_interested_follow': num_interested_follow,
                    'num_interested_hold': num_interested_hold,
                    'num_promise_visit': num_promise_visit,
                    'num_pre_no_answer': num_pre_no_answer,
                    'num_contact_in_future': num_contact_in_future,
                    'num_eoi': num_eoi,
                    'num_waiting': num_waiting,
                    'num_meeting': num_meeting,
                    'num_won': num_won,
                    'num_lost': num_lost,
                    'num_not_interested': num_not_interested,
                    'num_low_budget': num_low_budget,
                    'num_not_interested_now': num_not_interested_now,
                    'num_no_answer': num_no_answer,
                    'num_no_answer_hold': num_no_answer_hold,
                    'num_no_answer_follow': num_no_answer_follow,
                    'num_not_reached': num_not_reached,
                    'num_total_leads': num_total_leads
                    })
            return render_template('pages/manager/dashboard.html', data=data), 200
        else: 
            abort(403)
    
    @app.route('/manager/visits-report', methods=['GET','POST'])
    @login_required
    def get_manager__visits_repor():
        if current_user.role == 'manager':
            channels = ['Inbound', 'Form', 'Night Call', 'Whatsapp', 'Inbox','Self Add', 'Medical', 'Marasi', 'Message', None]
            data = {"id": current_user.employees_id, "channels":[]}
            for channel in channels:
                num_facebook = Leads.query.filter(Leads.channel == channel, Leads.source =='Facebook', Leads.visit_date != None).count()
                num_instagram = Leads.query.filter(Leads.channel == channel, Leads.source =='Instagram', Leads.visit_date != None).count()
                num_google = Leads.query.filter(Leads.channel == channel, Leads.source =='Google', Leads.visit_date != None).count()
                num_outdoor = Leads.query.filter(Leads.channel == channel, Leads.source =='Outdoor', Leads.visit_date != None).count()
                num_website = Leads.query.filter(Leads.channel == channel, Leads.source =='Website', Leads.visit_date != None).count()
                num_cold_data = Leads.query.filter(Leads.channel == channel, Leads.source =='Cold Data', Leads.visit_date != None).count()
                num_sms = Leads.query.filter(Leads.channel == channel, Leads.source =='SMS', Leads.visit_date != None).count()
                num_property_finder = Leads.query.filter(Leads.channel == channel, Leads.source =='Property Finder', Leads.visit_date != None).count()
                num_event = Leads.query.filter(Leads.channel == channel, Leads.source =='Website', Leads.visit_date != None).count()
                num_expo = Leads.query.filter(Leads.channel == channel, Leads.source =='Expo', Leads.visit_date != None).count()
                num_olx = Leads.query.filter(Leads.channel == channel, Leads.source =='OLX', Leads.visit_date != None).count()
                num_p_data = Leads.query.filter(Leads.channel == channel, Leads.source =='P. Data', Leads.visit_date != None).count()
                num_none = Leads.query.filter(Leads.channel == channel, Leads.source ==None, Leads.visit_date != None).count()

                data['channels'].append({
                    'channel_name': channel,
                    'num_none': num_none,
                    'num_facebook': num_facebook,
                    'num_instagram': num_instagram,
                    'num_google': num_google,
                    'num_outdoor': num_outdoor,
                    'num_website': num_website,
                    'num_cold_data': num_cold_data,
                    'num_sms': num_sms,
                    'num_property_finder': num_property_finder,
                    'num_event': num_event,
                    'num_expo': num_expo,
                    'num_olx': num_olx,
                    'num_p_data': num_p_data
                    })
            return render_template('pages/manager/visits-report.html', data=data), 200
        else:
            abort(403)

    @app.route('/manager/sales-report', methods=['GET','POST'])
    @login_required
    def get_manager_sales_repor():
        if current_user.role == 'manager':
            employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Admin', Employees.job_title == 'Key Account')).all()
            
            tot_num_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'International').count()
            tot_num_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'International').count()
            tot_num_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'International').count()
            tot_local_num_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'National').count()
            tot_local_num_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'National').count()
            tot_local_num_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'National').count()
            
            tot_num_total_leads = tot_num_qualified + tot_num_neutral + tot_num_not_qualified + tot_local_num_qualified + tot_local_num_neutral + tot_local_num_not_qualified

            tot_per_qualified = ((tot_num_qualified / tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_per_qualified = round(tot_per_qualified, 2 )

            tot_per_neutral = ((tot_num_neutral/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_per_neutral = round(tot_per_neutral, 2)

            tot_per_not_qualified = ((tot_num_not_qualified/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_per_not_qualified = round(tot_per_not_qualified, 2)

            tot_num_cold_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'International').count()
            tot_num_cold_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'International').count()
            tot_num_cold_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'International').count()
            tot_local_num_cold_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'National').count()
            tot_local_num_cold_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'National').count()
            tot_local_num_cold_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'National').count()
            
            tot_num_cold_total_leads = tot_num_cold_qualified + tot_num_cold_neutral + tot_num_cold_not_qualified + tot_local_num_cold_qualified + tot_local_num_cold_neutral + tot_local_num_cold_not_qualified

            tot_per_cold_qualified = ((tot_num_cold_qualified / tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_per_cold_qualified = round(tot_per_cold_qualified, 2 )

            tot_per_cold_neutral = ((tot_num_cold_neutral/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_per_cold_neutral = round(tot_per_cold_neutral, 2)

            tot_per_cold_not_qualified = ((tot_num_cold_not_qualified/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_per_cold_not_qualified = round(tot_per_cold_not_qualified, 2)

            tot_local_per_qualified = ((tot_local_num_qualified / tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_local_per_qualified = round(tot_local_per_qualified, 2 )

            tot_local_per_neutral = ((tot_local_num_neutral/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_local_per_neutral = round(tot_local_per_neutral, 2)

            tot_local_per_not_qualified = ((tot_local_num_not_qualified/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_local_per_not_qualified = round(tot_local_per_not_qualified, 2)


            tot_local_per_cold_qualified = ((tot_local_num_cold_qualified / tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_local_per_cold_qualified = round(tot_local_per_cold_qualified, 2 )

            tot_local_per_cold_neutral = ((tot_local_num_cold_neutral/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_local_per_cold_neutral = round(tot_local_per_cold_neutral, 2)

            tot_local_per_cold_not_qualified = ((tot_local_num_cold_not_qualified/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_local_per_cold_not_qualified = round(tot_local_per_cold_not_qualified, 2)

            data = {"id": current_user.employees_id, 'tot_num_qualified': tot_num_qualified, 'tot_num_neutral':tot_num_neutral, 'tot_num_not_qualified': tot_num_not_qualified, 'tot_num_total_leads': tot_num_total_leads, 'tot_per_qualified': tot_per_qualified, 'tot_per_neutral': tot_per_neutral,'tot_per_not_qualified': tot_per_not_qualified, 'tot_num_cold_qualified': tot_num_cold_qualified, 'tot_num_cold_neutral':tot_num_cold_neutral, 'tot_num_cold_not_qualified': tot_num_cold_not_qualified, 'tot_num_cold_total_leads': tot_num_cold_total_leads, 'tot_per_cold_qualified': tot_per_cold_qualified, 'tot_per_cold_neutral': tot_per_cold_neutral,'tot_per_cold_not_qualified': tot_per_cold_not_qualified, 'tot_local_num_qualified': tot_local_num_qualified, 'tot_local_num_neutral': tot_local_num_neutral, 'tot_local_num_not_qualified': tot_local_num_not_qualified, 'tot_local_per_qualified': tot_local_per_qualified, 'tot_local_per_neutral': tot_local_per_neutral,'tot_local_per_not_qualified': tot_local_per_not_qualified, 'tot_local_num_cold_qualified': tot_local_num_cold_qualified, 'tot_local_num_cold_neutral':tot_local_num_cold_neutral, 'tot_local_num_cold_not_qualified': tot_local_num_cold_not_qualified, 'tot_local_per_cold_qualified': tot_local_per_cold_qualified, 'tot_local_per_cold_neutral': tot_local_per_cold_neutral,'tot_local_per_cold_not_qualified': tot_local_per_cold_not_qualified, "employees":[], "cold_employees": []}
            for employee in employees:
                num_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'International').count()
                num_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'International').count()
                num_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'International').count()
                num_local_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'National').count()
                num_local_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'National').count()
                num_local_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'National').count()
                num_total_leads = num_qualified + num_neutral + num_not_qualified + num_local_qualified + num_local_neutral + num_local_not_qualified
                per_qualified = ((num_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_qualified = round(per_qualified, 2)
                per_neutral = ((num_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_neutral = round(per_neutral, 2)
                per_not_qualified = ((num_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_not_qualified = round(per_not_qualified, 2)
                per_local_qualified = ((num_local_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_qualified = round(per_local_qualified, 2)
                per_local_neutral = ((num_local_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_neutral = round(per_local_neutral, 2)
                per_local_not_qualified = ((num_local_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_not_qualified = round(per_local_not_qualified, 2)
                data['employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_qualified': num_qualified,
                    'per_qualified': per_qualified,
                    'num_neutral': num_neutral,
                    'per_neutral': per_neutral,
                    'num_not_qualified': num_not_qualified,
                    'per_not_qualified': per_not_qualified,
                    'num_local_qualified': num_local_qualified,
                    'per_local_qualified': per_local_qualified,
                    'num_local_neutral': num_local_neutral,
                    'per_local_neutral': per_local_neutral,
                    'num_local_not_qualified': num_local_not_qualified,
                    'per_local_not_qualified': per_local_not_qualified,
                    'num_total_leads': num_total_leads
                    })
            for employee in employees:
                num_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'International').count()
                num_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'International').count()
                num_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'International').count()
                num_local_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'National').count()
                num_local_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'National').count()
                num_local_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'National').count()
                num_total_leads = num_qualified + num_neutral + num_not_qualified + num_local_qualified + num_local_neutral + num_local_not_qualified
                per_qualified = ((num_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_qualified = round(per_qualified, 2)
                per_neutral = ((num_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_neutral = round(per_neutral, 2)
                per_not_qualified = ((num_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_not_qualified = round(per_not_qualified, 2)
                per_local_qualified = ((num_local_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_qualified = round(per_local_qualified, 2)
                per_local_neutral = ((num_local_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_neutral = round(per_local_neutral, 2)
                per_local_not_qualified = ((num_local_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_not_qualified = round(per_local_not_qualified, 2)
                data['cold_employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_qualified': num_qualified,
                    'per_qualified': per_qualified,
                    'num_neutral': num_neutral,
                    'per_neutral': per_neutral,
                    'num_not_qualified': num_not_qualified,
                    'per_not_qualified': per_not_qualified,
                    'num_local_qualified': num_local_qualified,
                    'per_local_qualified': per_local_qualified,
                    'num_local_neutral': num_local_neutral,
                    'per_local_neutral': per_local_neutral,
                    'num_local_not_qualified': num_local_not_qualified,
                    'per_local_not_qualified': per_local_not_qualified,
                    'num_total_leads': num_total_leads
                    })
            return render_template('pages/manager/sales-report.html', data=data), 200
        else:
            abort(403)

    @app.route('/manager/sales-report/date-new', methods=['POST'])
    @login_required
    def new_sales_report_date():
        body = request.get_json()
        start_date = body.get('start_date', None)
        end_date = body.get('end_date', None)

        try:
            employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Admin', Employees.job_title == 'Key Account')).all()
            
            tot_num_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_num_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_num_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_local_num_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_local_num_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_local_num_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            
            tot_num_total_leads = tot_num_qualified + tot_num_neutral + tot_num_not_qualified + tot_local_num_qualified + tot_local_num_neutral + tot_local_num_not_qualified

            tot_per_qualified = ((tot_num_qualified / tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_per_qualified = round(tot_per_qualified, 2 )

            tot_per_neutral = ((tot_num_neutral/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_per_neutral = round(tot_per_neutral, 2)

            tot_per_not_qualified = ((tot_num_not_qualified/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_per_not_qualified = round(tot_per_not_qualified, 2)

            tot_local_per_qualified = ((tot_local_num_qualified / tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_local_per_qualified = round(tot_local_per_qualified, 2 )

            tot_local_per_neutral = ((tot_local_num_neutral/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_local_per_neutral = round(tot_local_per_neutral, 2)

            tot_local_per_not_qualified = ((tot_local_num_not_qualified/tot_num_total_leads) * 100) if tot_num_total_leads != 0 else 0
            tot_local_per_not_qualified = round(tot_local_per_not_qualified, 2)

            data = {"id": current_user.employees_id, 'tot_num_qualified': tot_num_qualified, 'tot_num_neutral':tot_num_neutral, 'tot_num_not_qualified': tot_num_not_qualified, 'tot_num_total_leads': tot_num_total_leads, 'tot_per_qualified': tot_per_qualified, 'tot_per_neutral': tot_per_neutral,'tot_per_not_qualified': tot_per_not_qualified, 'tot_local_num_qualified': tot_local_num_qualified, 'tot_local_num_neutral': tot_local_num_neutral, 'tot_local_num_not_qualified': tot_local_num_not_qualified, 'tot_local_per_qualified': tot_local_per_qualified, 'tot_local_per_neutral': tot_local_per_neutral,'tot_local_per_not_qualified': tot_local_per_not_qualified, "employees":[]}
            for employee in employees:
                num_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_local_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_local_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_local_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_total_leads = num_qualified + num_neutral + num_not_qualified + num_local_qualified + num_local_neutral + num_local_not_qualified
                per_qualified = ((num_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_qualified = round(per_qualified, 2)
                per_neutral = ((num_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_neutral = round(per_neutral, 2)
                per_not_qualified = ((num_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_not_qualified = round(per_not_qualified, 2)
                per_local_qualified = ((num_local_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_qualified = round(per_local_qualified, 2)
                per_local_neutral = ((num_local_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_neutral = round(per_local_neutral, 2)
                per_local_not_qualified = ((num_local_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_not_qualified = round(per_local_not_qualified, 2)
                data['employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_qualified': num_qualified,
                    'per_qualified': per_qualified,
                    'num_neutral': num_neutral,
                    'per_neutral': per_neutral,
                    'num_not_qualified': num_not_qualified,
                    'per_not_qualified': per_not_qualified,
                    'num_local_qualified': num_local_qualified,
                    'per_local_qualified': per_local_qualified,
                    'num_local_neutral': num_local_neutral,
                    'per_local_neutral': per_local_neutral,
                    'num_local_not_qualified': num_local_not_qualified,
                    'per_local_not_qualified': per_local_not_qualified,
                    'num_total_leads': num_total_leads
                })
            return jsonify({
                'success': True,
                'data': data
            }), 200
        except:
            abort(403)

    @app.route('/manager/sales-report/date-cold', methods=['POST'])
    @login_required
    def cold_sales_report_date():
        body = request.get_json()
        start_date = body.get('start_date', None)
        end_date = body.get('end_date', None)

        try:
            employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Admin', Employees.job_title == 'Key Account')).all()
            
            tot_num_cold_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_num_cold_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_num_cold_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_local_num_cold_qualified = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_local_num_cold_neutral = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            tot_local_num_cold_not_qualified = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
            
            tot_num_cold_total_leads = tot_num_cold_qualified + tot_num_cold_neutral + tot_num_cold_not_qualified + tot_local_num_cold_qualified + tot_local_num_cold_neutral + tot_local_num_cold_not_qualified

            tot_per_cold_qualified = ((tot_num_cold_qualified / tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_per_cold_qualified = round(tot_per_cold_qualified, 2 )

            tot_per_cold_neutral = ((tot_num_cold_neutral/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_per_cold_neutral = round(tot_per_cold_neutral, 2)

            tot_per_cold_not_qualified = ((tot_num_cold_not_qualified/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_per_cold_not_qualified = round(tot_per_cold_not_qualified, 2)

            tot_local_per_cold_qualified = ((tot_local_num_cold_qualified / tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_local_per_cold_qualified = round(tot_local_per_cold_qualified, 2 )

            tot_local_per_cold_neutral = ((tot_local_num_cold_neutral/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_local_per_cold_neutral = round(tot_local_per_cold_neutral, 2)

            tot_local_per_cold_not_qualified = ((tot_local_num_cold_not_qualified/tot_num_cold_total_leads) * 100) if tot_num_cold_total_leads != 0 else 0
            tot_local_per_cold_not_qualified = round(tot_local_per_cold_not_qualified, 2)

            data = {"id": current_user.employees_id, 'tot_num_cold_qualified': tot_num_cold_qualified, 'tot_num_cold_neutral':tot_num_cold_neutral, 'tot_num_cold_not_qualified': tot_num_cold_not_qualified, 'tot_num_cold_total_leads': tot_num_cold_total_leads, 'tot_per_cold_qualified': tot_per_cold_qualified, 'tot_per_cold_neutral': tot_per_cold_neutral,'tot_per_cold_not_qualified': tot_per_cold_not_qualified, 'tot_local_num_cold_qualified': tot_local_num_cold_qualified, 'tot_local_num_cold_neutral':tot_local_num_cold_neutral, 'tot_local_num_cold_not_qualified': tot_local_num_cold_not_qualified, 'tot_local_per_cold_qualified': tot_local_per_cold_qualified, 'tot_local_per_cold_neutral': tot_local_per_cold_neutral,'tot_local_per_cold_not_qualified': tot_local_per_cold_not_qualified, "cold_employees": []}

            for employee in employees:
                num_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'International', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_local_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_local_neutral = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold',  Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_local_not_qualified = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type == 'National', and_(Leads.created_time >= start_date, Leads.created_time <= end_date)).count()
                num_total_leads = num_qualified + num_neutral + num_not_qualified + num_local_qualified + num_local_neutral + num_local_not_qualified
                per_qualified = ((num_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_qualified = round(per_qualified, 2)
                per_neutral = ((num_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_neutral = round(per_neutral, 2)
                per_not_qualified = ((num_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_not_qualified = round(per_not_qualified, 2)
                per_local_qualified = ((num_local_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_qualified = round(per_local_qualified, 2)
                per_local_neutral = ((num_local_neutral/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_neutral = round(per_local_neutral, 2)
                per_local_not_qualified = ((num_local_not_qualified/num_total_leads) * 100) if num_total_leads != 0 else 0
                per_local_not_qualified = round(per_local_not_qualified, 2)
                data['cold_employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_qualified': num_qualified,
                    'per_qualified': per_qualified,
                    'num_neutral': num_neutral,
                    'per_neutral': per_neutral,
                    'num_not_qualified': num_not_qualified,
                    'per_not_qualified': per_not_qualified,
                    'num_local_qualified': num_local_qualified,
                    'per_local_qualified': per_local_qualified,
                    'num_local_neutral': num_local_neutral,
                    'per_local_neutral': per_local_neutral,
                    'num_local_not_qualified': num_local_not_qualified,
                    'per_local_not_qualified': per_local_not_qualified,
                    'num_total_leads': num_total_leads
                })
            return jsonify({
                'success': True,
                'data': data
            }), 200
        except:
            abort(403)

    @app.route('/manager/leads/<int:id>/new-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-neutral/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_neutral_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200
    
    @app.route('/manager/leads/<int:id>/new-not-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_not_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-total-not-qualified', methods=['GET'])
    @login_required
    def manager_get_new_tot_not_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-total-neutral', methods=['GET'])
    @login_required
    def manager_get_new_tot_neutral_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-total-qualified', methods=['GET'])
    @login_required
    def manager_get_new_tot_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-total/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_total_new_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.round == 'New').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200


    @app.route('/manager/leads/<int:id>/cold-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_cold_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-neutral/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_cold_neutral_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200
    
    @app.route('/manager/leads/<int:id>/cold-not-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_cold_not_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-total-not-qualified', methods=['GET'])
    @login_required
    def manager_get_cold_tot_not_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-total-neutral', methods=['GET'])
    @login_required
    def manager_get_cold_tot_neutral_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-total-qualified', methods=['GET'])
    @login_required
    def manager_get_cold_tot_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type =="International").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-total/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_total_cold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.round == 'New Cold').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-local-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_local_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-local-neutral/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_local_neutral_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200
    
    @app.route('/manager/leads/<int:id>/new-local-not-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_local_not_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-total-local-not-qualified', methods=['GET'])
    @login_required
    def manager_get_new_local_tot_not_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-cold-local-total-neutral', methods=['GET'])
    @login_required
    def manager_get_new_local_tot_neutral_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-cold-local-total-qualified', methods=['GET'])
    @login_required
    def manager_get_new_cold_local_tot_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new-local-total/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_total_new_local_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.round == 'New', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200


    @app.route('/manager/leads/<int:id>/cold-local-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_cold_local_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-local-neutral/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_cold_local_neutral_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200
    
    @app.route('/manager/leads/<int:id>/cold-local-not-qualified/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_cold_local_not_qualified_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-local-total-not-qualified', methods=['GET'])
    @login_required
    def manager_get_cold_local_tot_not_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Not Interested Now', Leads.status == 'Not Interested', Leads.status == 'No Answer', Leads.status == 'Not Reached', Leads.status =='Lost', Leads.status == 'Low Budget'), Leads.round == 'New Cold', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-local-total-neutral', methods=['GET'])
    @login_required
    def manager_get_cold_local_tot_neutral_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'New', Leads.status == 'New Cold', Leads.status == 'Pre No Answer'), Leads.round == 'New Cold', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/cold-local-total-qualified', methods=['GET'])
    @login_required
    def manager_get_local_cold_tot_qualified_leads(id):
        selection = Leads.query.filter(or_(Leads.status == 'Interested Follow', Leads.status == 'Meeting', Leads.status == 'Promise Visit', Leads.status == 'Interested Hold', Leads.status == 'Contact in Future', Leads.status == 'Waiting', Leads.status =='No Answer Hold', Leads.status == 'No Answer Follow', Leads.status == 'Won'), Leads.round == 'New Cold', Leads.lead_type =="National").all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route("/manager/import", methods=['GET', 'POST'])
    @login_required
    def manager_doimport():
        if request.method == 'POST':
            uploaded_file = request.files['file']
            if uploaded_file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
                new_status = request.form.get('status', None)
                new_lead_type = request.form.get('lead_type', None)
                new_country = request.form.get('country', None)
                new_current_time= datetime.utcnow()
                # set the file path
                uploaded_file.save(file_path)
                col_names = ['client_name','phone', 'second_phone','email','description', 'request', 'channel', 'source', 'ad_details', 'campaign', 'round', 'assigned_to', 'client_job']
                df = pd.read_excel(file_path, names=col_names, dtype={'phone': str, 'second_phone': str})
                preassigned_to = [current_user.employees_id]*len(df)
                if new_status == 'New Cold':
                    status = ['New Cold']*len(df)
                else:
                    status = ['New']*len(df)
                lead_type = [new_lead_type]*len(df)
                country = [new_country] *len(df)
                new_current_time = [new_current_time] *len(df)
                df.insert(0, "preassigned_to", preassigned_to)
                df.insert(0, "status", status)
                df.insert(0, "lead_type", lead_type)
                df.insert(0, "country", country)
                df.insert(0, "created_time", new_current_time)
                df['assigned_to'] = df['assigned_to'].astype(str)
                df['assigned_to'] = df['assigned_to'].fillna(current_user.employees_id)
                new_leads = pd.DataFrame(columns = list(df.columns))
                dublicate_leads = pd.DataFrame(columns = list(df.columns))
                os.remove(file_path)
                for index, row in df.iterrows():
                    if Leads.query.filter(Leads.phone == row['phone']).first():
                        lead = Leads.query.filter(Leads.phone == row['phone']).first()
                        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
                        df['assigned_to'] = df['assigned_to'].astype(str)
                        df.at[index, 'assigned_to'] = assigned_to_name.name
                        dublicate_leads = dublicate_leads.append(df.iloc[index])
                    else:
                        assigned_to = db.session.query(Employees.id, Employees.name).filter(Employees.name == row['assigned_to']).one_or_none()
                        if assigned_to:
                            df.at[index, 'assigned_to'] = assigned_to.id
                            df['assigned_to'] = df['assigned_to'].astype(str)
                            new_leads = new_leads.append(df.iloc[index])
                            new_leads['assigned_to'] = new_leads['assigned_to'].astype(int)
                        else:
                            df.at[index, 'assigned_to'] = current_user.employees_id
                            df['assigned_to'] = df['assigned_to'].astype(str)
                            new_leads = new_leads.append(df.iloc[index])
                            new_leads['assigned_to'] = new_leads['assigned_to'].astype(int)
                for index1, row1 in df.iterrows():
                    times = 0
                    for index2, row2 in new_leads.iterrows():
                        if row1['phone'] == row2['phone']:
                            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == current_user.employees_id).first()
                            df['assigned_to'] = df['assigned_to'].astype(str)
                            df.at[index1, 'assigned_to'] = assigned_to_name.name
                            times = times + 1
                            if times > 1:
                                dublicate_leads = dublicate_leads.append(df.iloc[index1])
                                times = 0
                        else:
                            pass
                
                new_leads.drop_duplicates(subset='phone', keep='first', inplace=True)
                
                new_leads_json = new_leads.to_json(orient='records')
                dublicate_leads_json = dublicate_leads.to_json(orient='records')
                
                new_leads.to_excel(os.path.join(app.config['UPLOAD_FOLDER'], 'new_leads.xlsx'), index=False)
                dublicate_leads.to_excel(os.path.join(app.config['UPLOAD_FOLDER'], 'dublicate_leads.xlsx'), index=False)
                return render_template('/pages/manager/leads-stage.html', data={'id': current_user.employees_id, 'new_leads': json.loads(new_leads_json), 'dublicate_leads': json.loads(dublicate_leads_json)})
        return render_template('pages/manager/add-lead-excel.html', data={'id': current_user.employees_id})


    @app.route("/manager/confirm-import", methods=['GET'])
    @login_required
    def manager_save_imported_data():
            new_leads_path =os.path.join(app.config['UPLOAD_FOLDER'], 'new_leads.xlsx')
            dublicate_leads_path = os.path.join(app.config['UPLOAD_FOLDER'], 'dublicate_leads.xlsx')
            os.remove(dublicate_leads_path)
            col_names = ['created_time','country', 'lead_type','status', 'preassigned_to', 'client_name','phone','second_phone', 'email','description', 'request', 'channel', 'source', 'ad_details', 'campaign', 'round', 'assigned_to', 'client_job']
            df = pd.read_excel(new_leads_path, names=col_names, dtype={'phone': str, 'second_phone': str })
            engine= db.engine
            df.to_sql('leads', con=engine, if_exists='append', index=False)
            os.remove(new_leads_path)
            sql_command1="""UPDATE leads SET whatsapp_link=CONCAT('https://wa.me/+', phone) WHERE phone LIKE '9%';"""

            sql_command2="""UPDATE leads SET whatsapp_link=CONCAT('https://wa.me/+2', phone) WHERE phone LIKE '01%';"""
            db.session.execute(text(sql_command1))
            db.session.commit()
            db.session.execute(text(sql_command2))
            db.session.commit()
            return redirect('/manager/leads/'+ str(current_user.employees_id))

    @app.route('/manager/<int:id>/select-assign-lead/<int:lead_id>', methods=['PATCH'])
    @login_required
    def select_assign_manager_lead(id, lead_id):
        body = request.get_json()
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        try:
            new_assigned_to = body.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return jsonify({
                    'success': True,
                }), 200
        except:
            abort(404)

    @app.route('/manager/leads/<int:id>/total-new', methods=['GET'])
    @login_required
    def manager_get_all_new_leads(id):
        selection = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/total-new-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/total-followup', methods=['GET'])
    @login_required
    def manager_get_all_followup_leads(id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(func.date(Leads.next_follow_up) == current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/total-followup-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/total-delayed', methods=['GET'])
    @login_required
    def manager_get_all_delayed_leads(id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(func.date(Leads.next_follow_up) < current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/total-delayed-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/total-newcold', methods=['GET'])
    @login_required
    def manager_get_all_new_cold_leads(id):
        selection = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/total-newcold-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/total-newglobal', methods=['GET'])
    @login_required
    def manager_get_all_new_global_leads(id):
        selection = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'International').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/total-newglobal-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/total-coldglobal', methods=['GET'])
    @login_required
    def manager_get_all_cold_global_leads(id):
        selection = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type == 'International').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/total-coldglobal-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/new/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_new_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'New', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/followup/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_followup_leads(id, employee_id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(Leads.assigned_to == employee_id, func.date(Leads.next_follow_up) == current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/delayed/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_delayed_leads(id, employee_id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(Leads.assigned_to == employee_id, func.date(Leads.next_follow_up) < current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/newcold/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_new_cold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'New Cold', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/newglobal/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_new_global_leads(id, employee_id):
            selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').all()
            current_leads = [result.format() for result in selection]
            all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            return render_template('pages/manager/small-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads,
                'all_sales': all_sales,
            }), 200

    @app.route('/manager/leads/<int:id>/interested-hold/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_interested_hold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Interested Hold').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/interested-follow/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_interested_follow_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Interested Follow').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/not-interested/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_not_interested_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Interested').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/total-leads/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_total_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager', Employees.job_title=='Key Account', Employees.job_title=='Admin')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/manager/leads/<int:id>/promise-visit/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_promise_visit_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Promise Visit').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200
    
    @app.route('/manager/leads/<int:id>/pre-no-answer/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_pre_no_answer_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Pre No Answer').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/contact-in-future/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_contact_in_future_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Contact in Future').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/eoi/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_eoi_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'EOI').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/waiting/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_waiting_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Waiting').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/meeting/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_meeting_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Meeting').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/won/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_won_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Won').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/lost/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_lost_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Lost').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/low-budget/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_low_budget_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Low Budget').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/not-interested-now/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_not_interested_now_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Interested Now').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/no-answer/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_no_answer_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/no-answer-follow/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_no_answer_follow_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer Follow').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/no-answer-hold/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_no_answer_hold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer Hold').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/leads/<int:id>/not-reached/<int:employee_id>', methods=['GET'])
    @login_required
    def manager_get_not_reached_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Reached').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/manager/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/manager/<int:id>/add-lead', methods=['GET', 'POST'])
    @login_required
    def manager_add_new_lead(id):
        if current_user.role == 'manager':
            if request.method == 'POST':
                new_client_name = request.form.get('client_name', None)
                new_phone = request.form.get('phone', None)
                new_email = request.form.get('email', None)
                new_status = request.form.get('status', None)
                new_channel = request.form.get('channel', None)
                new_request = request.form.get('request', None)
                new_ad_details = request.form.get('ad_details', None)
                new_lead_type = request.form.get('lead_type', None)
                new_country = request.form.get('country', None)
                new_campaign = request.form.get('campaign', None)
                new_round = request.form.get('round', None)
                new_source = request.form.get('source', None)
                new_client_job = request.form.get('client_job', None)
                if new_phone[0] == '0':
                    new_whatsapp_link = 'https://wa.me/+2' + new_phone
                else:
                    new_whatsapp_link = 'https://wa.me/+' + new_phone
                new_current_time= datetime.utcnow()
                new_lead = Leads(created_time=new_current_time, client_name=new_client_name, phone=new_phone, second_phone='', email= new_email, lead_type=new_lead_type, client_job=new_client_job, country = new_country, preassigned_to= None, assigned_to=current_user.employees_id, visit_date = None, ad_details=new_ad_details, campaign=new_campaign, round=new_round, status=new_status, last_follow_up=None, next_follow_up=None, description='', channel=new_channel, request=new_request, source=new_source, whatsapp_link=new_whatsapp_link)
                new_lead.insert()
                current_time = datetime.utcnow()
                new_description = Description(created_time=current_time, status=new_status, description='', employees_id=current_user.employees_id, deals_id=None ,leads_id=new_lead.id)
                new_description.insert()
                db.session.close()

                return redirect('/manager/leads/'+ str(id))
            return render_template('pages/manager/add-lead.html', data={
                'id': id
            })
        else: 
            abort(403)

    @app.route('/manager/leads/<int:id>', methods=['GET','POST'])
    @login_required
    def get_manager_leads(id):
        if current_user.employees_id == id:
            selection = Leads.query.order_by(Leads.created_time.desc()).all()
            current_leads = [result.format() for result in selection]
            all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
            all_sales = [result.format() for result in all_sales]
            for a in current_leads:
                if a['assigned_to']:
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            return render_template('pages/manager/leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads,
                'total_leads': len(selection),
                'all_sales': all_sales,
            }), 200
        else:
            abort(403)

    @app.route('/manager/<int:id>/view-lead/<int:lead_id>', methods=['GET'])
    @login_required
    def get_manager_lead(id, lead_id):
        lead = Leads.query.get(lead_id)
        if not lead:
            abort(404)
        selection = Description.query.filter(Description.leads_id == lead_id).all()
        descriptions = [result.format() for result in selection]
        for a in descriptions:
            employee_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['employees_id'] ).first()
            a['employees_name'] = employee_name.name
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to ).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to :
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''
        if lead.created_time:
            created_time_gmt = datetime_from_utc_to_local(lead.created_time)
        if lead.last_follow_up:
            last_follow_up_gmt = datetime_from_utc_to_local(lead.last_follow_up)
        else:
            last_follow_up_gmt = ''
        if lead.next_follow_up:
            next_follow_up_gmt = datetime_from_utc_to_local(lead.next_follow_up)
        else:
            next_follow_up_gmt = ''
        return render_template('pages/manager/employee-lead.html', data={
            'sucess': True,
            'id': id,
            'lead_id': lead.id,
            'client_name': lead.client_name,
            'whatsapp_link': lead.whatsapp_link,
            'status': lead.status,
            'created_time': created_time_gmt,
            'phone': lead.phone,
            'second_phone': lead.second_phone,
            'email': lead.email,
            'assigned_to': assigned_to_name.name,
            'last_follow_up': last_follow_up_gmt,
            'next_follow_up': next_follow_up_gmt,
            'preassigned_to': preassigned_to_name.name,
            'description': lead.description,
            'request': lead.request,
            'channel': lead.channel,
            'lead_type': lead.lead_type,
            'client_job': lead.client_job,
            'country': lead.country,
            'source': lead.source,
            'campaign': lead.campaign,
            'round': lead.round,
            'ad_details': lead.ad_details,
            'descriptions': descriptions
        }), 200

    @app.route('/manager/<int:id>/edit-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_manager_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_current_time = datetime.utcnow()
            new_client_name = request.form.get('client_name', None)
            new_phone = request.form.get('phone', None)
            new_second_phone = request.form.get('second_phone', None)
            new_email = request.form.get('email', None)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_source = request.form.get('source', None)
            new_channel = request.form.get('channel', None)
            new_round = request.form.get('round', None)
            new_request = request.form.get('request', None)
            new_campaign = request.form.get('campaign', None)
            new_ad_details = request.form.get('ad_details', None)
            new_lead_type = request.form.get('lead_type', None)
            new_country = request.form.get('country', None)


            lead.client_name = new_client_name
            lead.phone = new_phone
            lead.second_phone = new_second_phone
            lead.email = new_email
            if new_next_follow_up:
                lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
            lead.description = new_description
            lead.status = new_status
            lead.last_follow_up = new_current_time
            lead.source = new_source
            lead.channel = new_channel
            lead.round = new_round
            lead.request = new_request
            lead.campaign = new_campaign
            lead.ad_details = new_ad_details
            lead.lead_type = new_lead_type
            lead.country = new_country
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()

            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id))
        lead = Leads.query.filter(Leads.id == lead_id).one()
        return render_template('pages/manager/edit-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'client_name': lead.client_name,
            'phone': lead.phone,
            'second_phone': lead.second_phone,
            'email': lead.email,
            'description': lead.description,
            'next_follow_up': lead.next_follow_up,
            'source': lead.source,
            'channel': lead.channel,
            'ad_details': lead.ad_details,
            'campaign': lead.campaign,
            'request': lead.request,
            'round': lead.round,
            'status': lead.status,
            'assigned_to': lead.assigned_to,
            'lead_type': lead.lead_type,
            'country': lead.country,
            'campaign': lead.campaign
        })
    
    @app.route('/manager/<int:id>/assign-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def assign_manager_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+  str(id))
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/manager/<int:id>/assign-new-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def manager_assign_new_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id)+'/total-new')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-new-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/manager/<int:id>/assign-delayed-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def manager_assign_delayed_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id)+'/total-delayed')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-delayed-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/manager/<int:id>/assign-followup-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def manager_assign_followup_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id)+'/total-followup')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-followup-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })


    @app.route('/manager/<int:id>/assign-newcold-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def manager_assign_newcold_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id)+'/total-newcold')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-newcold-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })


    @app.route('/manager/<int:id>/assign-newglobal-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def manager_assign_newglobal_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id)+'/total-newglobal')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-newglobal-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/manager/<int:id>/assign-coldglobal-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def manager_assign_coldglobal_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/manager/leads/'+ str(id)+'/total-coldglobal')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/manager/assign-coldglobal-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    """
    Admin
    """

    @app.route('/deal/<int:id>/view/<int:deal_id>', methods=['GET'])
    @login_required
    def get_employee_deal(id, deal_id):
        deal = Deals.query.get(deal_id)
        if not deal:
            abort(404)
        selection = Description.query.filter(Description.deals_id == deal_id).all()
        descriptions = [result.format() for result in selection]
        for a in descriptions:
                employee_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['employees_id'] ).first()
                a['employees_name'] = employee_name.name
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == deal.assigned_to).first()
        return render_template('pages/admin/employee-deal.html', data={
            'sucess': True,
            'id': deal.id,
            'buyer_name': deal.buyer_name,
            'status': deal.status,
            'created_time': deal.created_time,
            'phone': deal.phone,
            'email': deal.email,
            'assigned_to': assigned_to_name.name,
            'project_developer': deal.project_developer,
            'project_type': deal.project_type,
            'project_name': deal.project_name,
            'description': deal.description,
            'unit_price': deal.unit_price,
            'down_payment': deal.down_payment,
            'commission': deal.commission,
            'descriptions': descriptions
        }), 200

    @app.route('/employee/<int:id>/edit', methods=['GET','POST'])
    @login_required
    def edit_employee(id):
        if current_user.employee_id == id:
            if request.method == 'POST':
                employee = Employees.query.get(current_user.employee_id)

                if not employee:
                    abort(404)
                try:
                    new_name = request.form.get('name', None)
                    new_id_number = request.form.get('id_number', None)
                    new_phone = request.form.get('phone', None)
                    new_address = request.form.get('address', None)
                    new_qualifications = request.form.get('qualifications', None)

                    new_name = new_name.split()
                    employee.f_name = new_name[0]
                    employee.l_name = new_name[1]
                    employee.ssn=new_id_number
                    employee.phone_number=new_phone
                    employee.address=new_address
                    employee.qualifications=new_qualifications
                    employee.update()
                    db.session.close()

                    return redirect('/employee/'+ str(id))
                except:
                    abort(422)
            employee = Employees.query.get(current_user.employee_id)
            if current_user.role == 'admin':
                return render_template('pages/admin/edit-employee.html', data={
                    'sucess': True,
                    'id': id,
                    'employees_id': employee.employees_id,
                    'name': employee.f_name + ' '+ employee.l_name,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications,
                }), 200
            elif current_user.role == 'manager':
                return render_template('pages/manager/edit-employee.html', data={
                    'sucess': True,
                    'id': id,
                    'employees_id': employee.employees_id,
                    'name': employee.f_name + ' '+ employee.l_name,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications,
                }), 200
            elif current_user.role == 'sales':
                return render_template('pages/sales/edit-employee.html', data={
                    'sucess': True,
                    'id': id,
                    'employees_id': employee.employees_id,
                    'name': employee.f_name + ' '+ employee.l_name,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications,
                }), 200
            elif current_user.role == 'teamlead':
                return render_template('pages/teamlead/edit-employee.html', data={
                    'sucess': True,
                    'id': id,
                    'employees_id': employee.employees_id,
                    'name': employee.f_name + ' '+ employee.l_name,
                    'id_number': employee.ssn,
                    'phone': employee.phone_number,
                    'address': employee.address,
                    'qualifications': employee.qualifications,
                }), 200
        else:
            abort(403)
    
    @app.route('/deal/<int:id>/edit/<int:deal_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_deal(id, deal_id):
        if request.method == 'POST':
            deal = Deals.query.filter(Deals.id == deal_id).one()
            if not deal:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            deal.description = new_description
            
            deal.update()
            db.session.close()
            new_current_time = datetime.utcnow()
            new_description = Description(created_time=new_current_time, status=new_status, description=new_description, employees_id=id, deals_id=deal_id, leads_id=None)
            new_description.insert()
            db.session.close()

            return redirect('/deals/'+ str(id))
        return render_template('pages/admin/edit-employee-deal.html', data={
            'id': id,
            'deal_id': deal_id
        })

    @app.route('/deals/<int:id>/add', methods=['GET', 'POST'])
    @login_required
    def add_new_deal(id):
        if request.method == 'POST':
            try:
                new_buyer_name = request.form.get('buyer_name', None)
                new_phone = request.form.get('phone', None)
                new_assigned_to = id
                new_status = request.form.get('status', None)
                new_email = request.form.get('email', None)
                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_description = request.form.get('description', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                
                new_current_time= datetime.utcnow()
                new_deal = Deals(created_time=new_current_time, buyer_name=new_buyer_name, phone=new_phone, email= new_email, assigned_to=new_assigned_to, status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=new_unit_price, down_payment=new_down_payment, commission=new_commission)
                new_deal.insert()
                db.session.close()
                
                new_description = Description(created_time=new_current_time, status=new_status, description=new_description, employees_id=new_assigned_to, deals_id=new_deal.id)
                new_description.insert()
                db.session.close()

                return redirect('/deals/'+ str(id))
            except:
                abort(422)
        return render_template('pages/admin/add-deal.html', data={
            'id': id
        })

    @app.route('/admin/<int:id>/select-assign-lead/<int:lead_id>', methods=['PATCH'])
    @login_required
    def select_assign_admin_lead(id, lead_id):
        body = request.get_json()
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        try:
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return jsonify({
                    'success': True,
                }), 200
        except:
            abort(404)

    """
    Leads
    """

    @app.route('/dashboard/<int:id>')
    @login_required
    def employee_dashboard(id):
        num_fresh = Leads.query.filter(Leads.assigned_to_id == current_user.employee_id).count()
        return render_template('pages/sales/dashboard.html', data={
            'id': current_user.employee_id,
            'num_fresh': num_fresh,
            }), 200

    @app.route('/leads', methods=['GET'])
    @login_required
    def retrieve_leads():
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            selection = Leads.query.order_by(Leads.created_time.desc()).all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            return render_template('pages/general-manager/leads.html', data={
                'id': current_user.id,
                'sucess': True,
                'leads': current_leads,
            }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>', methods=['GET','POST'])
    @login_required
    def get_employee_leads(id):
        if current_user.employees_id == id:
            selection = Leads.query.order_by(Leads.created_time.desc()).filter(Leads.assigned_to == current_user.employees_id).all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads,
                }), 200
            else:
                return render_template('pages/sales/employee-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads,
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/new', methods=['GET'])
    @login_required
    def get_new_leads(id):
        if current_user.employee_id == id:
            selection = Leads.query.filter(Leads.assigned_to_id == current_user.employee_id).all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to_id']:    
                    assigned_to_name = db.session.query(Employees.employees_id, Employees.f_name, Employees.l_name).filter(Employees.employees_id == a['assigned_to_id'] ).first()
                    a['assigned_to_name'] = assigned_to_name.f_name+ ' ' + assigned_to_name.l_name
                if a['source_id']:    
                    source_name = db.session.query(Source.source_id, Source.name).filter(Source.source_id == a['source_id'] ).first()
                    a['source'] = source_name.name
                if a['time_created']:
                    a['time_created'] = datetime_from_utc_to_local(a['time_created'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/new-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
            }), 200
            else:
                return render_template('pages/sales/new-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/followup', methods=['GET'])
    @login_required
    def get_followup_leads(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, func.date(Leads.next_follow_up) == current_time).order_by(Leads.next_follow_up.asc()).all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/follow-up-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
            }), 200
            else:
                return render_template('pages/sales/follow-up-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads,
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/delayed', methods=['GET'])
    @login_required
    def get_delayed_leads(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, func.date(Leads.next_follow_up) < current_time).order_by(Leads.next_follow_up.asc()).all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/delayed-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else: 
                return render_template('pages/sales/delayed-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads,
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/newcold', methods=['GET'])
    @login_required
    def get_new_cold_leads(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New Cold', Leads.lead_type == 'National').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/new-cold-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/new-cold-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads,
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/newglobal', methods=['GET'])
    @login_required
    def get_new_global_leads(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New', Leads.lead_type == 'International').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/new-international-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
            }), 200
            else:
                return render_template('pages/sales/new-international-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads,
                }), 200
        else:
            abort(403)
    
    @app.route('/leads/<int:id>/coldglobal', methods=['GET'])
    @login_required
    def get_cold_global_leads(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id,  Leads.status == 'New Cold', Leads.lead_type == 'International').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/new-cold-international-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
            }), 200
            else:
                return render_template('pages/sales/new-cold-international-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads,
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/interested-hold', methods=['GET'])
    @login_required
    def get_interested_hold(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Interested Hold').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/interested-follow', methods=['GET'])
    @login_required
    def get_interested_follow(id):
        if current_user.employees_id == id:
            current_time = datetime.now(timezone.utc).date()
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Interested Follow').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/waiting', methods=['GET'])
    @login_required
    def get_waiting(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Waiting').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/promise-visit', methods=['GET'])
    @login_required
    def get_promise_visit(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Promise Visit').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/no-answer-hold', methods=['GET'])
    @login_required
    def no_answer_hold(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'No Answer Hold').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/no-answer-follow', methods=['GET'])
    @login_required
    def get_no_answer_follow(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'No Answer Follow').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/pre-no-answer', methods=['GET'])
    @login_required
    def get_pre_no_answer(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Pre No Answer').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/contact-in-future', methods=['GET'])
    @login_required
    def get_contact_in_future(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Contact in Future').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/eoi', methods=['GET'])
    @login_required
    def get_eoi(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'EOI').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/meeting', methods=['GET'])
    @login_required
    def get_meeting(id):
        if current_user.employees_id == id:
            selection = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Meeting').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            if current_user.role == 'teamlead':
                return render_template('pages/teamlead/display-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads
                }), 200
            else:
                return render_template('pages/sales/display-leads.html', data={
                    'sucess': True,
                    'id': id,
                    'leads': current_leads
                }), 200
        else:
            abort(403)

    @app.route('/leads/<int:id>/view/<int:lead_id>', methods=['GET'])
    @login_required
    def get_employee_lead(id, lead_id):
        lead = Leads.query.get(lead_id)
        if not lead:
            abort(404)
        selection = Description.query.filter(Description.leads_id == lead_id).all()
        descriptions = [result.format() for result in selection]
        for a in descriptions:
            if a['employees_id']:
                employee_name = db.session.query(Employees.employees_id, Employees.f_name, Employees.l_name).filter(Employees.employees_id == a['employees_id'] ).first()
                a['employees_name'] = employee_name.f_name + ' ' + employee_name.l_name 
            if['time_created']:
                a['created_time'] = datetime_from_utc_to_local(a['time_created'])
        if lead.assigned_to_id:
            assigned_to_name = db.session.query(Employees.employees_id, Employees.f_name, Employees.l_name).filter(Employees.employees_id == lead.assigned_to_id ).first()
            assigned_to = assigned_to_name.f_name + ' ' + assigned_to_name.l_name 
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.time_created:
            created_time_gmt = datetime_from_utc_to_local(lead.time_created)
        return render_template('pages/sales/employee-lead.html', data={
            'sucess': True,
            'id': id,
            'lead_id': lead.leads_id,
            'client_name': lead.client_name,
            'created_time': created_time_gmt,
            'phone': lead.phone,
            'email': lead.email,
            'source': lead.source.name,
            'assigned_to': assigned_to,
            'request': lead.request,
            'descriptions': descriptions
        }), 200
    
    @app.route('/leads/<int:id>/edit/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.leads_id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)

            new_current_time = datetime.utcnow()
            print(new_status)
            status = Status.query.filter(Status.name == new_status).one()
            status_id = status.status_id
            lead.status_id = status_id

            new_assigned_to = current_user.employee_id
            lead.update()
            db.session.close()

            new_description = Description(time_created=new_current_time, notes=new_description, status_id=status_id, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/leads/'+ str(id)+'/new')
        lead = Leads.query.filter(Leads.leads_id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.employees_id, Employees.f_name, Employees.l_name).filter(Employees.employees_id == lead.assigned_to_id).first()
        assigned_to = assigned_to_name.f_name + ' ' +  assigned_to_name.l_name
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-lead.html', data={
                'sucess': True,
                'id': id,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'phone': lead.phone,
                'email': lead.email,
                'assigned_to_name': assigned_to,
                'assigned_to': lead.assigned_to_id,
            }), 200
        else:
            return render_template('pages/sales/edit-employee-lead.html', data={
                'sucess': True,
                'id': id,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'phone': lead.phone,
                'email': lead.email,
                'assigned_to_name': assigned_to,
                'assigned_to': lead.assigned_to_id,
            }),200

    @app.route('/leads/<int:id>/edit-new-cold/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_new_cold_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_second_phone = request.form.get('second_phone', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_current_time = datetime.utcnow()
            if new_status == 'Won':
                lead.last_follow_up = new_current_time
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                if new_next_follow_up:
                    lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                else:
                    lead.next_follow_up = None
                new_assigned_to = current_user.employees_id
                lead.update()
                db.session.close()

                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                lead = Leads.query.get(lead_id)

                new_deal = Deals(created_time=new_current_time, buyer_name=lead.client_name, phone=lead.phone, second_phone= lead.second_phone, email= lead.email, assigned_to=new_assigned_to, last_follow_up=new_current_time ,status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=int(new_unit_price), down_payment=int(new_down_payment), commission=new_commission)
                new_deal.insert()
                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to,deals_id=new_deal.id ,leads_id= lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/newcold')
            else:
                new_assigned_to = current_user.employees_id
                new_current_time = datetime.utcnow()
                if new_status == 'Interested Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Interested Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Not Interested':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Promise Visit':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Meeting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.visit_date = new_current_time
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Waiting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(hours=5)
                elif new_status == 'EOI':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Low Budget':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Not Interested Now':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Pre No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'No Answer Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Not Reached':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Contact in Future':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p')
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=15)
                elif new_status == 'Lost':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Won':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                lead.last_follow_up = new_current_time
                
                lead.update()
                db.session.close()

                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/newcold')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-new-cold-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200
        else:
            return render_template('pages/sales/edit-employee-new-cold-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            })

    @app.route('/leads/<int:id>/edit-follow-up/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_follow_up_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_second_phone = request.form.get('second_phone', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_current_time = datetime.utcnow()
            if new_status == 'Won':
                lead.last_follow_up = new_current_time
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                if new_next_follow_up:
                    lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                else:
                    lead.next_follow_up = None
                new_assigned_to = current_user.employees_id
                lead.update()
                db.session.close()

                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                lead = Leads.query.get(lead_id)

                new_deal = Deals(created_time=new_current_time, buyer_name=lead.client_name, phone=lead.phone, second_phone= lead.second_phone, email= lead.email, assigned_to=new_assigned_to, last_follow_up=new_current_time ,status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=int(new_unit_price), down_payment=int(new_down_payment), commission=new_commission)
                new_deal.insert()
                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to,deals_id=new_deal.id ,leads_id= lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/followup')
            else:
                new_assigned_to = current_user.employees_id
                new_current_time = datetime.utcnow()
                if new_status == 'Interested Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Interested Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Not Interested':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Promise Visit':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Meeting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.visit_date = new_current_time
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Waiting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(hours=5)
                elif new_status == 'EOI':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Low Budget':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Not Interested Now':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Pre No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'No Answer Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Not Reached':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Contact in Future':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p')
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=15)
                elif new_status == 'Lost':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Won':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                lead.last_follow_up = new_current_time
                
                lead.update()
                db.session.close()

                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/followup')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-follow-up-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200
        else:
            return render_template('pages/sales/edit-employee-follow-up-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200

    @app.route('/leads/<int:id>/edit-delayed/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_delayed_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_second_phone = request.form.get('second_phone', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_current_time = datetime.utcnow()
            if new_status == 'Won':
                lead.last_follow_up = new_current_time
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                if new_next_follow_up:
                    lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                else:
                    lead.next_follow_up = None
                new_assigned_to = current_user.employees_id
                lead.update()
                db.session.close()

                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                lead = Leads.query.get(lead_id)

                new_deal = Deals(created_time=new_current_time, buyer_name=lead.client_name, phone=lead.phone, second_phone= lead.second_phone, email= lead.email, assigned_to=new_assigned_to, last_follow_up=new_current_time ,status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=int(new_unit_price), down_payment=int(new_down_payment), commission=new_commission)
                new_deal.insert()
                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to,deals_id=new_deal.id ,leads_id= lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/delayed')
            else:
                new_assigned_to = current_user.employees_id
                new_current_time = datetime.utcnow()
                if new_status == 'Interested Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Interested Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Not Interested':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Promise Visit':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Meeting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.visit_date = new_current_time
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Waiting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(hours=5)
                elif new_status == 'EOI':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Low Budget':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Not Interested Now':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Pre No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'No Answer Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Not Reached':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Contact in Future':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p')
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=15)
                elif new_status == 'Lost':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Won':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                lead.last_follow_up = new_current_time
                
                lead.update()
                db.session.close()

                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/delayed')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-delayed-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200
        else:
            return render_template('pages/sales/edit-employee-delayed-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }),200

    @app.route('/leads/<int:id>/edit-new/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_new_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_second_phone = request.form.get('second_phone', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_current_time = datetime.utcnow()
            if new_status == 'Won':
                lead.last_follow_up = new_current_time
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                if new_next_follow_up:
                    lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                else:
                    lead.next_follow_up = None
                new_assigned_to = current_user.employees_id
                lead.update()
                db.session.close()

                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                lead = Leads.query.get(lead_id)

                new_deal = Deals(created_time=new_current_time, buyer_name=lead.client_name, phone=lead.phone, second_phone= lead.second_phone, email= lead.email, assigned_to=new_assigned_to, last_follow_up=new_current_time ,status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=int(new_unit_price), down_payment=int(new_down_payment), commission=new_commission)
                new_deal.insert()
                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to,deals_id=new_deal.id ,leads_id= lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/new')
            else:
                new_assigned_to = current_user.employees_id
                new_current_time = datetime.utcnow()
                if new_status == 'Interested Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Interested Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Not Interested':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Promise Visit':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Meeting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.visit_date = new_current_time
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Waiting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(hours=5)
                elif new_status == 'EOI':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Low Budget':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Not Interested Now':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Pre No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'No Answer Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Not Reached':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Contact in Future':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p')
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=15)
                elif new_status == 'Lost':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Won':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                lead.last_follow_up = new_current_time
                
                lead.update()
                db.session.close()

                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/new')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-new-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200
        else:
            return render_template('pages/sales/edit-employee-new-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200

    @app.route('/leads/<int:id>/edit-new-international/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_new_international_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_second_phone = request.form.get('second_phone', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_current_time = datetime.utcnow()
            if new_status == 'Won':
                lead.last_follow_up = new_current_time
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                if new_next_follow_up:
                    lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                else:
                    lead.next_follow_up = None
                new_assigned_to = current_user.employees_id
                lead.update()
                db.session.close()

                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                lead = Leads.query.get(lead_id)

                new_deal = Deals(created_time=new_current_time, buyer_name=lead.client_name, phone=lead.phone, second_phone= lead.second_phone, email= lead.email, assigned_to=new_assigned_to, last_follow_up=new_current_time ,status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=int(new_unit_price), down_payment=int(new_down_payment), commission=new_commission)
                new_deal.insert()
                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to,deals_id=new_deal.id ,leads_id= lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/newglobal')
            else:
                new_assigned_to = current_user.employees_id
                new_current_time = datetime.utcnow()
                if new_status == 'Interested Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Interested Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Not Interested':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Promise Visit':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Meeting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.visit_date = new_current_time
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Waiting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(hours=5)
                elif new_status == 'EOI':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Low Budget':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Not Interested Now':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Pre No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'No Answer Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Not Reached':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Contact in Future':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p')
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=15)
                elif new_status == 'Lost':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Won':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                lead.last_follow_up = new_current_time
                
                lead.update()
                db.session.close()

                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/newglobal')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-new-international-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200
        else:
            return render_template('pages/sales/edit-employee-new-international-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200

    @app.route('/leads/<int:id>/edit-new-cold-international/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_employee_new_cold_international_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_second_phone = request.form.get('second_phone', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_current_time = datetime.utcnow()
            if new_status == 'Won':
                lead.last_follow_up = new_current_time
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                if new_next_follow_up:
                    lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                else:
                    lead.next_follow_up = None
                new_assigned_to = current_user.employees_id
                lead.update()
                db.session.close()

                new_project_developer = request.form.get('project_developer', None)
                new_project_name = request.form.get('project_name', None)
                new_project_type = request.form.get('project_type', None)
                new_unit_price = request.form.get('unit_price', None)
                new_down_payment = request.form.get('down_payment', None)
                new_commission = request.form.get('commission', None)
                lead = Leads.query.get(lead_id)

                new_deal = Deals(created_time=new_current_time, buyer_name=lead.client_name, phone=lead.phone, second_phone= lead.second_phone, email= lead.email, assigned_to=new_assigned_to, last_follow_up=new_current_time ,status=new_status, project_developer=new_project_developer, project_name=new_project_name, project_type=new_project_type, description=new_description, unit_price=int(new_unit_price), down_payment=int(new_down_payment), commission=new_commission)
                new_deal.insert()
                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to,deals_id=new_deal.id ,leads_id= lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/coldglobal')
            else:
                new_assigned_to = current_user.employees_id
                new_current_time = datetime.utcnow()
                if new_status == 'Interested Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Interested Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Not Interested':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Promise Visit':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Meeting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.visit_date = new_current_time
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Waiting':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(hours=5)
                elif new_status == 'EOI':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=2)
                elif new_status == 'Low Budget':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Not Interested Now':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Pre No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'No Answer Hold':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'No Answer Follow':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=1)
                elif new_status == 'Not Reached':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Contact in Future':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p')
                    else:
                        lead.next_follow_up = new_current_time + timedelta(days=15)
                elif new_status == 'Lost':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                elif new_status == 'Won':
                    if new_next_follow_up:
                        lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
                    else:
                        lead.next_follow_up = None
                lead.description = new_description
                lead.status = new_status
                lead.second_phone = new_second_phone
                lead.last_follow_up = new_current_time
                
                lead.update()
                db.session.close()

                new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=new_assigned_to, deals_id=None, leads_id=lead_id)
                new_description.insert()
                db.session.close()

                return redirect('/leads/'+ str(id)+'/coldglobal')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        if not lead:
            abort(404)
        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/edit-employee-new-cold-international-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200
        else:
            return render_template('pages/sales/edit-employee-new-cold-international-lead.html', data={
                'sucess': True,
                'id': id,
                'second_phone': lead.second_phone,
                'lead_id': lead_id,
                'client_name': lead.client_name,
                'status': lead.status,
                'phone': lead.phone,
                'second_phone': lead.second_phone,
                'email': lead.email,
                'assigned_to_name': assigned_to_name.name,
                'assigned_to': lead.assigned_to,
                'description': lead.description
            }), 200

    @app.route('/leads/help', methods=['GET'])
    @login_required
    def get_status_help():
        if current_user.role == 'sales':
            return render_template('pages/sales/status-help.html', data={
                'sucess': True,
                'id': current_user.employee_id
                })
        elif current_user.role == 'admin':
            return render_template('pages/admin/status-help.html', data={
                'sucess': True,
                'id': current_user.employee_id
                })
        elif current_user.role == 'manager':
            return render_template('pages/manager/status-help.html', data={
                'sucess': True,
                'id': current_user.employee_id
                })
        elif current_user.role == 'teamlead':
            return render_template('pages/teamlead/status-help.html', data={
                'sucess': True,
                'id': current_user.employee_id
                })

    """
    Deals
    """

    @app.route('/deals', methods=['GET'])
    @login_required
    def retrieve_deals():
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            selection = Deals.query.order_by(Deals.id).all()
            current_deals = [result.format() for result in selection]
            for a in current_deals:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            return render_template('pages/general-manager/deals.html', data={
                'id': current_user.employees_id,
                'sucess': True,
                'deals': current_deals,
            }), 200
        elif current_user.role == 'admin':
            selection = Deals.query.order_by(Deals.id).all()
            current_deals = [result.format() for result in selection]
            for a in current_deals:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            return render_template('pages/admin/deals.html', data={
                'id': current_user.employees_id,
                'sucess': True,
                'deals': current_deals,
            }), 200
        elif current_user.role == 'manager':
            selection = Deals.query.order_by(Deals.id).all()
            current_deals = [result.format() for result in selection]
            for a in current_deals:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            return render_template('pages/manager/deals.html', data={
                'id': current_user.employees_id,
                'sucess': True,
                'deals': current_deals,
            }), 200
        else:
            abort(403)

    """
    Salaries
    """

    @app.route('/salaries')
    @login_required
    def retrieve_salaries():
        if current_user.role == 'gm' or current_user.role == 'hr' or current_user.role == 'it':
            selection = Salaries.query.join(Employees).all()
            salary = []
            i = 0

            current_salaries = [result.format() for result in selection]
            for s in selection:
                salary.append(s.employees.name)
                salary.append(s.employees.job_title)
            for a in current_salaries:
                a['name'] = salary[i]
                a['job_title'] = salary[i+1]
                i= i + 2
            if len(current_salaries) == 0:
                abort(404)
            return render_template('pages/general-manager/salaries.html', data={
                'id': current_user.id,
                'sucess': True,
                'salaries': current_salaries,
            }), 200
        else:
            abort(403)
    """
    Admin
    """
    @app.route("/admin/import", methods=['GET', 'POST'])
    @login_required
    def doimport():
        if request.method == 'POST':
            uploaded_file = request.files['file']
            if uploaded_file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
                new_status = request.form.get('status', None)
                new_lead_type = request.form.get('lead_type', None)
                new_country = request.form.get('country', None)
                new_current_time= datetime.utcnow()
                # set the file path
                uploaded_file.save(file_path)
                col_names = ['client_name','phone', 'second_phone','email','description', 'request', 'channel', 'source', 'ad_details', 'campaign', 'round', 'assigned_to', 'client_job']
                df = pd.read_excel(file_path, names=col_names, dtype={'phone': str, 'second_phone': str})
                preassigned_to = [current_user.employees_id]*len(df)
                if new_status == 'New Cold':
                    status = ['New Cold']*len(df)
                else:
                    status = ['New']*len(df)
                lead_type = [new_lead_type]*len(df)
                country = [new_country] *len(df)
                new_current_time = [new_current_time] *len(df)
                df.insert(0, "preassigned_to", preassigned_to)
                df.insert(0, "status", status)
                df.insert(0, "lead_type", lead_type)
                df.insert(0, "country", country)
                df.insert(0, "created_time", new_current_time)
                df['assigned_to'] = df['assigned_to'].astype(str)
                df['assigned_to'] = df['assigned_to'].fillna(current_user.employees_id)
                new_leads = pd.DataFrame(columns = list(df.columns))
                dublicate_leads = pd.DataFrame(columns = list(df.columns))
                os.remove(file_path)
                for index, row in df.iterrows():
                    if Leads.query.filter(Leads.phone == row['phone']).first():
                        lead = Leads.query.filter(Leads.phone == row['phone']).first()
                        assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
                        df['assigned_to'] = df['assigned_to'].astype(str)
                        df.at[index, 'assigned_to'] = assigned_to_name.name
                        dublicate_leads = dublicate_leads.append(df.iloc[index])
                    else:
                        assigned_to = db.session.query(Employees.id, Employees.name).filter(Employees.name == row['assigned_to']).one_or_none()
                        if assigned_to:
                            df.at[index, 'assigned_to'] = assigned_to.id
                            df['assigned_to'] = df['assigned_to'].astype(str)
                            new_leads = new_leads.append(df.iloc[index])
                            new_leads['assigned_to'] = new_leads['assigned_to'].astype(int)
                        else:
                            df.at[index, 'assigned_to'] = current_user.employees_id
                            df['assigned_to'] = df['assigned_to'].astype(str)
                            new_leads = new_leads.append(df.iloc[index])
                            new_leads['assigned_to'] = new_leads['assigned_to'].astype(int)
                for index1, row1 in df.iterrows():
                    times = 0
                    for index2, row2 in new_leads.iterrows():
                        if row1['phone'] == row2['phone']:
                            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == current_user.employees_id).first()
                            df['assigned_to'] = df['assigned_to'].astype(str)
                            df.at[index1, 'assigned_to'] = assigned_to_name.name
                            times = times + 1
                            if times > 1:
                                dublicate_leads = dublicate_leads.append(df.iloc[index1])
                                times = 0
                        else:
                            pass
                
                new_leads.drop_duplicates(subset='phone', keep='first', inplace=True)
                
                new_leads_json = new_leads.to_json(orient='records')
                dublicate_leads_json = dublicate_leads.to_json(orient='records')
                
                new_leads.to_excel(os.path.join(app.config['UPLOAD_FOLDER'], 'new_leads.xlsx'), index=False)
                dublicate_leads.to_excel(os.path.join(app.config['UPLOAD_FOLDER'], 'dublicate_leads.xlsx'), index=False)
                return render_template('/pages/admin/leads-stage.html', data={'id': current_user.employees_id, 'new_leads': json.loads(new_leads_json), 'dublicate_leads': json.loads(dublicate_leads_json)})
        return render_template('pages/admin/add-lead-excel.html', data={'id': current_user.employees_id})


    @app.route("/admin/confirm-import", methods=['GET'])
    @login_required
    def save_imported_data():
            new_leads_path =os.path.join(app.config['UPLOAD_FOLDER'], 'new_leads.xlsx')
            dublicate_leads_path = os.path.join(app.config['UPLOAD_FOLDER'], 'dublicate_leads.xlsx')
            os.remove(dublicate_leads_path)
            col_names = ['created_time','country', 'lead_type','status', 'preassigned_to', 'client_name','phone','second_phone', 'email','description', 'request', 'channel', 'source', 'ad_details', 'campaign', 'round', 'assigned_to', 'client_job']
            df = pd.read_excel(new_leads_path, names=col_names, dtype={'phone': str, 'second_phone': str })
            engine= db.engine
            df.to_sql('leads', con=engine, if_exists='append', index=False)
            os.remove(new_leads_path)
            sql_command1="""UPDATE leads SET whatsapp_link=CONCAT('https://wa.me/+', phone) WHERE phone LIKE '9%';"""

            sql_command2="""UPDATE leads SET whatsapp_link=CONCAT('https://wa.me/+2', phone) WHERE phone LIKE '01%';"""
            db.session.execute(text(sql_command1))
            db.session.commit()
            db.session.execute(text(sql_command2))
            db.session.commit()
            return redirect('/admin/leads/'+ str(current_user.employees_id))
    
    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if current_user.role == 'admin':
            employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager', Employees.job_title == 'Key Account', Employees.job_title == 'Admin')).all()
            current_time = datetime.now(timezone.utc).date()
            tot_fresh = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'National').count()
            tot_new_international = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'International').count()
            tot_new_cold_international = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type == 'International').count()
            tot_new_cold = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type=='National').count()
            tot_delayed = Leads.query.filter(func.date(Leads.next_follow_up) < current_time).count()
            tot_followups = Leads.query.filter(func.date(Leads.next_follow_up) == current_time).count()
            data = {"id": current_user.employees_id, "tot_fresh": tot_fresh, "tot_new_international": tot_new_international,"tot_new_cold":tot_new_cold, 'tot_new_cold_international':tot_new_cold_international, "tot_delayed":tot_delayed,"tot_followups": tot_followups, "employees":[]}
            for employee in employees:
                num_fresh = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'New', Leads.lead_type == 'National').count()
                num_new_international = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').count()
                num_new_cold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'New Cold', Leads.lead_type=='National').count()
                num_delayed = Leads.query.filter(Leads.assigned_to == employee.id, func.date(Leads.next_follow_up) < current_time).count()
                num_followups = Leads.query.filter(Leads.assigned_to == employee.id, func.date(Leads.next_follow_up) == current_time).count()
                num_interested_follow = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Interested Follow').count()
                num_interested_hold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Interested Hold').count()
                num_promise_visit = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Promise Visit').count()
                num_eoi = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'EOI').count()
                num_waiting = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Waiting').count()
                num_meeting = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Meeting').count()
                num_pre_no_answer = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Pre No Answer').count()
                num_contact_in_future = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Contact in Future').count()
                num_won = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Won').count()
                num_lost = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Lost').count()
                num_not_interested = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Interested').count()
                num_low_budget = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Low Budget').count()
                num_not_interested_now = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Interested Now').count()
                num_no_answer = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer').count()
                num_no_answer_hold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer Hold').count()
                num_no_answer_follow = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer Follow').count()
                num_not_reached = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Reached').count()
                data['employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_fresh': num_fresh,
                    'num_new_cold': num_new_cold,
                    'num_new_international': num_new_international,
                    'num_followups': num_followups,
                    'num_delayed': num_delayed,
                    'num_interested_follow': num_interested_follow,
                    'num_interested_hold': num_interested_hold,
                    'num_promise_visit': num_promise_visit,
                    'num_pre_no_answer': num_pre_no_answer,
                    'num_contact_in_future': num_contact_in_future,
                    'num_eoi': num_eoi,
                    'num_waiting': num_waiting,
                    'num_meeting': num_meeting,
                    'num_won': num_won,
                    'num_lost': num_lost,
                    'num_not_interested': num_not_interested,
                    'num_low_budget': num_low_budget,
                    'num_not_interested_now': num_not_interested_now,
                    'num_no_answer': num_no_answer,
                    'num_no_answer_hold': num_no_answer_hold,
                    'num_no_answer_follow': num_no_answer_follow,
                    'num_not_reached': num_not_reached
                    })
            return render_template('pages/admin/dashboard.html', data=data), 200
        else: 
            abort(403)

    @app.route('/admin/leads/<int:id>/total-new', methods=['GET'])
    @login_required
    def get_all_new_leads(id):
        selection = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/total-new-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/total-followup', methods=['GET'])
    @login_required
    def get_all_followup_leads(id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(func.date(Leads.next_follow_up) == current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/total-followup-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/total-delayed', methods=['GET'])
    @login_required
    def get_all_delayed_leads(id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(func.date(Leads.next_follow_up) < current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/total-delayed-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/total-newcold', methods=['GET'])
    @login_required
    def get_all_new_cold_leads(id):
        selection = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/total-newcold-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/total-newglobal', methods=['GET'])
    @login_required
    def get_all_new_global_leads(id):
        selection = Leads.query.filter(Leads.status == 'New', Leads.lead_type == 'International').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/total-newglobal-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/total-coldglobal', methods=['GET'])
    @login_required
    def get_all_cold_global_leads(id):
        selection = Leads.query.filter(Leads.status == 'New Cold', Leads.lead_type == 'International').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/total-coldglobal-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/new/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_new_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'New', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/followup/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_followup_leads(id, employee_id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(Leads.assigned_to == employee_id, func.date(Leads.next_follow_up) == current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/delayed/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_delayed_leads(id, employee_id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(Leads.assigned_to == employee_id, func.date(Leads.next_follow_up) < current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/newcold/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_new_cold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'New Cold', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/newglobal/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_new_global_leads(id, employee_id):
            selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').all()
            current_leads = [result.format() for result in selection]
            all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            return render_template('pages/admin/small-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads,
                'all_sales': all_sales,
            }), 200

    @app.route('/admin/leads/<int:id>/interested-hold/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_interested_hold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Interested Hold').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/interested-follow/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_interested_follow_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Interested Follow').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/not-interested/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_not_interested_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Interested').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200

    @app.route('/admin/leads/<int:id>/promise-visit/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_promise_visit_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Promise Visit').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales,
        }), 200
    
    @app.route('/admin/leads/<int:id>/pre-no-answer/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_pre_no_answer_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Pre No Answer').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/contact-in-future/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_contact_in_future_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Contact in Future').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/eoi/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_eoi_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'EOI').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/waiting/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_waiting_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Waiting').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/meeting/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_meeting_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Meeting').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/won/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_won_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Won').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/lost/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_lost_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Lost').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/low-budget/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_low_budget_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Low Budget').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/not-interested-now/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_not_interested_now_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Interested Now').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/no-answer/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_no_answer_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/no-answer-follow/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_no_answer_follow_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer Follow').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/no-answer-hold/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_no_answer_hold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer Hold').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/leads/<int:id>/not-reached/<int:employee_id>', methods=['GET'])
    @login_required
    def admin_get_not_reached_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Reached').all()
        current_leads = [result.format() for result in selection]
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/admin/small-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
            'all_sales': all_sales
        }), 200

    @app.route('/admin/<int:id>/add-lead', methods=['GET', 'POST'])
    @login_required
    def add_new_lead(id):
        if current_user.role == 'admin':
            if request.method == 'POST':
                new_client_name = request.form.get('client_name', None)
                new_phone = request.form.get('phone', None)
                new_email = request.form.get('email', None)
                new_status = request.form.get('status', None)
                new_channel = request.form.get('channel', None)
                new_request = request.form.get('request', None)
                new_ad_details = request.form.get('ad_details', None)
                new_lead_type = request.form.get('lead_type', None)
                new_country = request.form.get('country', None)
                new_campaign = request.form.get('campaign', None)
                new_round = request.form.get('round', None)
                new_source = request.form.get('source', None)
                new_client_job = request.form.get('client_job', None)
                if new_phone[0] == '0':
                    new_whatsapp_link = 'https://wa.me/+2' + new_phone
                else:
                    new_whatsapp_link = 'https://wa.me/+' + new_phone
                new_current_time= datetime.utcnow()
                new_lead = Leads(created_time=new_current_time, client_name=new_client_name, phone=new_phone, second_phone='', email= new_email, lead_type=new_lead_type, client_job=new_client_job, country = new_country, preassigned_to= None, assigned_to=current_user.employees_id, visit_date = None, ad_details=new_ad_details, campaign=new_campaign, round=new_round, status=new_status, last_follow_up=None, next_follow_up=None, description='', channel=new_channel, request=new_request, source=new_source, whatsapp_link=new_whatsapp_link)
                new_lead.insert()
                current_time = datetime.utcnow()
                new_description = Description(created_time=current_time, status=new_status, description='', employees_id=current_user.employees_id, deals_id=None ,leads_id=new_lead.id)
                new_description.insert()
                db.session.close()

                return redirect('/admin/leads/'+ str(id))
            return render_template('pages/admin/add-lead.html', data={
                'id': id
            })
        else: 
            abort(403)

    @app.route('/admin/leads/<int:id>', methods=['GET','POST'])
    @login_required
    def get_admin_leads(id):
        if current_user.employees_id == id:
            selection = Leads.query.order_by(Leads.created_time.desc()).all()
            current_leads = [result.format() for result in selection]
            all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
            all_sales = [result.format() for result in all_sales]
            for a in current_leads:
                if a['assigned_to']:
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            return render_template('pages/admin/leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads,
                'total_deals': len(selection),
                'all_sales': all_sales,
            }), 200
        else:
            abort(403)

    @app.route('/admin/<int:id>/view-lead/<int:lead_id>', methods=['GET'])
    @login_required
    def get_admin_lead(id, lead_id):
        lead = Leads.query.get(lead_id)
        if not lead:
            abort(404)
        selection = Description.query.filter(Description.leads_id == lead_id).all()
        descriptions = [result.format() for result in selection]
        for a in descriptions:
            employee_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['employees_id'] ).first()
            a['employees_name'] = employee_name.name
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to ).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to :
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''
        if lead.created_time:
            created_time_gmt = datetime_from_utc_to_local(lead.created_time)
        if lead.last_follow_up:
            last_follow_up_gmt = datetime_from_utc_to_local(lead.last_follow_up)
        else:
            last_follow_up_gmt = ''
        if lead.next_follow_up:
            next_follow_up_gmt = datetime_from_utc_to_local(lead.next_follow_up)
        else:
            next_follow_up_gmt = ''
        return render_template('pages/admin/employee-lead.html', data={
            'sucess': True,
            'id': id,
            'lead_id': lead.id,
            'client_name': lead.client_name,
            'whatsapp_link': lead.whatsapp_link,
            'status': lead.status,
            'created_time': created_time_gmt,
            'phone': lead.phone,
            'second_phone': lead.second_phone,
            'email': lead.email,
            'assigned_to': assigned_to_name.name,
            'last_follow_up': last_follow_up_gmt,
            'next_follow_up': next_follow_up_gmt,
            'preassigned_to': preassigned_to_name.name,
            'description': lead.description,
            'request': lead.request,
            'channel': lead.channel,
            'lead_type': lead.lead_type,
            'client_job': lead.client_job,
            'country': lead.country,
            'source': lead.source,
            'campaign': lead.campaign,
            'round': lead.round,
            'ad_details': lead.ad_details,
            'descriptions': descriptions
        }), 200

    @app.route('/admin/<int:id>/edit-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def edit_admin_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_current_time = datetime.utcnow()
            new_client_name = request.form.get('client_name', None)
            new_phone = request.form.get('phone', None)
            new_second_phone = request.form.get('second_phone', None)
            new_email = request.form.get('email', None)
            new_description = request.form.get('description', None)
            new_status = request.form.get('status', None)
            new_next_follow_up = request.form.get('next_follow_up', None)
            new_source = request.form.get('source', None)
            new_channel = request.form.get('channel', None)
            new_round = request.form.get('round', None)
            new_request = request.form.get('request', None)
            new_campaign = request.form.get('campaign', None)
            new_ad_details = request.form.get('ad_details', None)
            new_lead_type = request.form.get('lead_type', None)
            new_country = request.form.get('country', None)


            lead.client_name = new_client_name
            lead.phone = new_phone
            lead.second_phone = new_second_phone
            lead.email = new_email
            if new_next_follow_up:
                lead.next_follow_up = datetime_from_local_to_utc(datetime.strptime(new_next_follow_up, '%m/%d/%Y %I:%M %p'))
            lead.description = new_description
            lead.status = new_status
            lead.last_follow_up = new_current_time
            lead.source = new_source
            lead.channel = new_channel
            lead.round = new_round
            lead.request = new_request
            lead.campaign = new_campaign
            lead.ad_details = new_ad_details
            lead.lead_type = new_lead_type
            lead.country = new_country
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()

            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id))
        lead = Leads.query.filter(Leads.id == lead_id).one()
        return render_template('pages/admin/edit-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'client_name': lead.client_name,
            'phone': lead.phone,
            'second_phone': lead.second_phone,
            'email': lead.email,
            'description': lead.description,
            'next_follow_up': lead.next_follow_up,
            'source': lead.source,
            'channel': lead.channel,
            'ad_details': lead.ad_details,
            'campaign': lead.campaign,
            'request': lead.request,
            'round': lead.round,
            'status': lead.status,
            'assigned_to': lead.assigned_to,
            'lead_type': lead.lead_type,
            'country': lead.country,
            'campaign': lead.campaign
        })
    
    @app.route('/admin/<int:id>/assign-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def assign_admin_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+  str(id))
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/admin/<int:id>/assign-new-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def admin_assign_new_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id)+'/total-new')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-new-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/admin/<int:id>/assign-delayed-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def admin_assign_delayed_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id)+'/total-delayed')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-delayed-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/admin/<int:id>/assign-followup-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def admin_assign_followup_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id)+'/total-followup')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-followup-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })


    @app.route('/admin/<int:id>/assign-newcold-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def admin_assign_newcold_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id)+'/total-newcold')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-newcold-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })


    @app.route('/admin/<int:id>/assign-newglobal-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def admin_assign_newglobal_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id)+'/total-newglobal')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-newglobal-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })

    @app.route('/admin/<int:id>/assign-coldglobal-lead/<int:lead_id>', methods=['GET', 'POST'])
    @login_required
    def admin_assign_coldglobal_lead(id, lead_id):
        if request.method == 'POST':
            lead = Leads.query.filter(Leads.id == lead_id).one()
            if not lead:
                abort(404)
            new_assigned_to = request.form.get('assigned_to', None)
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == new_assigned_to).first()
            assign_from = preassigned_to_name.name
            assign_to = assigned_to_name.name
            new_description = 'From ' + assign_from + ' To ' + assign_to
            new_status = "Assign Lead"
            new_current_time = datetime.utcnow()
            lead.preassigned_to = lead.assigned_to
            lead.assigned_to = new_assigned_to
            lead.last_follow_up = new_current_time
            
            employee_id = current_user.employees_id

            lead.update()
            db.session.close()
            new_description = Description(created_time=new_current_time, description=new_description, status=new_status, employees_id=employee_id, deals_id=None, leads_id=lead_id)
            new_description.insert()
            db.session.close()

            return redirect('/admin/leads/'+ str(id)+'/total-coldglobal')
        lead = Leads.query.filter(Leads.id == lead_id).one()
        all_sales = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Team Leader', Employees.job_title == 'Sales Manager')).all()
        if lead.assigned_to:
            assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.assigned_to).first()
        else:
            class assigned_to_obj(object):
                pass
            assigned_to_name = assigned_to_obj()
            assigned_to_name.name = ''
        if lead.preassigned_to:
            preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == lead.preassigned_to ).first()
        else:
            class preassigned_to_obj(object):
                pass
            preassigned_to_name = preassigned_to_obj()
            preassigned_to_name.name = ''

        return render_template('pages/admin/assign-coldglobal-lead.html', data={
            'id': id,
            'lead_id': lead_id,
            'assigned_to': lead.assigned_to,
            'assigned_to_name': assigned_to_name.name,
            'preassigned_to_name': preassigned_to_name.name,
            'all_sales': all_sales
        })
    """
    Report
    """
    @app.route('/add-report/<int:id>', methods=['GET', 'POST'])
    @login_required 
    def sales_add_report(id):
        if request.method == 'POST':
            chats = int(request.form.get('chats', 0))
            new_developer = int(request.form.get('new_developer', 0))
            availability = int(request.form.get('availability', 0))
            hot_deals = int(request.form.get('hot_deals', 0))
            new = int(request.form.get('new', 0))
            done = int(request.form.get('done', 0))

            if request.form.get('check_an_availability'):
                check_in_availability = True
            else:
                check_in_availability = False
            if request.form.get('check_today_tasks'):
                check_today_tasks = True
            else:
                check_today_tasks = False
            if request.form.get('check_hot_deals'):
                check_hot_deals = True
            else:
                check_hot_deals = False
            
            if request.form.get('highlight_immediate_tasks'):
                highlight_immediate_tasks = True
            else:
                highlight_immediate_tasks = False
            
            if request.form.get('share_stories'):
                share_stories = True
            else:
                share_stories = False
            
            if request.form.get('workshop'):
                workshop = True
            else:
                workshop = False
            
            first_period = request.form.get('first_period', None)
            second_period = request.form.get('second_period', None)
            third_period = request.form.get('third_period', None)
            
            new_current_time= datetime.utcnow()
            new_report = Report(created_time=new_current_time, chats=chats, new_developer=new_developer, availability=availability, hot_deals=hot_deals, new=new, done=done, check_in_availability=check_in_availability, check_hot_deals=check_hot_deals, check_todays_tasks=check_today_tasks, highlight_immediate_tasks=highlight_immediate_tasks, share_stories=share_stories, workshop=workshop, first_period=first_period, second_period=second_period, third_period=third_period, employees_id=id, comment=None, rating=0)
            new_report.insert()
            return redirect('/reports/view/'+ str(id))
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/add-daily-report.html', data={
            'id': id
        })
        else:
            return render_template('pages/sales/add-daily-report.html', data={
                'id': id
            })

    @app.route('/reports/view/<int:id>')
    @login_required 
    def sales_view_reports(id):
        current_reports = Report.query.filter( Report.employees_id == id).all()
        if not current_reports:
            abort(404)
        all_reports = [result.format() for result in current_reports]
        for a in all_reports:
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/all-reports.html', data={
            'id': id,
            'reports': all_reports
            })
        else:
            return render_template('pages/sales/all-reports.html', data={
                'id': id,
                'reports': all_reports
            })

    @app.route('/teamlead/reports/view/<int:id>')
    @login_required
    def teamlead_view_reports(id):
        employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Sales Manager'), Employees.team_id == id).all()
        current_time = datetime.now(timezone.utc).date()
        data = { 'id': id, 'team':[]}
        for employee in employees:
            employee_report = Report.query.filter(Report.employees_id == employee.id, func.date(Report.created_time) == current_time ).first()
            if employee_report:
                data['team'].append({
                        'employee_id': employee.id,
                        'employee_name': employee.name,
                        'chats': employee_report.chats,
                        'new_developer': employee_report.new_developer,
                        'availability': employee_report.availability,
                        'hot_deals': employee_report.hot_deals,
                        'new': employee_report.new,
                        'done': employee_report.done,
                        'check_in_availability': employee_report.check_in_availability,
                        'check_hot_deals': employee_report.check_hot_deals,
                        'share_stories': employee_report.share_stories,
                        'check_todays_tasks': employee_report.check_todays_tasks,
                        'highlight_immediate_tasks': employee_report.highlight_immediate_tasks,
                        'workshop': employee_report.workshop,
                        'first_period': employee_report.first_period,
                        'second_period': employee_report.second_period,
                        'third_period': employee_report.third_period,
                        'rating': employee_report.rating,
                        'comment': employee_report.comment
                        })
            else:
                data['team'].append({
                        'employee_id': employee.id,
                        'employee_name': employee.name,
                        'chats': 'No Report',
                        'new_developer': 'No Report',
                        'availability': 'No Report',
                        'hot_deals': 'No Report',
                        'new': 'No Report',
                        'done': 'No Report',
                        'check_in_availability': 'No Report',
                        'check_hot_deals': 'No Report',
                        'share_stories': 'No Report',
                        'check_todays_tasks': 'No Report',
                        'highlight_immediate_tasks': 'No Report',
                        'workshop':'No Report',
                        'first_period': 'No Report',
                        'second_period': 'No Report',
                        'third_period': 'No Report',
                        'rating': 'No Report',
                        'comment': 'No Report'
                        })         
        return render_template('pages/teamlead/employee-reports.html', data=data)

    @app.route('/reports/<int:id>/view/<int:report_id>')
    @login_required 
    def sales_view_report(id, report_id):
        report = Report.query.get(report_id)
        if not report:
            abort(404)
        created_time_gmt = datetime_from_utc_to_local(report.created_time)
        if current_user.role == 'teamlead':
            return render_template('pages/teamlead/view-daily-report.html', data={
            'id': id,
            'created_time': created_time_gmt,
            'chats': report.chats,
            'new_developer': report.new_developer,
            'availability': report.availability,
            'hot_deals': report.hot_deals,
            'new': report.new,
            'done': report.done,
            'check_an_availability': report.check_in_availability,
            'check_todays_tasks': report.check_todays_tasks,
            'check_hot_deals': report.check_hot_deals,
            'highlight_immediate_tasks': report.highlight_immediate_tasks,
            'share_stories': report.share_stories,
            'workshop': report.workshop,
            'first_period': report.first_period,
            'second_period': report.second_period,
            'third_period': report.third_period
        })
        else:
            return render_template('pages/sales/view-daily-report.html', data={
                'id': id,
                'created_time': created_time_gmt,
                'chats': report.chats,
                'new_developer': report.new_developer,
                'availability': report.availability,
                'hot_deals': report.hot_deals,
                'new': report.new,
                'done': report.done,
                'check_an_availability': report.check_in_availability,
                'check_todays_tasks': report.check_todays_tasks,
                'check_hot_deals': report.check_hot_deals,
                'highlight_immediate_tasks': report.highlight_immediate_tasks,
                'share_stories': report.share_stories,
                'workshop': report.workshop,
                'first_period': report.first_period,
                'second_period': report.second_period,
                'third_period': report.third_period
            })
    """
    Team Leader
    """
    @app.route('/teamlead/dashboard')
    @login_required
    def teamlead_dashboard():
        if current_user.role == 'teamlead':
            employees = Employees.query.filter(or_(Employees.job_title == 'Sales Representative', Employees.job_title == 'Sales Manager'), Employees.team_id == current_user.employees_id).all()
            current_time = datetime.now(timezone.utc).date()
            tot_fresh = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New', Leads.lead_type == 'National').count()
            tot_new_international = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New', Leads.lead_type == 'International').count()
            tot_new_cold_international = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New Cold', Leads.lead_type == 'International').count()
            tot_new_cold = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New Cold', Leads.lead_type=='National').count()
            tot_delayed = Leads.query.filter(Leads.assigned_to == current_user.employees_id, func.date(Leads.next_follow_up) < current_time).count()
            tot_followups = Leads.query.filter(Leads.assigned_to == current_user.employees_id, func.date(Leads.next_follow_up) == current_time).count()
            data = {"id": current_user.employees_id, "tot_fresh": tot_fresh, "tot_new_international": tot_new_international,"tot_new_cold":tot_new_cold,'tot_new_cold_international': tot_new_cold_international, "tot_delayed":tot_delayed,"tot_followups": tot_followups, "employees":[], "leads":[]}
            for employee in employees:
                num_fresh = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'New', Leads.lead_type == 'National').count()
                num_new_international = Leads.query.filter(Leads.assigned_to == employee.id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').count()
                num_new_cold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'New Cold', Leads.lead_type=='National').count()
                num_delayed = Leads.query.filter(Leads.assigned_to == employee.id, func.date(Leads.next_follow_up) < current_time).count()
                num_followups = Leads.query.filter(Leads.assigned_to == employee.id, func.date(Leads.next_follow_up) == current_time).count()
                num_interested_follow = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Interested Follow').count()
                num_interested_hold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Interested Hold').count()
                num_promise_visit = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Promise Visit').count()
                num_eoi = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'EOI').count()
                num_waiting = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Waiting').count()
                num_meeting = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Meeting').count()
                num_pre_no_answer = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Pre No Answer').count()
                num_contact_in_future = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Contact in Future').count()
                num_won = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Won').count()
                num_lost = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Lost').count()
                num_not_interested = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Interested').count()
                num_low_budget = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Low Budget').count()
                num_not_interested_now = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Interested Now').count()
                num_no_answer = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer').count()
                num_no_answer_hold = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer Hold').count()
                num_no_answer_follow = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'No Answer Follow').count()
                num_not_reached = Leads.query.filter(Leads.assigned_to == employee.id, Leads.status == 'Not Reached').count()
                data['employees'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'num_fresh': num_fresh,
                    'num_new_cold': num_new_cold,
                    'num_new_international': num_new_international,
                    'num_followups': num_followups,
                    'num_delayed': num_delayed,
                    'num_interested_follow': num_interested_follow,
                    'num_interested_hold': num_interested_hold,
                    'num_promise_visit': num_promise_visit,
                    'num_pre_no_answer': num_pre_no_answer,
                    'num_contact_in_future': num_contact_in_future,
                    'num_eoi': num_eoi,
                    'num_waiting': num_waiting,
                    'num_meeting': num_meeting,
                    'num_won': num_won,
                    'num_lost': num_lost,
                    'num_not_interested': num_not_interested,
                    'num_low_budget': num_low_budget,
                    'num_not_interested_now': num_not_interested_now,
                    'num_no_answer': num_no_answer,
                    'num_no_answer_hold': num_no_answer_hold,
                    'num_no_answer_follow': num_no_answer_follow,
                    'num_not_reached': num_not_reached
                    })
            num_fresh = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New', Leads.lead_type == 'National').count()
            num_new_international = Leads.query.filter(Leads.assigned_to == current_user.employees_id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').count()
            num_new_cold = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'New Cold', Leads.lead_type=='National').count()
            num_delayed = Leads.query.filter(Leads.assigned_to == current_user.employees_id, func.date(Leads.next_follow_up) < current_time).count()
            num_followups = Leads.query.filter(Leads.assigned_to == current_user.employees_id, func.date(Leads.next_follow_up) == current_time).count()
            num_interested_follow = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Interested Follow').count()
            num_interested_hold = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Interested Hold').count()
            num_promise_visit = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Promise Visit').count()
            num_eoi = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'EOI').count()
            num_waiting = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Waiting').count()
            num_meeting = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Meeting').count()
            num_pre_no_answer = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Pre No Answer').count()
            num_contact_in_future = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Contact in Future').count()
            num_won = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Won').count()
            num_lost = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Lost').count()
            num_not_interested = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Not Interested').count()
            num_low_budget = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Low Budget').count()
            num_not_interested_now = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Not Interested Now').count()
            num_no_answer = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'No Answer').count()
            num_no_answer_hold = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'No Answer Hold').count()
            num_no_answer_follow = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'No Answer Follow').count()
            num_not_reached = Leads.query.filter(Leads.assigned_to == current_user.employees_id, Leads.status == 'Not Reached').count()
            data['leads'].append({
                'employee_id': current_user.employees_id,
                'num_fresh': num_fresh,
                'num_new_cold': num_new_cold,
                'num_new_international': num_new_international,
                'num_followups': num_followups,
                'num_delayed': num_delayed,
                'num_interested_follow': num_interested_follow,
                'num_interested_hold': num_interested_hold,
                'num_promise_visit': num_promise_visit,
                'num_pre_no_answer': num_pre_no_answer,
                'num_contact_in_future': num_contact_in_future,
                'num_eoi': num_eoi,
                'num_waiting': num_waiting,
                'num_meeting': num_meeting,
                'num_won': num_won,
                'num_lost': num_lost,
                'num_not_interested': num_not_interested,
                'num_low_budget': num_low_budget,
                'num_not_interested_now': num_not_interested_now,
                'num_no_answer': num_no_answer,
                'num_no_answer_hold': num_no_answer_hold,
                'num_no_answer_follow': num_no_answer_follow,
                'num_not_reached': num_not_reached
                })
            return render_template('pages/teamlead/dashboard.html', data=data), 200
        else: 
            abort(403)

    @app.route('/teamlead/leads/<int:id>/new/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_new_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'New', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/followup/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_followup_leads(id, employee_id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(Leads.assigned_to == employee_id, func.date(Leads.next_follow_up) == current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
        }), 200

    @app.route('/teamlead/leads/<int:id>/delayed/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_delayed_leads(id, employee_id):
        current_time = datetime.now(timezone.utc).date()
        selection = Leads.query.filter(Leads.assigned_to == employee_id, func.date(Leads.next_follow_up) < current_time).order_by(Leads.created_time.desc()).all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
        }), 200

    @app.route('/teamlead/leads/<int:id>/newcold/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_new_cold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'New Cold', Leads.lead_type == 'National').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads,
        }), 200

    @app.route('/teamlead/leads/<int:id>/newglobal/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_new_global_leads(id, employee_id):
            selection = Leads.query.filter(Leads.assigned_to == employee_id, or_(Leads.status == 'New', Leads.status == 'New Cold'), Leads.lead_type == 'International').all()
            current_leads = [result.format() for result in selection]
            for a in current_leads:
                if a['assigned_to']:    
                    assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                    a['assigned_to_name'] = assigned_to_name.name
                if a['preassigned_to']:
                    preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                    a['preassigned_to_name'] = preassigned_to_name.name
                if a['next_follow_up']:
                    a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
                if a['last_follow_up']:
                    a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
                if a['created_time']:
                    a['created_time'] = datetime_from_utc_to_local(a['created_time'])
            return render_template('pages/teamlead/no-edit-leads.html', data={
                'sucess': True,
                'id': id,
                'leads': current_leads,
            }), 200

    @app.route('/teamlead/leads/<int:id>/interested-hold/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_interested_hold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Interested Hold').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/interested-follow/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_interested_follow_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Interested Follow').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/not-interested/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_not_interested_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Interested').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/promise-visit/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_promise_visit_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Promise Visit').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200
    
    @app.route('/teamlead/leads/<int:id>/pre-no-answer/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_pre_no_answer_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Pre No Answer').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/contact-in-future/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_contact_in_future_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Contact in Future').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/eoi/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_eoi_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'EOI').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/waiting/<int:employee_id>', methods=['GET'])
    @login_required
    def temalead_get_waiting_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Waiting').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/meeting/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_meeting_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Meeting').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/won/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_won_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Won').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/lost/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_lost_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Lost').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/low-budget/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_low_budget_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Low Budget').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/not-interested-now/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_not_interested_now_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Interested Now').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/no-answer/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_no_answer_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/no-answer-follow/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_no_answer_follow_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer Follow').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/no-answer-hold/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_no_answer_hold_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'No Answer Hold').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200

    @app.route('/teamlead/leads/<int:id>/not-reached/<int:employee_id>', methods=['GET'])
    @login_required
    def teamlead_get_not_reached_leads(id, employee_id):
        selection = Leads.query.filter(Leads.assigned_to == employee_id, Leads.status == 'Not Reached').all()
        current_leads = [result.format() for result in selection]
        for a in current_leads:
            if a['assigned_to']:    
                assigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['assigned_to'] ).first()
                a['assigned_to_name'] = assigned_to_name.name
            if a['preassigned_to']:
                preassigned_to_name = db.session.query(Employees.id, Employees.name).filter(Employees.id == a['preassigned_to'] ).first()
                a['preassigned_to_name'] = preassigned_to_name.name
            if a['next_follow_up']:
                a['next_follow_up'] = datetime_from_utc_to_local(a['next_follow_up'])
            if a['last_follow_up']:
                a['last_follow_up'] = datetime_from_utc_to_local(a['last_follow_up'])
            if a['created_time']:
                a['created_time'] = datetime_from_utc_to_local(a['created_time'])
        return render_template('pages/teamlead/no-edit-leads.html', data={
            'sucess': True,
            'id': id,
            'leads': current_leads
        }), 200


    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 401,
            'message': 'Unauthorized'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('pages/errors/403.html', data={
            'success': False,
            'error': 403,
            'message': 'Access forbidden'
        }), 403


    @app.errorhandler(404)
    def not_found(error):
        return render_template('pages/errors/404.html',data={
            'success': False,
            'error': 404,
            'message': 'Not Found'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return render_template('pages/errors/405.html', data={
            'success': False,
            'error': 405,
            'message': 'Method not allowed'
        }), 405

    @app.errorhandler(422)
    def unprocessed(error):
        return render_template('pages/errors/422.html',data={
            'success': False,
            'error': 422,
            'message': 'Unprocessable Entity'
        }), 422

    @app.errorhandler(500)
    def unauthorized(error):
        return render_template('pages/errors/500.html',data={
            'success': False,
            'error': 500,
            'message': 'Unauthorized'
        }), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run()