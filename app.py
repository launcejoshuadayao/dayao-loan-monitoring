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
    archived = db.Column(db.Boolean, default=False)

#KLoan for months class
class LoanMonths(db.Model):
    __tablename__ = 'loan_months'

    loan_months_id = db.Column(db.Integer, primary_key=True)
    lender_name = db.Column(db.String(255), nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    application_date = db.Column(db.Date, nullable=False)
    months_to_pay = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    penalty_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='Current')
    archived = db.Column(db.Boolean, default=False)

#Monthly Loan Payment History
class PaymentHistory(db.Model):
    __tablename__ = 'months_payment_history'

    id = db.Column(db.Integer, primary_key=True)
    loan_payment_id = db.Column(db.Integer, db.ForeignKey('loan_payments.loan_payment_id'), nullable=False)
    date_paid = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)    
    remarks = db.Column(db.String(100))  # Optional

    loan_payment = db.relationship('LoanPayment', backref=db.backref('history', lazy=True))

#Term Loan Payment History
class TermPaymentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_months_id = db.Column(db.Integer, db.ForeignKey('loan_months.loan_months_id'))  # ✅ correct column
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float)
    remarks = db.Column(db.String(255), nullable=True)

    loan = db.relationship('LoanMonths', backref=db.backref('payment_histories', lazy=True))
    loan_months_id = db.Column(db.Integer, db.ForeignKey('loan_months.loan_months_id'))


#llogin
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
                flash(f"Welcome {username}! Login Successful!",  "success")
                return redirect(url_for('superadmin_dashboard'))
            elif user.role == 'admin':
                flash("Login Successful!", "success")
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Login Failed!",  "error")

    return render_template('login.html')


#superadmin --------------------------------------------------------------------------

#superadmin dashboard
@app.route('/superadmin', endpoint='superadmin_dashboard')
def superadmin_dashboard():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])

        today = date.today()

        loans = Loan.query.filter(Loan.application_date == today).all()
    
        loans_term = LoanMonths.query.filter(LoanMonths.application_date == today, Loan.archived == 'False').all()

        total_amount = sum(loan.amount for loan in loans)
        total_applications = len(loans)
        total_term_applications = len(loans_term)

        month_current_loans = Loan.query.filter(Loan.status == 'Current', Loan.archived== 'False').count()
        month_paid_loans = Loan.query.filter(Loan.status == 'Paid', Loan.archived== 'False').count()
        month_overdue_loans = Loan.query.filter(Loan.status == 'Overdue', Loan.archived== 'False').count()

        term_current_loans = LoanMonths.query.filter(LoanMonths.status == 'Current', LoanMonths.archived== 'False').count()
        term_paid_loans = LoanMonths.query.filter(LoanMonths.status == 'Paid', LoanMonths.archived== 'False').count()
        term_overdue_loans = LoanMonths.query.filter(LoanMonths.status == 'Overdue', LoanMonths.archived== 'False').count()

        overall_current_loans = month_current_loans + term_current_loans
        overall_paid_loans = month_paid_loans + term_paid_loans
        overall_overdue_loans = month_overdue_loans + term_overdue_loans

        total_users = User.query.filter(User.id).count()

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
            total_overdue_loans=overall_overdue_loans,
            total_users=total_users
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


#term loan route
@app.route('/superadmin/monitoring_term', endpoint='superadmin_monitoring_terms')
def superadmin_monitoring_terms():
    if 'role' in session and session['role'] == 'superadmin':
        loans_term = LoanMonths.query.filter(LoanMonths.status.in_(['Current']), LoanMonths.archived == False).all()

        for loan in loans_term:
            loan.payment_history = TermPaymentHistory.query.filter_by(loan_months_id=loan.loan_months_id).all()

        for loan in loans_term:
            # Check if overdue and not yet paid
            if loan.due_date < datetime.now().date() and loan.status != 'Paid':
                if loan.status != 'Overdue':
                    # Calculate remaining balance
                    remaining_balance = loan.loan_amount - loan.paid_amount
                    # Apply penalty to the remaining balance
                    penalty = remaining_balance * 0.03
                    loan.penalty_amount = penalty
                    loan.loan_amount += penalty  # This increases the total due
                    loan.status = 'Overdue'
                db.session.commit()

        total_applications = LoanMonths.query.filter(LoanMonths.status == 'Current', LoanMonths.archived == False).count()

        user = db.session.get(User, session['user_id'])

        return render_template('/superadmin/monitoring_term.html', loans_term=loans_term, total_applications=total_applications, username=user.username)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


