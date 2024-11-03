from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from functools import wraps
from datetime import datetime
from config import config
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config.from_object(config)
mysql = MySQL(app)

# User signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')  # Store directly without hashing
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        # Password matching check
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO users (name, username, email, password, role)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, username, email, password, role))  # Store plain password here
            mysql.connection.commit()
            cur.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')




# index route
@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        print("Attempting index with:", email)  # Debug

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            print("User found:", user)  # Debug
        else:
            print("No user found with that email.")  # Debug

        if user and user['password'] == password:  # Direct comparison
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['logged_in'] = True
            flash('index successful!', 'success')
            
            # Redirect based on role
            if user['role'] == 'Admin':
                print("Redirecting to admin dashboard")  # Debug
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'User':
                print("Redirecting to user dashboard")  # Debug
                return redirect(url_for('user_dashboard'))
            else:
                flash('Role not recognized.', 'danger')
                return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('index'))

    return render_template('index.html')



# index required decorator
def index_required(roles=None):
    if roles is None:
        roles = []

    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('You need to log in first!', 'danger')
                return redirect(url_for('index'))
            if roles and session.get('role') not in roles:
                flash('You do not have access to this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# User dashboard with complaint submission form
@app.route('/user-dashboard', methods=['GET', 'POST'])
@index_required(roles=["User"])
def user_dashboard():
    if request.method == 'POST':
        name = request.form['name']
        issue_type = ', '.join(request.form.getlist('complaint'))
        custom_complaint = request.form['own-complaint']
        address = request.form['address']
        user_id = session.get('user_id')

        # Insert complaint details into the database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO complaints (user_id, name, issue_type, custom_complaint, address, status, date_created)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, name, issue_type, custom_complaint, address, 'Submitted', datetime.now()))
        mysql.connection.commit()
        cur.close()
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM complaints WHERE user_id = %s", (session.get('user_id'),))
    complaints = cur.fetchall()
    cur.close()
    return render_template('user_dashboard.html', complaints=complaints)

# Admin dashboard to view and update complaints
@app.route('/admin-dashboard', methods=['GET', 'POST'])
@index_required(roles=["Admin"])
def admin_dashboard():
    if request.method == 'POST':
        complaint_id = request.form['complaint_id']
        new_status = request.form['status']

        cur = mysql.connection.cursor()
        cur.execute("UPDATE complaints SET status = %s WHERE id = %s", (new_status, complaint_id))
        mysql.connection.commit()
        cur.close()
        flash('Complaint status updated successfully!', 'success')
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM complaints")
    complaints = cur.fetchall()
    cur.close()
    return render_template('admin_dashboard.html', complaints=complaints)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    app.run(debug=True)
