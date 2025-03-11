from flask import Flask, url_for, render_template, session, redirect, request, flash
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


#superadmin
@app.route('/superadmin')
def superadmin_dashboard():
    if 'role' in session and session['role'] == 'superadmin':
        return render_template('superadmin/superadmin_dashboard.html')
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        return render_template('admin/admin_dashboard.html')
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

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