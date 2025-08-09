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

# Configure the database connection using the DATABASE_URL from Render's environment
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database extension
db = SQLAlchemy(app)


# --- DATABASE MODELS (Matching your aquaculture_db.sql) ---

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    head_quarter = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), default=None)
    kms_covered = db.Column(db.Integer, default=0)
    role = db.Column(db.String(10), nullable=False, default='employee') # 'employee' or 'manager'
    status = db.Column(db.String(15), nullable=False, default='inactive') # 'active', 'inactive', 'deactivated'
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
    # Define relationships
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
            # Update last login time
            account.last_login = datetime.datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect username or password!', 'danger')
    return render_template('login.html')

# Note: You will need a register route or a way to add employees.
# This is a placeholder.
@app.route('/register')
def register():
    return "Registration page placeholder. Add logic to create new employees."


@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session['role'] != 'manager':
        return redirect(url_for('login'))

    # --- KPI Calculations ---
    total_employees = Employee.query.filter_by(role='employee').count()
    total_farmers = Farmer.query.count()

    now = datetime.datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Sales this month (summing quantity as there's no price)
    sales_this_month_query = db.session.query(func.sum(Sale.quantity_sold)).filter(Sale.sale_date >= start_of_month).scalar()
    sales_this_month = sales_this_month_query or 0

    # --- Employee Data for Table ---
    employees = Employee.query.filter_by(role='employee').all()

    # --- Top Performer (by quantity sold) ---
    top_employee_query = db.session.query(
        Employee.username, func.sum(Sale.quantity_sold).label('total_sales')
    ).join(Sale, Employee.id == Sale.employee_id).filter(
        Sale.sale_date >= start_of_month
    ).group_by(Employee.username).order_by(func.sum(Sale.quantity_sold).desc()).first()
    top_employee = {'username': top_employee_query[0]} if top_employee_query else None

    # --- Chart & Heatmap Data ---
    # In a real app, you would add logic for these
    sales_today_data = [] 
    sales_month_data = []
    sales_geo_data = [] # The previous version had logic for this; it needs to be adapted

    return render_template(
        'dashboard.html',
        username=session['username'],
        total_employees=total_employees,
        total_farmers=total_farmers,
        sales_this_month=sales_this_month,
        top_employee=top_employee,
        employees=employees,
        sales_today=sales_today_data,
        sales_month=sales_month_data,
        sales_geo_data=sales_geo_data
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- DATABASE INITIALIZATION COMMAND ---

@app.cli.command("init-db")
def init_db_command():
    """Creates all database tables."""
    db.create_all()
    print("Initialized the database and created all tables.")
    # Optional: Add a default manager account if it doesn't exist
    if not Employee.query.filter_by(username='john').first():
        hashed_password = generate_password_hash('123')
        manager = Employee(username='john', password=hashed_password, head_quarter='HQ1', role='manager')
        db.session.add(manager)
        db.session.commit()
        print("Created default manager account 'john'.")


if __name__ == '__main__':
    app.run(debug=True)