#monthly loan route
@app.route('/superadmin/monitoring', endpoint='superadmin_monitoring')
def superadmin_monitoring():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        loans = Loan.query.filter(Loan.archived == False, Loan.status == 'Current').all()
        total_amount = sum(loan.amount for loan in loans)  
        total_applications = len(loans)  

        today = date.today()

        for loan in loans:
            total_paid = db.session.query(db.func.sum(LoanPayment.amount_paid))\
                .filter_by(loan_id=loan.loan_id).scalar() or 0

            overdue_payments = LoanPayment.query.filter(
                LoanPayment.loan_id == loan.loan_id,
                LoanPayment.due_date < today,  
                LoanPayment.amount_paid < LoanPayment.amount_due  
            ).count()

            
            if total_paid >= loan.amount:
                loan.status = "Paid"  
            elif overdue_payments > 0:
                loan.status = "Overdue"  
            else:
                loan.status = "Current"  


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


#paid loans route
@app.route('/superadmin/paid-loans')
def superadmin_paid_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])

        paid_loans = Loan.query.filter_by(status='Paid', archived=False).all()
        total_paid_loans = len(paid_loans)

        return render_template(
            'superadmin/paid_loans.html',  
            username=user.username,
            paid_loans=paid_loans,
            total_paid_loans=total_paid_loans
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#paid Term loan route
@app.route('/superadmin/paid-term-loans', endpoint = 'superadmin_paid_term_loans')
def superadmin_paid_term_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])

       
        
        # Fetch term loans with 'Paid' status
        paid_term_loans = LoanMonths.query.filter_by(status='Paid', archived=False).all()
        for loan in paid_term_loans:
            loan.payment_history = TermPaymentHistory.query.filter_by(loan_months_id=loan.loan_months_id).all()
        total_paid_term_loans = len(paid_term_loans)  # Count paid term loans
        
        return render_template(
            'superadmin/paid_term_loans.html',  # Create the template for displaying paid term loans
            username=user.username,
            paid_term_loans=paid_term_loans,
            total_paid_term_loans=total_paid_term_loans
        )
    
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


#overdue loans route
@app.route('/superadmin/overdue-loans', endpoint = 'superadmin_overdue_loans')
def superadmin_overdue_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])

        # Fetch monthly loans with 'Paid' status
        overdue_loans = Loan.query.filter_by(status='Overdue', archived=False).all()
        total_overdue_loans = len(overdue_loans)

        return render_template(
            'superadmin/overdue_loans.html',  
            username=user.username,
            overdue_loans=overdue_loans,
            total_overdue_loans=total_overdue_loans
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#overdue term route
@app.route('/superadmin/overdue-term-loans', endpoint = 'superadmin_overdue_term_loans')
def superadmin_overdue_term_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])

        overdue_term_loans = LoanMonths.query.filter_by(status = 'Overdue', archived = False).all()
        total_overdue_term_loans = len(overdue_term_loans)

        return render_template('superadmin/overdue_term_loans.html', user = user.username, overdue_term_loans=overdue_term_loans, total_overdue_term_loans=total_overdue_term_loans)
    
    flash("Unauthorized access!" "danger")
    return redirect(url_for('login'))

#activity log route
@app.route('/superadmin/activity-logs')
def superadmin_activity_logs():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/logs.html', username=user.username)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#users management
@app.route('/superadmin/manage-users', endpoint = "superadmin_manage_users")
def superadmin_manage_users():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        users = User.query.all()
        total_users = len(users)
        return render_template('superadmin/manage_users.html', username=user.username, users=users, total_users=total_users)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#add user 
@app.route('/superadmin/add_user', methods=['GET', 'POST'], endpoint = 'add_user')
def add_user():
    if 'role' in session and session['role'] == 'superadmin':
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')

            if not username or not password or not role:
                flash("All fields are required!", "danger")
                return redirect(url_for('add_user'))

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username already exists!", "danger")
                return redirect(url_for('add_user'))

            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()

            flash("User added successfully!", "success")
            return redirect(url_for('superadmin_manage_users'))
        
        user = db.session.get(User, session['user_id'])
        return render_template('superadmin/add_user.html', username=user.username)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#edit user
