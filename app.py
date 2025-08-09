import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime

# --- APP CONFIGURATION ---
app = Flask(__name__)

# Configure a secret key for session management
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_long_and_random_secret_key')

# --- DIRECT DATABASE CONNECTION ---
# ⚠️ PASTE YOUR NEW RENDER DATABASE INTERNAL CONNECTION STRING HERE ⚠️
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://aqua_db_w5l9_user:KOCJ1ssQ3WsAcDh8omgEMpWKvfGePVCF@dpg-d2brsb7diees73f2l50g-a/aqua_db_w5l9"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure the upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# Initialize the database extension
db = SQLAlchemy(app)


# --- DATABASE MODELS (Matching your aquaculture_db.sql) ---
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    head_quarter = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50))
    address = db.Column(db.String(255))
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
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
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

class DailyRoute(db.Model):
    __tablename__ = 'daily_routes'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    location_segment = db.Column(db.String(255), nullable=False)
    kms_segment = db.Column(db.Integer, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('routes', lazy=True))


# --- Auto-create Database Tables ---
with app.app_context():
    db.create_all()
    if not Employee.query.filter_by(username='john').first():
        hashed_password = generate_password_hash('123')
        manager = Employee(username='john', password=hashed_password, head_quarter='HQ1', role='manager', status='active')
        db.session.add(manager)
        db.session.commit()
        print("Database tables created and default manager added.")

# --- HELPER FUNCTIONS ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        account = Employee.query.filter_by(username=username).first()
        if account and account.status != 'deactivated' and check_password_hash(account.password, password):
            session['loggedin'] = True
            session['id'] = account.id
            session['username'] = account.username
            session['role'] = account.role
            account.last_login = datetime.datetime.utcnow()
            account.status = 'active'
            db.session.commit()
            if account.role == 'manager':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('profile'))
        else:
            flash('Incorrect username/password or account deactivated.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        head_quarter = request.form['head_quarter']
        contact = request.form['contact']
        address = request.form['address']
        if Employee.query.filter_by(username=username).first():
            flash('Account with that username already exists!', 'warning')
            return render_template('register.html')
        hashed_password = generate_password_hash(password)
        new_employee = Employee(
            username=username, 
            password=hashed_password, 
            head_quarter=head_quarter, 
            contact=contact, 
            address=address,
            role='employee'
        )
        db.session.add(new_employee)
        db.session.commit()
        flash('You have successfully registered! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('forgot_password'))

        account = Employee.query.filter_by(username=username).first()
        if account:
            account.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Your password has been updated successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('No account found with that username.', 'danger')
            return redirect(url_for('forgot_password'))
            
    return render_template('forgot_password.html')

@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))
    
    total_employees = db.session.query(func.count(Employee.id)).filter_by(role='employee').scalar()
    total_farmers = db.session.query(func.count(Farmer.id)).scalar()
    now = datetime.datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sales_this_month = db.session.query(func.sum(Sale.quantity_sold)).filter(Sale.sale_date >= start_of_month).scalar() or 0
    employees_list = Employee.query.all()
    top_employee_query = db.session.query(Employee.username, func.sum(Sale.quantity_sold).label('total_sales')).join(Sale).filter(Sale.sale_date >= start_of_month).group_by(Employee.username).order_by(func.sum(Sale.quantity_sold).desc()).first()
    top_employee = {'username': top_employee_query[0]} if top_employee_query else None
    sales_locations = db.session.query(Farmer.latitude, Farmer.longitude, func.sum(Sale.quantity_sold)).join(Sale).filter(Farmer.latitude.isnot(None), Farmer.longitude.isnot(None), Sale.sale_date >= start_of_month).group_by(Farmer.latitude, Farmer.longitude).all()
    sales_geo_data = [[lat, lng, intensity] for lat, lng, intensity in sales_locations]
    sales_today_query = db.session.query(Employee.username, func.sum(Sale.quantity_sold)).join(Sale).filter(Sale.sale_date >= start_of_today).group_by(Employee.username).all()
    sales_today_data = [{'username': username, 'total_sales': total} for username, total in sales_today_query]
    sales_month_query = db.session.query(Employee.username, func.sum(Sale.quantity_sold)).join(Sale).filter(Sale.sale_date >= start_of_month).group_by(Employee.username).all()
    sales_month_data = [{'username': username, 'total_sales': total} for username, total in sales_month_query]

    return render_template(
        'dashboard.html',
        username=session['username'], total_employees=total_employees, total_farmers=total_farmers,
        sales_this_month=sales_this_month, top_employee=top_employee, employees=employees_list,
        sales_today=sales_today_data, sales_month=sales_month_data, sales_geo_data=sales_geo_data
    )

