from flask import Flask, url_for, render_template, session, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/loan_monitoring'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_PERMANENT'] = False 

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('superadmin', 'admin'), nullable=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        if session['role'] == 'superadmin':
            return redirect(url_for('superadmin_dashboard'))
        elif session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Store user ID
            session['role'] = user.role  # Store user role

           

            #Redirect to correct dashboard
            if user.role == 'superadmin':
                flash("Login Successful!",  "success")
                return redirect(url_for('superadmin_dashboard'))
            elif user.role == 'admin':
                flash("Login Successful!", "success")
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Login Failed!",  "error")

    return render_template('login.html')


#superadmin --------------------------------------------------------------------------
@app.route('/superadmin',  endpoint='superadmin_dashboard')
def superadmin_dashboard():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/superadmin_dashboard.html', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/monitoring', endpoint='superadmin_monitoring')
def superadmin_monitoring():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/monitoring.html', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/paid-loans')
def superadmin_paid_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/paid_loans.html', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/overdue-loans')
def superadmin_overdue_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/overdue_loans.html', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/activity-logs')
def superadmin_activity_logs():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/logs.html', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/manage-users')
def superadmin_manage_users():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/manage_users', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#admin --------------------------------------------------------------------------------------
@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin/admin_dashboard.html')
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


#addloan -----------------------------
@app.route('/add-loan', methods=['POST'])
def add_loan():
    lender_name = request.form.get('lender_name')
    amount = request.form.get('amount')
    application_date = request.form.get('application_date')
    months_to_pay = request.form.get('months_to_pay')
    monthly_payment = float(amount) / int(months_to_pay)

    sql = "INSERT INTO loans (lender_name, amount, application_date, months_to_pay, monthly_payment) VALUES (%s, %s, %s, %s, %s)"
    values = (lender_name, amount, application_date, months_to_pay, monthly_payment)

    cursor = db.connection.cursor()
    cursor.execute(sql, values)
    db.connection.commit()
    cursor.close()

    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


@app.route('/')
def hello():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)