import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, cast, Date
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_long_and_random_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', "postgresql://aqua_db_whhd_user:kLmox5PxigU2zpBK96naPV2MomVsYrUZ@dpg-d2c68m3uibrs7385qomg-a/aqua_db_whhd")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    head_quarter = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50))
    address = db.Column(db.String(255))
    role = db.Column(db.String(10), nullable=False, default='employee')
    status = db.Column(db.String(15), nullable=False, default='inactive')
    last_login = db.Column(db.DateTime, default=None)

class Farmer(db.Model):
    __tablename__ = 'farmers'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    farmer_name = db.Column(db.String(100), nullable=False)
    num_of_ponds = db.Column(db.Integer, nullable=False)
    doc = db.Column(db.Date)
    contact_details = db.Column(db.String(100), nullable=False)
    products_using = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    notes = db.Column(db.Text)
    employee = db.relationship('Employee', backref=db.backref('farmers', lazy=True))

class Dealer(db.Model):
    __tablename__ = 'dealers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shop_name = db.Column(db.String(100))
    address = db.Column(db.String(255))
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    employee = db.relationship('Employee', backref=db.backref('dealers', lazy=True))

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.id'), nullable=True)
    dealer_id = db.Column(db.Integer, db.ForeignKey('dealers.id'), nullable=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    packing = db.Column(db.String(50))
    pacs_per_case = db.Column(db.Integer)
    mrp_per_pack = db.Column(db.Float)
    discount_percentage = db.Column(db.Float)
    discount_amount = db.Column(db.Float)
    sale_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('sales', lazy=True))
    dealer = db.relationship('Dealer', backref=db.backref('sales', lazy=True))
    farmer = db.relationship('Farmer', backref=db.backref('sales', lazy=True))

