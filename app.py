from flask import Flask, url_for, render_template, session, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
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
    status = db.Column(db.String(20), nullable=False, default='Current') 
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)

    loan = db.relationship('Loan', backref=db.backref('payments', lazy=True))


#loan monthly class
class Loan(db.Model):
    __tablename__ = 'loan'
    loan_id = db.Column(db.Integer, primary_key=True)
    lender_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    application_date = db.Column(db.Date, nullable=False)
    months_to_pay = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Current')

#KLoan for months class
class LoanMonths(db.Model):
    __tablename__ = 'loan_months'

    loan_months_id = db.Column(db.Integer, primary_key=True)
    lender_name = db.Column(db.String(255), nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    application_date = db.Column(db.Date, nullable=False)
    
    due_date = db.Column(db.Date, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='Current')



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
@app.route('/superadmin', endpoint='superadmin_dashboard')
def superadmin_dashboard():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])

        today = date.today()

        # Fetch today's monthly payment loans
        loans = Loan.query.filter(Loan.application_date == today).all()
        
        # Fetch loan term records where due_date is today
        loans_term = LoanMonths.query.filter(LoanMonths.application_date == today).all()

        # Total applications and amounts
        total_amount = sum(loan.amount for loan in loans)
        total_applications = len(loans)
        total_term_applications = len(loans_term)

        # Count loans based on status
        month_current_loans = Loan.query.filter(Loan.status == 'Current').count()
        month_paid_loans = Loan.query.filter(Loan.status == 'Paid').count()
        month_overdue_loans = Loan.query.filter(Loan.status == 'Overdue').count()

        term_current_loans = LoanMonths.query.filter(LoanMonths.status == 'Current').count()
        term_paid_loans = LoanMonths.query.filter(LoanMonths.status == 'Paid').count()
        term_overdue_loans = LoanMonths.query.filter(LoanMonths.status == 'Overdue').count()

        overall_current_loans = month_current_loans + term_current_loans
        overall_paid_loans = month_paid_loans + term_paid_loans
        overall_overdue_loans = month_overdue_loans + term_overdue_loans

        return render_template(
            'superadmin/superadmin_dashboard.html',
            username=user.username,
            loans=loans,
            loans_term=loans_term,
            total_amount=total_amount,
            total_applications=total_applications,
            total_term_applications=total_term_applications,
            total_current_loans=overall_current_loans,
            total_paid_loans=overall_paid_loans,
            total_overdue_loans=overall_overdue_loans
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/monitoring_term', endpoint='superadmin_monitoring_terms')
def superadmin_monitoring_terms():
    if 'role' in session and session['role'] == 'superadmin':
        loans_term = LoanMonths.query.all()
        total_applications = LoanMonths.query.count()
        user = db.session.get(User, session['user_id'])
        
        return render_template('/superadmin/monitoring_term.html', loans_term=loans_term, total_applications=total_applications, username=user.username)
    
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

@app.route('/superadmin/monitoring', endpoint='superadmin_monitoring')
def superadmin_monitoring():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        loans = Loan.query.all()
        total_amount = sum(loan.amount for loan in loans)  # Calculate total loan amount
        total_applications = len(loans)  # Count total applications

        today = date.today()

        for loan in loans:
            total_paid = db.session.query(db.func.sum(LoanPayment.amount_paid))\
                .filter_by(loan_id=loan.loan_id).scalar() or 0

            overdue_payments = LoanPayment.query.filter(
                LoanPayment.loan_id == loan.loan_id,
                LoanPayment.due_date < today,  # Overdue only if due date is past
                LoanPayment.amount_paid < LoanPayment.amount_due  # Payment not met
            ).count()

            # Determine loan status
            if total_paid >= loan.amount:
                loan.status = "Paid"  # Fully paid
            elif overdue_payments > 0:
                loan.status = "Overdue"  # Has overdue payments
            else:
                loan.status = "Current"  # Payments ongoing and not overdue


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

#route to add monthly page
@app.route('/add-monthly-loan', endpoint='add_monthly_loan')
def add_monthly_loan():
    if 'role' in session and session['role'] == 'superadmin':
        return render_template('add_monthly_loan.html')
    
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
            monthly_payment=monthly_payment,
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

    #add term loan
@app.route('/add_term_loan', methods=['POST'])
def add_term_loan():
    try:
        lender_name = request.form.get('lender_name')
        amount = float(request.form.get('amount'))
        months_to_pay = int(request.form.get('months_to_pay'))
        monthly_payment = amount / months_to_pay  # Auto-calculate monthly payment

        # Get application date (or default to today if not provided)
        application_date_str = request.form.get('application_date')
        application_date = datetime.strptime(application_date_str, "%Y-%m-%d") if application_date_str else datetime.now()

        # Calculate due date (last payment date)
        due_date = application_date + relativedelta(months=months_to_pay)

        # Create and save loan
        new_loan = LoanMonths(
            lender_name=lender_name,
            loan_amount=amount,
            application_date=application_date,
            due_date=due_date,
            paid_amount=0.0,
            status="Current"
        )
        db.session.add(new_loan)
        db.session.flush()  # Get new_loan.loan_months_id before inserting payments


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

        # Update status dynamically before rendering
        for payment in payments:
            due_date = payment.due_date  # No need for .date() if it's already a date object

            if payment.amount_due > 0 and due_date < date.today():  # If past due date & unpaid
                payment.status = "Overdue"
            elif payment.amount_due == 0:  # If fully paid
                payment.status = "Paid"
            else:  # Otherwise, it's still active
                payment.status = "Current"

        db.session.commit()  # Save updates to the database

        return render_template(
            'loan_schedule.html',
            username=user.username,
            loan=loan,
            payments=payments
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#partial payment for monthly

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

#edit for monthly
@app.route('/edit_monthly_loan/<int:loan_id>', methods=['GET', 'POST'], endpoint="edit_monthly_loan")
def edit_monthly_loan(loan_id):
    if 'role' in session and session['role'] == 'superadmin':
        loan = db.session.get(Loan, loan_id)

        if not loan:
            flash("Loan not found!", "danger")
            return redirect(url_for('superadmin_monitoring'))

        if request.method == 'POST':
            try:
                # Get updated loan details
                loan.lender_name = request.form.get('lender_name')
                loan.amount = float(request.form.get('amount'))
                loan.months_to_pay = int(request.form.get('months_to_pay'))
                loan.application_date = datetime.strptime(request.form.get('application_date'), "%Y-%m-%d")
                loan.monthly_payment = loan.amount / loan.months_to_pay

                # Delete existing loan payments
                LoanPayment.query.filter_by(loan_id=loan.loan_id).delete()

                # Generate new loan payment schedule
                due_date = loan.application_date
                for _ in range(loan.months_to_pay):
                    due_date += relativedelta(months=1)  # Increment by one month
                    new_payment = LoanPayment(
                        loan_id=loan.loan_id, 
                        due_date=due_date,
                        amount_due=loan.monthly_payment,
                        status='Current'
                    )
                    db.session.add(new_payment)

                db.session.commit()
                flash("Loan and payment schedule updated successfully!", "success")
                return redirect(url_for('superadmin_monitoring'))

            except Exception as e:
                db.session.rollback()
                flash(f"Error updating loan: {str(e)}", "danger")

        return render_template('edit_monthly_loan.html', loan=loan)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))



#partial payment for term

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



