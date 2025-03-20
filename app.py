from flask import Flask, url_for, render_template, session, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


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
    status = db.Column(db.String(20), nullable=False, default='Active') 
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)

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
    status = db.Column(db.String(20), default='Active')



@app.route('/login', methods=['GET', 'POST'])
def login():

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
            session['user_id'] = user.id  
            session['role'] = user.role  

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
    

        for loan in loans:
            total_paid = db.session.query(db.func.sum(LoanPayment.amount_due))\
                .filter_by(loan_id=loan.loan_id).scalar() or 0
            if total_paid == 0:
                loan.status = "Active"
            elif total_paid > 0 and total_paid < loan.amount:
                loan.status = "Partially Paid"
            elif total_paid >= loan.amount:
                loan.status = "Fully Paid"
            else:
                overdue_payments = LoanPayment.query.filter_by(loan_id=loan.loan_id, status='Pending').count()
                if overdue_payments > 0:
                    loan.status = "Overdue"

        db.session.commit()
        
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
        months_to_pay = int(request.form.get('months_to_pay'))
        monthly_payment = amount / months_to_pay

        # Ensure application_date is properly formatted
        application_date_str = request.form.get('application_date')
        if application_date_str:  # If user provides a date
            application_date = datetime.strptime(application_date_str, "%Y-%m-%d")
        else:  # If no date is provided, default to today
            application_date = datetime.now()

        new_loan = Loan(
            lender_name=lender_name,
            amount=amount,
            application_date=application_date,
            months_to_pay=months_to_pay,
            monthly_payment=monthly_payment
        )
        db.session.add(new_loan)
        db.session.flush()  

        # Generate payment schedule
        due_date = application_date
        for _ in range(months_to_pay):
            due_date += relativedelta(months=1)  # Increment by one month
            new_payment = LoanPayment(
                loan_id=new_loan.loan_id, 
                due_date=due_date,
                amount_due=monthly_payment,
                status='Active'
            )
            db.session.add(new_payment)

        db.session.commit()

        return jsonify({"success": True, "message": "Loan and payments added successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})   


@app.route('/loan_schedule/<int:loan_id>', endpoint='loan_schedule')
def loan_schedule(loan_id):
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        loan = db.session.get(Loan, loan_id)

        if not loan:
            flash("Loan not found!", "danger")
            return redirect(url_for('superadmin_monitoring'))

        payments = LoanPayment.query.filter_by(loan_id=loan_id).order_by(LoanPayment.due_date).all()

        return render_template(
            'loan_schedule.html',
            username=user.username,
            loan=loan,
            payments=payments
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/partial_payment', methods=['POST'])
def partial_payment():
    loan_payment_id = request.form.get('loan_payment_id')
    amount_paid = float(request.form.get('amount_paid'))

    payment = LoanPayment.query.get(loan_payment_id)

    if not payment:
        flash("Payment record not found!", "danger")
        return redirect(url_for('loan_schedule', loan_id=payment.loan_id))
    
    payment.amount_paid += amount_paid  
    payment.amount_due -= amount_paid 
    
    if payment.amount_due <= 0:
        payment.status = "Paid"
        
    db.session.commit()
    flash("Payment recorded successfully!", "success")
    return redirect(url_for('loan_schedule', loan_id=payment.loan_id))
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