@app.route('/employees', methods=['GET', 'POST'])
def employees():
    if 'loggedin' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        head_quarter = request.form['head_quarter']
        role = request.form['role']
        contact = request.form['contact']
        address = request.form['address']
        if not Employee.query.filter_by(username=username).first():
            hashed_password = generate_password_hash(password)
            new_employee = Employee(username=username, password=hashed_password, head_quarter=head_quarter, role=role, contact=contact, address=address)
            db.session.add(new_employee)
            db.session.commit()
            flash('Employee added successfully!', 'success')
        else:
            flash('Employee with that username already exists.', 'danger')
        return redirect(url_for('employees'))
    
    all_employees = Employee.query.all()
    return render_template('employees.html', employees=all_employees)

@app.route('/deactivate_employee/<int:employee_id>')
def deactivate_employee(employee_id):
    if 'loggedin' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))
    employee = Employee.query.get_or_404(employee_id)
    if employee.role != 'manager':
        employee.status = 'deactivated'
        db.session.commit()
        flash(f'Employee {employee.username} has been deactivated.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/farmers', methods=['GET', 'POST'])
def farmers():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        visit_proof_filename = None
        if 'visit_proof' in request.files:
            file = request.files['visit_proof']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                visit_proof_filename = filename
        new_farmer = Farmer(employee_id=session['id'], farmer_name=request.form['farmer_name'], num_of_ponds=request.form['num_of_ponds'], doc=request.form['doc'], contact_details=request.form['contact_details'], products_using=request.form['products_using'], latitude=request.form.get('latitude'), longitude=request.form.get('longitude'), visit_proof_path=visit_proof_filename)
        db.session.add(new_farmer)
        db.session.commit()
        flash('Farmer added successfully!', 'success')
        return redirect(url_for('farmers'))
    user_farmers = Farmer.query.filter_by(employee_id=session['id']).all()
    return render_template('farmers.html', farmers=user_farmers)

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    farmers_list = Farmer.query.filter_by(employee_id=session['id']).all()
    if request.method == 'POST':
        new_sale = Sale(employee_id=session['id'], farmer_id=request.form['farmer_id'], product_name=request.form['product_name'], quantity_sold=request.form['quantity_sold'], prescription=request.form.get('prescription'))
        db.session.add(new_sale)
        db.session.commit()
        flash('Sale recorded successfully!', 'success')
        return redirect(url_for('sales'))
    sales_with_farmer = db.session.query(Sale, Farmer.farmer_name).join(Farmer).filter(Sale.employee_id==session['id']).order_by(Sale.sale_date.desc()).limit(20).all()
    recent_sales_formatted = [{'sale_date': s.sale_date, 'farmer_name': fn, 'product_name': s.product_name, 'quantity_sold': s.quantity_sold} for s, fn in sales_with_farmer]
    return render_template('sales.html', farmers=farmers_list, recent_sales=recent_sales_formatted)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    account = Employee.query.get(session['id'])
    if request.method == 'POST':
        new_route = DailyRoute(employee_id=session['id'], location_segment=request.form['location'], kms_segment=request.form['kms_covered'])
        db.session.add(new_route)
        account.kms_covered = (account.kms_covered or 0) + int(request.form['kms_covered'])
        db.session.commit()
        flash('Route segment added!', 'success')
        return redirect(url_for('profile'))
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    daily_routes = DailyRoute.query.filter(DailyRoute.employee_id == session['id'], DailyRoute.entry_time >= today_start).all()
    total_kms_today = sum(route.kms_segment for route in daily_routes)
    return render_template('profile.html', account=account, daily_routes=daily_routes, total_kms_today=total_kms_today, now=datetime.datetime.now())

# --- UPDATED LOGOUT ROUTE ---
@app.route('/logout')
def logout():
    if 'loggedin' in session:
        # Find the employee and update their status to inactive
        employee = Employee.query.get(session['id'])
        if employee:
            employee.status = 'inactive'
            db.session.commit()
    
    # Clear the session data
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
