import os
from datetime import datetime, date
import re
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- App Configuration ---
app.secret_key = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Noor@818' # Change to your password
app.config['MYSQL_DB'] = 'aquaculture_db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

mysql = MySQL(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# =================================================================
#                        AUTHENTICATION & CORE ROUTES
# =================================================================

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employees WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            if account['status'] == 'deactivated':
                return render_template('login.html', msg='Your account is deactivated.')
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['role'] = account['role']
            cursor.execute('UPDATE employees SET status = %s, last_login = %s WHERE id = %s', ('active', datetime.now(), account['id'],))
            mysql.connection.commit()
            if account['role'] == 'manager':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('profile'))
        else:
            return render_template('login.html', msg='Incorrect username/password!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username, password, head_quarter, role = request.form['username'], request.form['password'], request.form['head_quarter'], 'employee'
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employees WHERE username = %s', (username,))
        if cursor.fetchone():
            msg = 'Account with that username already exists!'
        else:
            cursor.execute('INSERT INTO employees (username, password, head_quarter, role) VALUES (%s, %s, %s, %s)', (username, password, head_quarter, role))
            mysql.connection.commit()
            return redirect(url_for('login', msg='You have successfully registered! Please login.'))
    return render_template('register.html', msg=msg)

@app.route('/logout')
def logout():
    if 'id' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE employees SET status = %s WHERE id = %s', ('inactive', session['id'],))
        mysql.connection.commit()
    session.clear()
    return redirect(url_for('login'))

# =================================================================
#                        PROFILE & ROUTE TRACKING
# =================================================================

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    msg = ''

    if request.method == 'POST':
        location = request.form['location']
        kms_covered = request.form['kms_covered']
        cursor.execute('INSERT INTO daily_routes (employee_id, location_segment, kms_segment, entry_time) VALUES (%s, %s, %s, %s)',
                       (session['id'], location, kms_covered, datetime.now()))
        cursor.execute("SELECT SUM(kms_segment) as total_kms FROM daily_routes WHERE employee_id = %s AND DATE(entry_time) = CURDATE()", (session['id'],))
        total_kms_today = cursor.fetchone()['total_kms'] or 0
        cursor.execute("UPDATE employees SET location = %s, kms_covered = %s WHERE id = %s", (location, total_kms_today, session['id']))
        mysql.connection.commit()
        msg = "Route segment added successfully!"

    cursor.execute('SELECT * FROM employees WHERE id = %s', (session['id'],))
    account = cursor.fetchone()
    cursor.execute("SELECT * FROM daily_routes WHERE employee_id = %s AND DATE(entry_time) = CURDATE() ORDER BY entry_time ASC", (session['id'],))
    daily_routes = cursor.fetchall()
    total_kms_today = sum(route['kms_segment'] for route in daily_routes)

    return render_template('profile.html', account=account, daily_routes=daily_routes, total_kms_today=total_kms_today, now=datetime.now(), msg=msg)

# =================================================================
#                        MANAGER & EMPLOYEE ROUTES
# =================================================================

@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'manager':
        return redirect(url_for('profile')) 

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # --- KPI Data ---
    cursor.execute("SELECT COUNT(id) as count FROM employees WHERE status != 'deactivated'")
    total_employees = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(id) as count FROM farmers")
    total_farmers = cursor.fetchone()['count']
    cursor.execute("SELECT SUM(quantity_sold) as total_sales FROM sales WHERE MONTH(sale_date) = MONTH(CURDATE()) AND YEAR(sale_date) = YEAR(CURDATE())")
    sales_this_month = (cursor.fetchone() or {'total_sales': 0})['total_sales'] or 0
    cursor.execute("""
        SELECT e.username, SUM(s.quantity_sold) as total_sales FROM sales s JOIN employees e ON s.employee_id = e.id
        WHERE MONTH(s.sale_date) = MONTH(CURDATE()) AND YEAR(s.sale_date) = YEAR(CURDATE())
        GROUP BY e.username ORDER BY total_sales DESC LIMIT 1
    """)
    top_employee = cursor.fetchone()

    # --- Geographical Sales Data for Heatmap ---
    cursor.execute("""
        SELECT f.latitude, f.longitude, SUM(s.quantity_sold) as sales_intensity
        FROM sales s
        JOIN farmers f ON s.farmer_id = f.id
        WHERE f.latitude IS NOT NULL AND f.longitude IS NOT NULL AND MONTH(s.sale_date) = MONTH(CURDATE())
        GROUP BY f.id, f.latitude, f.longitude;
    """)
    geo_data_raw = cursor.fetchall()
    sales_geo_data = [[float(row['latitude']), float(row['longitude']), row['sales_intensity']] for row in geo_data_raw]

    # --- Other Data ---
    cursor.execute("SELECT id, username, head_quarter, role, status, last_login, location, kms_covered FROM employees")
    all_employees = cursor.fetchall()
    cursor.execute("SELECT e.username, SUM(s.quantity_sold) as total_sales FROM sales s JOIN employees e ON s.employee_id = e.id WHERE DATE(s.sale_date) = CURDATE() GROUP BY e.username")
    sales_today = cursor.fetchall()
    cursor.execute("SELECT e.username, SUM(s.quantity_sold) as total_sales FROM sales s JOIN employees e ON s.employee_id = e.id WHERE MONTH(s.sale_date) = MONTH(CURDATE()) AND YEAR(s.sale_date) = YEAR(CURDATE()) GROUP BY e.username")
    sales_month_chart = cursor.fetchall()
    
    return render_template('dashboard.html', 
                           username=session['username'], 
                           employees=all_employees,
                           total_employees=total_employees,
                           total_farmers=total_farmers,
                           sales_this_month=sales_this_month,
                           top_employee=top_employee,
                           sales_today=sales_today, 
                           sales_month=sales_month_chart,
                           sales_geo_data=sales_geo_data)

@app.route('/employees', methods=['GET', 'POST'])
def employees():
    if 'loggedin' not in session or session.get('role') != 'manager': 
        return redirect(url_for('profile'))
    
    msg = ''
    if request.method == 'POST':
        username, password, head_quarter, role = request.form['username'], request.form['password'], request.form['head_quarter'], request.form['role']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employees WHERE username = %s', (username,))
        if cursor.fetchone():
            msg = 'Employee with that username already exists!'
        else:
            cursor.execute('INSERT INTO employees (username, password, head_quarter, role) VALUES (%s, %s, %s, %s)', (username, password, head_quarter, role))
            mysql.connection.commit()
            msg = 'New employee added successfully!'
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, username, head_quarter, role, status FROM employees")
    all_employees = cursor.fetchall()
    return render_template('employees.html', employees=all_employees, msg=msg)

@app.route('/deactivate_employee/<int:employee_id>')
def deactivate_employee(employee_id):
    if 'loggedin' not in session or session.get('role') != 'manager': 
        return redirect(url_for('profile'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("UPDATE employees SET status = 'deactivated' WHERE id = %s", (employee_id,))
    mysql.connection.commit()
    return redirect(url_for('dashboard'))

@app.route('/farmers', methods=['GET', 'POST'])
def farmers():
    if 'loggedin' not in session: 
        return redirect(url_for('login'))
    
    msg = ''
    if request.method == 'POST':
        proof_path = None
        if 'visit_proof' in request.files:
            file = request.files['visit_proof']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                proof_path = f"uploads/{unique_filename}"
        
        farmer_name = request.form['farmer_name']
        num_of_ponds = request.form['num_of_ponds']
        doc = request.form['doc']
        contact = request.form['contact_details']
        products = request.form['products_using']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO farmers (employee_id, farmer_name, num_of_ponds, doc, contact_details, products_using, visit_proof_path, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                       (session['id'], farmer_name, num_of_ponds, doc, contact, products, proof_path, latitude, longitude))
        mysql.connection.commit()
        msg = 'New farmer added successfully!'
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM farmers WHERE employee_id = %s", (session['id'],))
    user_farmers = cursor.fetchall()
    return render_template('farmers.html', farmers=user_farmers, msg=msg)

@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if 'loggedin' not in session: 
        return redirect(url_for('login'))
    
    msg = ''
    if request.method == 'POST':
        farmer_id, product_name, quantity_sold, prescription = request.form['farmer_id'], request.form['product_name'], request.form['quantity_sold'], request.form.get('prescription', '')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO sales (employee_id, farmer_id, product_name, quantity_sold, prescription, sale_date) VALUES (%s, %s, %s, %s, %s, %s)',
                       (session['id'], farmer_id, product_name, quantity_sold, prescription, datetime.now()))
        mysql.connection.commit()
        msg = 'Sale recorded successfully!'
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT id, farmer_name FROM farmers WHERE employee_id = %s", (session['id'],))
    user_farmers = cursor.fetchall()
    
    cursor.execute("SELECT s.*, f.farmer_name FROM sales s JOIN farmers f ON s.farmer_id = f.id WHERE s.employee_id = %s ORDER BY s.sale_date DESC LIMIT 10", (session['id'],))
    recent_sales = cursor.fetchall()
    return render_template('sales.html', farmers=user_farmers, recent_sales=recent_sales, msg=msg)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