class DailyRoute(db.Model):
    __tablename__ = 'daily_routes'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    location_segment = db.Column(db.String(255), nullable=False)
    kms_segment = db.Column(db.Integer, nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    employee = db.relationship('Employee', backref=db.backref('routes', lazy=True))

# --- DATABASE INITIALIZATION ---
with app.app_context():
    db.create_all()
    if not Employee.query.filter_by(username='john').first():
        hashed_password = generate_password_hash('123')
        manager = Employee(username='john', password=hashed_password, head_quarter='HQ1', role='manager', status='active')
        db.session.add(manager)
        db.session.commit()

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
            return redirect(url_for('dashboard') if account.role == 'manager' else url_for('profile'))
        else:
            flash('Incorrect username/password or account deactivated.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'loggedin' in session:
        return redirect(url_for('profile'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        head_quarter = request.form['head_quarter']
        contact = request.form.get('contact')
        address = request.form.get('address')
        existing_account = Employee.query.filter_by(username=username).first()
        if existing_account:
            flash('An account with this username already exists.', 'danger')
            return render_template('register.html')
        hashed_password = generate_password_hash(password)
        new_employee = Employee(username=username, password=hashed_password, head_quarter=head_quarter, contact=contact, address=address, role='employee', status='inactive')
        db.session.add(new_employee)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            flash('New passwords do not match. Please try again.', 'danger')
            return redirect(url_for('forgot_password'))
        account = Employee.query.filter_by(username=username).first()
        if account:
            hashed_password = generate_password_hash(new_password)
            account.password = hashed_password
            db.session.commit()
            flash('Your password has been updated successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username not found. Please check and try again.', 'danger')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

# ### THIS IS THE CORRECTED FUNCTION ###
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))

    # --- Employee Progress Logic (Simplified and Corrected) ---
    employees = Employee.query.order_by(Employee.username).all()
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    for emp in employees:
        # Get last known location for each employee
        last_route = db.session.query(DailyRoute.location_segment)\
            .filter(DailyRoute.employee_id == emp.id)\
            .order_by(DailyRoute.entry_time.desc()).first()
        emp.location = last_route[0] if last_route else 'N/A'

        # Get total KMs covered today for each employee
        total_kms = db.session.query(func.sum(DailyRoute.kms_segment))\
            .filter(
                DailyRoute.employee_id == emp.id,
                DailyRoute.entry_time >= today_start
            ).scalar()
        emp.kms_covered = total_kms or 0

    # --- KPI and Chart Logic ---
    total_employees = Employee.query.filter_by(role='employee').count()
    total_farmers = Farmer.query.count()
    
    now = datetime.datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0)

    sales_this_month_val = db.session.query(func.sum(Sale.quantity_sold))\
        .filter(Sale.sale_date >= start_of_month).scalar() or 0

    top_employee_query = db.session.query(Employee)\
        .join(Sale, Employee.id == Sale.employee_id)\
        .filter(Sale.sale_date >= start_of_month)\
        .group_by(Employee.id).order_by(func.sum(Sale.quantity_sold).desc()).first()
    top_employee = top_employee_query if top_employee_query else None

    sales_locations = Farmer.query.filter(Farmer.latitude.isnot(None), Farmer.longitude.isnot(None)).all()
    sales_geo_data = [[f.latitude, f.longitude, 1] for f in sales_locations]

    # Chart Data
    sales_today_data = db.session.query(Employee.username, func.sum(Sale.quantity_sold).label('total_sales'))\
        .join(Sale, Employee.id == Sale.employee_id)\
        .filter(cast(Sale.sale_date, Date) == datetime.date.today())\
        .group_by(Employee.username).all()
    sales_today = [{'username': r.username, 'total_sales': r.total_sales or 0} for r in sales_today_data]

    sales_month_data = db.session.query(Employee.username, func.sum(Sale.quantity_sold).label('total_sales'))\
        .join(Sale, Employee.id == Sale.employee_id)\
        .filter(Sale.sale_date >= start_of_month)\
        .group_by(Employee.username).all()
    sales_month = [{'username': r.username, 'total_sales': r.total_sales or 0} for r in sales_month_data]
    
    return render_template(
        'dashboard.html',
        username=session.get('username'),
        employees=employees,
        total_employees=total_employees,
        total_farmers=total_farmers,
        sales_this_month=sales_this_month_val,
        top_employee=top_employee,
        sales_geo_data=sales_geo_data,
        sales_today=sales_today,
        sales_month=sales_month
    )

@app.route('/deactivate_employee/<int:employee_id>')
def deactivate_employee(employee_id):
    if 'loggedin' not in session or session.get('role') != 'manager':
        return redirect(url_for('login'))
    employee_to_deactivate = Employee.query.get(employee_id)
    if employee_to_deactivate and employee_to_deactivate.role != 'manager':
        employee_to_deactivate.status = 'deactivated'
        db.session.commit()
        flash(f"Employee '{employee_to_deactivate.username}' has been deactivated.", 'success')
    else:
        flash('Cannot deactivate this employee.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/farmer_details/<int:farmer_id>')
def farmer_details(farmer_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    farmer = Farmer.query.get_or_404(farmer_id)
    if session.get('role') != 'manager' and farmer.employee_id != session.get('id'):
        flash('You do not have permission to view this farmer.', 'danger')
        return redirect(url_for('farmers'))
    return render_template('farmer_details.html', farmer=farmer)

@app.route('/farmers', methods=['GET', 'POST'])
def farmers():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        doc_date = None
        doc_string = request.form.get('doc')
        if doc_string:
            try:
                doc_date = datetime.datetime.strptime(doc_string, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for DOC. Please use YYYY-MM-DD.', 'danger')
                return redirect(url_for('farmers'))
        new_farmer = Farmer(employee_id=session['id'], farmer_name=request.form['farmer_name'], num_of_ponds=request.form['num_of_ponds'], doc=doc_date, contact_details=request.form['contact_details'], products_using=request.form['products_using'], latitude=request.form.get('latitude') or None, longitude=request.form.get('longitude') or None, notes=request.form.get('notes'))
        db.session.add(new_farmer)
        db.session.commit()
        flash('Farmer added successfully!', 'success')
        return redirect(url_for('farmers'))
    user_farmers = Farmer.query.filter_by(employee_id=session['id']).all()
    return render_template('farmers.html', farmers=user_farmers, today=datetime.date.today())

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'add_dealer':
            new_dealer = Dealer(name=request.form['dealer_name'], shop_name=request.form['shop_name'], address=request.form['address'], employee_id=session['id'])
            db.session.add(new_dealer)
            db.session.commit()
            flash('Dealer added successfully!', 'success')
        elif form_type == 'dealer_sale':
            new_sale = Sale(employee_id=session['id'], dealer_id=request.form['dealer_id'], product_name=request.form['product_name'], packing=request.form['packing'], pacs_per_case=request.form['pacs_per_case'], mrp_per_pack=request.form['mrp_per_pack'], discount_percentage=request.form['discount_percentage'], discount_amount=request.form['discount_amount'])
            db.session.add(new_sale)
            db.session.commit()
            flash('Sale to dealer recorded successfully!', 'success')
        elif form_type == 'farmer_sale':
            new_sale = Sale(employee_id=session['id'], farmer_id=request.form['farmer_id'], product_name=request.form['product_name'], quantity_sold=request.form['quantity_sold'], prescription=request.form.get('prescription'))
            db.session.add(new_sale)
            db.session.commit()
            flash('Sale to farmer recorded successfully!', 'success')
        return redirect(url_for('sales'))
    dealers_list = Dealer.query.filter_by(employee_id=session['id']).all()
    farmers_list = Farmer.query.filter_by(employee_id=session['id']).all()
    recent_sales = db.session.query(Sale, Farmer.farmer_name, Dealer.name).outerjoin(Farmer).outerjoin(Dealer).filter(Sale.employee_id==session['id']).order_by(Sale.sale_date.desc()).limit(20).all()
    return render_template('sales.html', dealers=dealers_list, farmers=farmers_list, recent_sales=recent_sales)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    account = Employee.query.get(session['id'])
    if request.method == 'POST':
        new_route = DailyRoute(employee_id=session['id'], location_segment=request.form['location'], kms_segment=request.form['kms_covered'])
        db.session.add(new_route)
        db.session.commit()
        flash('Route segment added!', 'success')
        return redirect(url_for('profile'))
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    daily_routes_utc = DailyRoute.query.filter(DailyRoute.employee_id == session['id'], DailyRoute.entry_time >= today_start).all()
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    daily_routes_ist = []
    for route in daily_routes_utc:
        route.entry_time = route.entry_time + ist_offset
        daily_routes_ist.append(route)
    total_kms_today = sum(route.kms_segment for route in daily_routes_ist)
    return render_template('profile.html', account=account, daily_routes=daily_routes_ist, total_kms_today=total_kms_today, now=datetime.datetime.now() + ist_offset)
    
@app.route('/logout')
def logout():
    if 'loggedin' in session:
        employee = Employee.query.get(session['id'])
        if employee:
            employee.status = 'inactive'
            db.session.commit()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

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

if __name__ == '__main__':
    app.run(debug=True)