@app.route('/superadmin/edit_user/<int:user_id>', methods=['GET', 'POST'], endpoint = 'edit_user')
def edit_user(user_id):
    if 'role' in session and session['role'] == 'superadmin':
        user_to_edit = User.query.get_or_404(user_id)

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')

            if not username or not role:
                flash("Username and Role are required!", "danger")
                return redirect(url_for('edit_user', user_id=user_id))

            # Check for username conflict (excluding the current user)
            existing_user = User.query.filter(User.username == username, User.id != user_id).first()
            if existing_user:
                flash("Username already exists!", "danger")
                return redirect(url_for('edit_user', user_id=user_id))

            user_to_edit.username = username
            user_to_edit.role = role

            if password:  # Only update password if provided
                user_to_edit.password = generate_password_hash(password)

            db.session.commit()
            flash("User updated successfully!", "success")
            return redirect(url_for('superadmin_manage_users'))

        current_user = db.session.get(User, session['user_id'])
        return render_template('superadmin/edit_user.html', user=user_to_edit, username=current_user.username)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#delete user
@app.route('/superadmin/delete_user/<int:user_id>', methods=['POST'], endpoint = 'delete_user')
def delete_user(user_id):
    if 'role' in session and session['role'] == 'superadmin':
        user_to_delete = User.query.get_or_404(user_id)

        # Prevent self-deletion
        if user_to_delete.id == session.get('user_id'):
            return jsonify({"success": False, "message": "You cannot delete your own account."})

        db.session.delete(user_to_delete)
        db.session.commit()

        return jsonify({"success": True, "message": "User deleted successfully!"})

    return jsonify({"success": False, "message": "Unauthorized access!"})

#archived monthly loan
@app.route('/superadmin/archived_monthly_loan', endpoint= "archived_monthly_loan")
def archived_monthly_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        archived_loans = Loan.query.filter_by(archived=True).all()
        total_applications = len(archived_loans)
        return render_template('/superadmin/archived_monthly_loan.html', loans=archived_loans, username=user.username, total_applications=total_applications)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#archived term loan
@app.route('/superadmin/archived_term_loan', endpoint = "archived_term_loan")
def archived_term_loans():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        archived_loans = LoanMonths.query.filter_by(archived=True).all()
        total_term_archived= len(archived_loans)
        return render_template('/superadmin/archived_term_loan.html' , archived_loans = archived_loans, username = user.username, total_term_archived=total_term_archived)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#route to add monthly page
