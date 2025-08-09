import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# --- APP CONFIGURATION ---
app = Flask(__name__)

# Configure a secret key for session management
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_default_secret_key_for_development')

# --- DIRECT DATABASE CONNECTION ---
# Paste the Internal Connection String you copied from your Render PostgreSQL page here.
# It should look like: 'postgres://user:password@host/database'
app.config['SQLALCHEMY_DATABASE_URI'] = "Ppostgresql://aqua_db_8uu8_user:aBSqQ4FCynDnkx5282Tv3v9d6NNuD5bC@dpg-d2bk4omr433s739sf3ng-a/aqua_db_8uu8"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database extension
db = SQLAlchemy(app)


# --- DATABASE MODELS (Matching your aquaculture_db.sql) ---
# These classes define the structure of your database tables.

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    head_quarter = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), default=None)
    kms_covered = db.Column(db.Integer, default=0)
    role = db.Column(db.String(10), nullable=False, default='employee')
    status = db.Column(db.String(15), nullable=False, default='inactive')
    last_login = db.Column(db.DateTime, default=None)

class Farmer(db.Model):
    __tablename__ = 'farmers'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    farmer_name = db.Column(db.String(100), nullable=False)
    num_of_ponds = db.Column(db.Integer, nullable=False)
    doc = db.Column(db.String(100), nullable=False)
    contact_details = db.Column(db.String(100), nullable=False)
    products_using = db.Column(db.String(255), nullable=False)
    visit_proof_path = db.Column(db.String(255), default=None)
    employee = db.relationship('Employee', backref=db.backref('farmers', lazy=True))

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    prescription = db.Column(db.Text, default=None)
    employee = db.relationship('Employee', backref=db.backref('sales', lazy=True))
    farmer = db.relationship('Farmer', backref=db.backref('sales', lazy=True))

class SalesTarget(db.Model):
    __tablename__ = 'sales_targets'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    target_quantity = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    employee = db.relationship('Employee', backref=db.backref('targets', lazy=True))

class DailyRoute(db.Model):
    __tablename__ = 'daily_routes'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    location_segment = db.Column(db.String(255), nullable=False)
    kms_segment = db.Column(db.Integer, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('routes', lazy=True))


# --- Auto-create Database Tables ---
# This block creates the tables and a default user when the app starts.
with app.app_context():
    db.create_all()
    if not Employee.query.filter_by(username='john').first():
        hashed_password = generate_password_hash('123')
        manager = Employee(username='john', password=hashed_password, head_quarter='HQ1', role='manager')
        db.session.add(manager)
        db.session.commit()
        print("Database tables created and default manager added.")


# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        account = Employee.query.filter_by(username=username).first()
        if account and check_password_hash(account.password, password):
            session['loggedin'] = True
            session['id'] = account.id
            session['username'] = account.username
            session['role'] = account.role
            account.last_login = datetime.datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect username or password!', 'danger')
    return render_template('login.html')

# --- ADDED THIS FUNCTION TO FIX THE ERROR ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles new user registration."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Assuming email and head_quarter are also in your register.html form
        email = request.form.get('email', f'{username}@example.com') # Default email
        head_quarter = request.form.get('head_quarter', 'HQ_Default') # Default HQ

        # Check if account already exists
        existing_account = Employee.query.filter_by(username=username).first()
        if existing_account:
            flash('Account with that username already exists!', 'warning')
            return render_template('register.html')

        # Hash the password before saving for security
        hashed_password = generate_password_hash(password)
        
        # Create a new employee (default role is 'employee')
        new_employee = Employee(
            username=username, 
            password=hashed_password, 
            head_quarter=head_quarter
        )

        db.session.add(new_employee)
        db.session.commit()

        flash('You have successfully registered! Please log in.', 'success')
        return redirect(url_for('login'))

    # Show the registration page on a GET request
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session['role'] != 'manager':
        return redirect(url_for('login'))

    total_employees = Employee.query.filter_by(role='employee').count()
    total_farmers = Farmer.query.count()
    now = datetime.datetime.utcnow()
    start_of_month = now.replace(day=1)
    sales_this_month = db.session.query(func.sum(Sale.quantity_sold)).filter(Sale.sale_date >= start_of_month).scalar() or 0
    employees = Employee.query.filter_by(role='employee').all()
    top_employee_query = db.session.query(Employee.username, func.sum(Sale.quantity_sold).label('total_sales')).join(Sale).filter(Sale.sale_date >= start_of_month).group_by(Employee.username).order_by(func.sum(Sale.quantity_sold).desc()).first()
    top_employee = {'username': top_employee_query[0]} if top_employee_query else None
    
    return render_template(
        'dashboard.html',
        username=session['username'],
        total_employees=total_employees,
        total_farmers=total_farmers,
        sales_this_month=sales_this_month,
        top_employee=top_employee,
        employees=employees,
        sales_today=[], # Placeholder
        sales_month=[], # Placeholder
        sales_geo_data=[] # Placeholder
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
