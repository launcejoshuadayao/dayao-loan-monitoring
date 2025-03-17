from flask import Flask, url_for, render_template, session, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta


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


#loan payment class
class LoanPayment(db.Model):
    __tablename__ = 'loan_payments'
    loan_payment_id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.loan_id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    status = db.Column(db.Enum('Pending', 'Paid'), default='Pending', nullable=False)

    loan = db.relationship('Loan', backref=db.backref('payments', lazy=True))


#loan class
class Loan(db.Model):
    __tablename__ = 'loan'
    loan_id = db.Column(db.Integer, primary_key=True)
    lender_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    application_date = db.Column(db.Date, nullable=False)
    months_to_pay = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Float, nullable=False)



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
        loans = Loan.query.all()  
        total_amount = sum(loan.amount for loan in loans)  # Calculate total loan amount
        total_applications = len(loans)  # Count total applications
        
        return render_template(
            'superadmin/superadmin_dashboard.html',
            username=user.username,
            loans=loans,
            total_amount=total_amount,
            total_applications=total_applications
        )
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/monitoring', endpoint='superadmin_monitoring')
def superadmin_monitoring():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        loans = Loan.query.all()  
        total_amount = sum(loan.amount for loan in loans)  # Calculate total loan amount
        total_applications = len(loans)  # Count total applications
        
        return render_template(
            'superadmin/monitoring.html',
            username=user.username,
            loans=loans,
            total_amount=total_amount,
            total_applications=total_applications
        )
    
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

@app.route('/add-loan', methods=['POST'])
def add_loan():
    try:
        lender_name = request.form.get('lender_name')
        amount = float(request.form.get('amount'))
        application_date = request.form.get('application_date')
        months_to_pay = int(request.form.get('months_to_pay'))
        monthly_payment = amount / months_to_pay

       
        new_loan = Loan(
            lender_name=lender_name,
            amount=amount,
            application_date=datetime.strptime(application_date, "%Y-%m-%d"),
            months_to_pay=months_to_pay,
            monthly_payment=monthly_payment
        )
        db.session.add(new_loan)
        db.session.flush()  

       
        due_date = datetime.strptime(application_date, "%Y-%m-%d")
        for _ in range(months_to_pay):
            due_date += timedelta(days=30)  
            new_payment = LoanPayment(
                loan_id=new_loan.loan_id, 
                due_date=due_date,
                amount_due=monthly_payment,
                status='Pending'
            )
            db.session.add(new_payment)

        db.session.commit()

        return jsonify({"success": True, "message": "Loan and payments added successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

#admin --------------------------------------------------------------------------------------
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