@app.route('/add-monthly-loan', endpoint='add_monthly_loan')
def add_monthly_loan():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('add_monthly_loan.html', username=user.username)
    
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#Monthly loan addition
@app.route('/add-loan', methods=['POST'])
def add_loan():
    try:
        lender_name = request.form.get('lender_name')
        amount = request.form.get('amount')
        months_to_pay = request.form.get('months_to_pay')
        application_date_str = request.form.get('application_date')

        if not lender_name or not amount or not months_to_pay or not application_date_str:
            return jsonify({"success": False, "message": "All fields are required."})
        try:
            amount = float(amount)
            months_to_pay = int(months_to_pay)
            if amount <= 0 or months_to_pay <= 0:
                return jsonify({"success": False, "message": "Amount and months to pay must be positive numbers."})
        except ValueError:
            return jsonify({"success": False, "message": "Invalid amount or months to pay."})

        try:
            application_date = datetime.strptime(application_date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})

        monthly_payment = amount / months_to_pay

        new_loan = Loan(
            lender_name=lender_name,
            amount=amount,
            application_date=application_date,
            months_to_pay=months_to_pay,
            monthly_payment=monthly_payment,
            archived=False
        )
        db.session.add(new_loan)
        db.session.flush()  

        
        due_date = application_date
        for _ in range(months_to_pay):
            due_date += relativedelta(months=1)  
            new_payment = LoanPayment(
                loan_id=new_loan.loan_id, 
                due_date=due_date,
                amount_due=monthly_payment,
                status='Current',
            )
            db.session.add(new_payment)

        db.session.commit()

        return jsonify({"success": True, "message": "Loan and payment schedule added successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})
    
#route to add term page
@app.route('/add-term-loan', endpoint='add_term_loan')
def add_term_loan():
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        return render_template('add_term_loan.html', username=user.username)
    
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#add term loan
@app.route('/add_term_loan', methods=['POST'], endpoint = "add_loan_term")
def add_loan_term():
    try:
        lender_name = request.form.get('lender_name')
        loan_amount = request.form.get('amount')
        application_date = request.form.get('application_date')
        months_to_pay = request.form.get('months_to_pay')

        if not lender_name or not loan_amount or not application_date or not months_to_pay:
            return jsonify({"success": False, "message": "All fields are required!"})

        try:
            loan_amount = float(loan_amount)
            months_to_pay = int(months_to_pay)
            if loan_amount <= 0 or months_to_pay <= 0:
                return jsonify({"success": False, "message": "Loan amount and months to pay must be positive values."})
        except ValueError:
            return jsonify({"success": False, "message": "Invalid loan amount or months to pay. Must be numbers."})

        try:
            app_date = datetime.strptime(application_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."})

        due_date = app_date + timedelta(days=30 * months_to_pay)

        new_loan = LoanMonths(
            lender_name=lender_name,
            loan_amount=loan_amount,
            application_date=app_date.date(),
            months_to_pay=months_to_pay,
            due_date=due_date.date(),
            status='Current',
            archived=False
        )

        db.session.add(new_loan)
        db.session.commit()

        return jsonify({"success": True, "message": "Term Loan added successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Failed to add term loan. Error: {str(e)}"})

#monthly loan payment schedule
@app.route('/loan_schedule/<int:loan_id>', endpoint='loan_schedule')
def loan_schedule(loan_id):
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        loan = db.session.get(Loan, loan_id)

        if not loan:
            flash("Loan not found!", "danger")
            return redirect(url_for('superadmin_monitoring'))

        payments = LoanPayment.query.filter_by(loan_id=loan_id).order_by(LoanPayment.due_date).all()

        for payment in payments:
            due_date = payment.due_date  

            if payment.amount_due > 0 and due_date < date.today(): 
                payment.status = "Overdue"
            elif payment.amount_due == 0:  
                payment.status = "Paid"
            else:  
                payment.status = "Current"

        db.session.commit()  

        return render_template(
            'loan_schedule.html',
            username=user.username,
            loan=loan,
            payments=payments
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#route to payment for term
@app.route('/term_loan_payment/<int:loan_months_id>', methods = ['GET'])
def term_payment_page(loan_months_id):
    if 'role' in session and session['role'] == 'superadmin':
        loan = LoanMonths.query.get_or_404(loan_months_id)
        remaining_balance = loan.loan_amount - loan.paid_amount

        return render_template('term_loan_payment.html', loan=loan, remaining_balance=remaining_balance)
    
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#term partial payment
@app.route('/term_loan_payment/<int:loan_months_id>', methods=['POST'])
def process_term_payment(loan_months_id):
    if 'role' in session and session['role'] == 'superadmin':
        loan = LoanMonths.query.get_or_404(loan_months_id)

        remaining_balance = loan.loan_amount - loan.paid_amount

        if request.method == 'POST':
            paid_amount = request.form['paid_amount']
            remarks = request.form.get('remarks', '')  # optional remarks field

            try:
                paid_amount = float(paid_amount)
                
                if paid_amount <= 0:
                    flash("Payment amount must be greater than zero.", "danger")
                    return redirect(url_for('term_payment_page', loan_months_id=loan_months_id))

                if paid_amount > remaining_balance:
                    flash("Payment amount exceeds the remaining balance.", "danger")
                    return redirect(url_for('term_payment_page', loan_months_id=loan_months_id))
                
                loan.paid_amount += paid_amount
                if loan.paid_amount >= loan.loan_amount:
                    loan.status = 'Paid'  

                history = TermPaymentHistory(
                    loan_months_id=loan.loan_months_id,
                    amount=paid_amount,
                    date_paid=datetime.utcnow(),
                    remarks='Partial Pay'
                )
                db.session.add(history)

                db.session.commit()

                flash(f"Payment successfully processed for {loan.lender_name}", "success")
                return redirect(url_for('superadmin_monitoring_terms'))  

            except ValueError:
                flash("Invalid payment amount.", "danger")
                return redirect(url_for('term_payment_page', loan_months_id=loan_months_id))
        
        return render_template('term_loan_payment.html', loan=loan, remaining_balance=remaining_balance)
    
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#term full payment
@app.route('/term_full_payment/<int:loan_months_id>', methods=['POST'])
def term_full_payment(loan_months_id):
    loan = LoanMonths.query.get_or_404(loan_months_id)

    if loan.status == 'Paid':
        return jsonify({"success": False, "message": "This loan is already fully paid!"})

    loan.paid_amount = loan.loan_amount  
    loan.status = 'Paid' 

    
    history = TermPaymentHistory(
        loan_months_id=loan.loan_months_id,
        amount=loan.loan_amount,
        date_paid=datetime.utcnow(),
        remarks="Full payment"
    )
    db.session.add(history)

    db.session.commit() 

    return jsonify({"success": True, "message": "Loan fully paid successfully!"})



@app.route('/monthly_loan_payment/<int:loan_payment_id>', endpoint='monthly_loan_payment')
def partial_payment_page(loan_payment_id):
    if 'role' in session and session['role'] == 'superadmin':
        user = db.session.get(User, session['user_id'])
        loan_payment = db.session.get(LoanPayment, loan_payment_id)

        if not loan_payment:
            flash("Loan payment record not found!", "danger")
            return redirect(url_for('loan_schedule'))

        loan = db.session.get(Loan, loan_payment.loan_id)

        unpaid_previous = LoanPayment.query.filter(
            LoanPayment.loan_id == loan.loan_id,
            LoanPayment.due_date < loan_payment.due_date,
            LoanPayment.amount_due > 0
        ).first()

        block_payment = unpaid_previous is not None  

        return render_template(
            'monthly_loan_payment.html',
            username=user.username,
            loan=loan,
            loan_payment=loan_payment,
            block_payment=block_payment
        )

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))


#partial payment for monthly
@app.route('/partial_payment/<int:loan_payment_id>', methods=['POST'])
def partial_payment(loan_payment_id):
    if 'role' in session and session['role'] == 'superadmin':
        loan_payment = db.session.get(LoanPayment, loan_payment_id)

        if not loan_payment:
            flash("Loan payment record not found!", "danger")
            return redirect(url_for('superadmin_monitoring'))

        amount_paid = request.form.get('amount_paid')

        if not amount_paid:
            flash("Payment amount is required!", "danger")
            return redirect(url_for('monthly_loan_payment', loan_payment_id=loan_payment_id))

        try:
            amount_paid = float(amount_paid)
            if amount_paid <= 0:
                flash("Payment amount must be greater than zero!", "danger")
                return redirect(url_for('monthly_loan_payment', loan_payment_id=loan_payment_id))
        except ValueError:
            flash("Invalid payment amount! Enter a valid number.", "danger")
            return redirect(url_for('monthly_loan_payment', loan_payment_id=loan_payment_id))

        if loan_payment.amount_due == 0:
            flash("Loan is already fully paid!", "danger")
            return redirect(url_for('monthly_loan_payment', loan_payment_id=loan_payment_id))
        
        if amount_paid > loan_payment.amount_due:
            flash("Payment amount exceeds remaining balance!", "danger")
            return redirect(url_for('monthly_loan_payment', loan_payment_id=loan_payment_id))

        loan_payment.amount_due -= amount_paid
        loan_payment.amount_paid += amount_paid

        history = PaymentHistory(
        loan_payment_id=loan_payment_id,
        amount=amount_paid,
        date_paid=date.today(),
        remarks="Partial Payment"
        )
        db.session.add(history)

        if loan_payment.amount_due == 0:
            loan_payment.status = "Paid"
        elif loan_payment.due_date < date.today():
            loan_payment.status = "Overdue"
        else:
            loan_payment.status = "Current"

        loan = db.session.get(Loan, loan_payment.loan_id)
        payments = loan.payments  

        all_paid = all(p.amount_due == 0 for p in payments)
        any_overdue = any(p.amount_due > 0 and p.due_date < date.today() for p in payments)

        if all_paid:
            loan.status = "Paid"
        elif any_overdue:
            loan.status = "Overdue"
        else:
            loan.status = "Current"

        db.session.commit()
        flash("Payment successful!", "success")
        return redirect(url_for('loan_schedule', loan_id=loan_payment.loan_id))

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#Full pay in monthly loan
@app.route('/full_payment/<int:payment_id>', methods=['POST'])
def full_payment(payment_id):
    payment = LoanPayment.query.get(payment_id)
    
    if not payment:
        return jsonify({"success": False, "message": "Payment record not found."})

    unpaid_previous = LoanPayment.query.filter(
        LoanPayment.loan_id == payment.loan_id,
        LoanPayment.due_date < payment.due_date,
        LoanPayment.amount_due > 0
    ).first()

    if unpaid_previous:
        return jsonify({"success": False, "message": "You must complete previous payments before proceeding with this full payment."})

    remaining_balance = payment.amount_due 

    if remaining_balance > 0:
        payment.amount_paid += remaining_balance  
        payment.amount_due = 0 
        payment.status = "Paid"

        history = PaymentHistory(
        loan_payment_id=payment_id,
        amount=remaining_balance,
        date_paid=date.today(),
        remarks="Full Payment"
        )
        db.session.add(history)

        # Update the parent loan's status
        loan = db.session.get(Loan, payment.loan_id)
        payments = loan.payments

        all_paid = all(p.amount_due == 0 for p in payments)
        any_overdue = any(p.amount_due > 0 and p.due_date < date.today() for p in payments)

        if all_paid:
            loan.status = "Paid"
        elif any_overdue:
            loan.status = "Overdue"
        else:
            loan.status = "Current"

        db.session.commit()

        return jsonify({"success": True, "message": "Loan fully paid successfully!"})
    
    return jsonify({"success": False, "message": "This loan is already fully paid!"})


#edit loan for term
@app.route('/edit_term_loan/<int:loan_months_id>', methods=['GET', 'POST'])
def edit_term_loan(loan_months_id):
    loan = LoanMonths.query.get(loan_months_id)

    if not loan:
        flash("Loan not found!", "error")
        return redirect(url_for("superadmin_monitoring_terms"))  

    if request.method == "POST":
        # Get form data
        lender_name = request.form.get("lender_name")
        loan_amount = request.form.get("amount")
        application_date = request.form.get("application_date")
        months_to_pay = request.form.get("months_to_pay")

        # Validate required fields
        if not lender_name or not loan_amount or not application_date or not months_to_pay:
            flash("All fields are required!", "error")
            return redirect(url_for("edit_term_loan", loan_months_id=loan_months_id))

        # Validate loan amount and months to pay
        try:
            loan_amount = float(loan_amount)
            months_to_pay = int(months_to_pay)

            if loan_amount <= 0 or months_to_pay <= 0:
                flash("Loan amount and months to pay must be positive values.", "error")
                return redirect(url_for("edit_term_loan", loan_months_id=loan_months_id))
        except ValueError:
            flash("Invalid loan amount or months to pay. Must be numbers.", "error")
            return redirect(url_for("edit_term_loan", loan_months_id=loan_months_id))

        # Validate application date format
        try:
            app_date = datetime.strptime(application_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "error")
            return redirect(url_for("edit_term_loan", loan_months_id=loan_months_id))

        # Update loan details
        loan.lender_name = lender_name
        loan.loan_amount = loan_amount
        loan.application_date = app_date.date()
        loan.months_to_pay = months_to_pay

        # Recalculate and update the due date
        loan.due_date = app_date + relativedelta(months=months_to_pay)

        # Save changes
        db.session.commit()
        flash("Loan updated successfully!", "success")
        return redirect(url_for("superadmin_monitoring_terms"))

    return render_template("edit_term_loan.html", loan=loan)

#edit loan for monthly
@app.route('/edit_monthly_loan/<int:loan_id>', methods=['GET', 'POST'], endpoint="edit_monthly_loan")
def edit_monthly_loan(loan_id):
    if 'role' in session and session['role'] == 'superadmin':
        loan = db.session.get(Loan, loan_id)
        user = db.session.get(User, session['user_id'])

        if not loan:
            flash("Loan not found!", "danger")
            return redirect(url_for('superadmin_monitoring'))

        if request.method == 'POST':
            try:
                # Get form data
                lender_name = request.form.get('lender_name')
                amount = request.form.get('amount')
                months_to_pay = request.form.get('months_to_pay')
                application_date = request.form.get('application_date')

                # Validate required fields
                if not lender_name or not amount or not months_to_pay or not application_date:
                    flash("All fields are required!", "danger")
                    return redirect(url_for('edit_monthly_loan', loan_id=loan_id))

                # Validate numeric inputs
                try:
                    amount = float(amount)
                    months_to_pay = int(months_to_pay)

                    if amount <= 0 or months_to_pay <= 0:
                        flash("Loan amount and months to pay must be positive values.", "danger")
                        return redirect(url_for('edit_monthly_loan', loan_id=loan_id))
                except ValueError:
                    flash("Invalid amount or months to pay. Must be numbers.", "danger")
                    return redirect(url_for('edit_monthly_loan', loan_id=loan_id))

                # Validate application date format
                try:
                    application_date = datetime.strptime(application_date, "%Y-%m-%d")
                except ValueError:
                    flash("Invalid date format. Use YYYY-MM-DD.", "danger")
                    return redirect(url_for('edit_monthly_loan', loan_id=loan_id))

                # Update loan details
                loan.lender_name = lender_name
                loan.amount = amount
                loan.months_to_pay = months_to_pay
                loan.application_date = application_date
                loan.monthly_payment = amount / months_to_pay

                # Delete existing loan payments
                LoanPayment.query.filter_by(loan_id=loan.loan_id).delete()

                # Generate new loan payment schedule
                due_date = application_date
                for _ in range(months_to_pay):
                    due_date += relativedelta(months=1) 
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

        return render_template('edit_monthly_loan.html', loan=loan, username=user.username)

    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))

#archive term loan
@app.route('/superadmin/archive_term_loan/<int:loan_months_id>', methods=['POST'])
def archive_term_loan(loan_months_id):
    loan = LoanMonths.query.get(loan_months_id)

    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    
    loan.archived= True
    db.session.commit()
    
    return jsonify({"success": True, "message": "Loan archived successfully!"})

#archive monthly loan
@app.route('/superadmin/archive_monthly_loan/<int:loan_id>', methods=['POST'])
def archive_monthly_loan(loan_id):
    loan = Loan.query.get(loan_id)
    
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    
    loan.archived = True 
    db.session.commit()
    
    return jsonify({"success": True, "message": "Loan archived successfully!"})

#unarchive monthly loan
@app.route('/superadmin/unarchive_monthly_loan/<int:loan_id>', methods=['POST'])
def unarchive_monthly_loan(loan_id):
    loan = Loan.query.get(loan_id)
    
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    
    loan.archived = False  
    db.session.commit()
    
    return jsonify({"success": True, "message": "Loan unarchived successfully!"})

#unarchive term loan
@app.route('/superadmin/unarchive_term_loan/<int:loan_months_id>', methods=['POST'])
def unarchive_term_loan(loan_months_id):
    loan = LoanMonths.query.get(loan_months_id)
    
    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404
    
    loan.archived = False  
    db.session.commit()
    
    return jsonify({"success": True, "message": "Loan unarchived successfully!"})

#delete monthly loan
@app.route('/superadmin/delete_monthly_loan/<int:loan_id>', methods=['POST'])
def delete_monthly_loan(loan_id):
    loan = Loan.query.get(loan_id)

    if not loan:
        return jsonify({"success": False, "message": "Loan not found"}), 404

    try:
        loan_payments = LoanPayment.query.filter_by(loan_id=loan_id).all()

        for payment in loan_payments:
            PaymentHistory.query.filter_by(loan_payment_id=payment.loan_payment_id).delete()

        LoanPayment.query.filter_by(loan_id=loan_id).delete()

        db.session.delete(loan)
        db.session.commit()

        return jsonify({"success": True, "message": "Loan deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Failed to delete loan: {str(e)}"}), 500
    
#delete term loan
@app.route('/superadmin/delete_term_loan/<int:loan_id>', methods=['POST'])
def delete_tem_loan(loan_id):
    loan = LoanMonths.query.get_or_404(loan_id)

    try:
        TermPaymentHistory.query.filter_by(loan_months_id=loan.loan_months_id).delete()

        db.session.delete(loan)
        db.session.commit()
        return jsonify({"success": True, "message": "Loan deleted successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error deleting loan."})

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



