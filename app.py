import os
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from models import (
    db, User, Patient, PatientVital, StockItem, Prescription, PrescriptionItem, Bill, BillItem, AccountEntry, PurchaseBill, PurchaseBillItem, SubscriptionPackage, Subscription
)
from database import init_db, check_superadmin_exists

basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'instance')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
db_path = os.path.join(db_dir, 'hms_clinic_supscription.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hms-clinic-super-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'superadmin':
            flash('Access denied. Super Admin privileges required.', 'danger')
            return redirect(url_for('superadmin_login'))
        return f(*args, **kwargs)
    return decorated_function

# First load check: Redirect to /setup if no superadmin exists
@app.before_request
def check_first_run():
    allowed_endpoints = ['setup', 'static', 'login', 'register', 'superadmin_index', 'superadmin_login', 'logout', 'plans_list']
    if request.endpoint and request.endpoint not in allowed_endpoints:
        if not check_superadmin_exists():
            return redirect(url_for('setup'))

# Helper function to generate unique sequential numbers
def generate_code(prefix):
    count = 1
    if prefix == 'PAT':
        count = Patient.query.count() + 1001
        return f"PAT-{count}"
    elif prefix == 'RX':
        count = Prescription.query.count() + 1001
        return f"RX-{count}"
    elif prefix == 'INV':
        count = Bill.query.count() + 1001
        return f"INV-{count}"
    elif prefix == 'PUR':
        count = PurchaseBill.query.count() + 1001
        return f"PUR-{count}"
    elif prefix == 'TXN':
        count = AccountEntry.query.count() + 1001
        return f"TXN-{count}"
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# -------------------------------
# AUTHENTICATION & SETUP ROUTES
# -------------------------------

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if check_superadmin_exists():
        flash('Superadmin account already exists. Please log in.', 'info')
        return redirect(url_for('superadmin_login'))
        
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('setup'))

        superadmin = User(
            username=username,
            email=email,
            full_name=full_name or 'Superadmin',
            role='superadmin',
            is_active_user=True
        )
        superadmin.set_password(password)
        db.session.add(superadmin)
        db.session.commit()

        login_user(superadmin)
        flash('System initialized successfully! Welcome Superadmin.', 'success')
        return redirect(url_for('superadmin_dashboard'))

    return render_template('setup.html')


@app.route('/superadmin', strict_slashes=False)
@app.route('/superadmin/', strict_slashes=False)
def superadmin_index():
    if not check_superadmin_exists():
        return redirect(url_for('setup'))

    if current_user.is_authenticated and current_user.is_superadmin:
        return redirect(url_for('superadmin_dashboard'))
    return redirect(url_for('superadmin_login'))


@app.route('/superadmin/login', methods=['GET', 'POST'], strict_slashes=False)
def superadmin_login():

    if not check_superadmin_exists():
        return redirect(url_for('setup'))

    if current_user.is_authenticated:
        if current_user.is_superadmin:
            return redirect(url_for('superadmin_dashboard'))
        else:
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter((User.username == username_input) | (User.email == username_input)).first()
        if user and user.check_password(password):
            if user.role != 'superadmin':
                flash('Access denied. This portal is strictly for Super Admin accounts.', 'danger')
                return redirect(url_for('superadmin_login'))

            login_user(user)
            flash(f'Super Admin Logged In: Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('superadmin_dashboard'))
        else:
            flash('Invalid Super Admin username/email or password.', 'danger')

    return render_template('superadmin/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('plans_list'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        client_user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role='clinic_admin',
            is_active_user=True
        )
        client_user.set_password(password)
        db.session.add(client_user)
        db.session.commit()

        login_user(client_user)
        flash(f'Account created successfully, {client_user.full_name}! Please select your subscription plan below.', 'success')
        return redirect(url_for('plans_list'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if not check_superadmin_exists():
        return redirect(url_for('setup'))

    if current_user.is_authenticated:
        if current_user.is_superadmin:
            return redirect(url_for('superadmin_dashboard'))
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username_input = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter((User.username == username_input) | (User.email == username_input)).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            if user.is_superadmin:
                return redirect(url_for('superadmin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# -------------------------------
# DASHBOARD ROUTE
# -------------------------------

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    total_patients = Patient.query.count()
    total_prescriptions = Prescription.query.count()
    total_bills = Bill.query.count()
    
    # Financial metrics
    total_revenue = db.session.query(db.func.sum(Bill.paid_amount)).scalar() or 0.0
    total_income = db.session.query(db.func.sum(AccountEntry.amount)).filter(AccountEntry.entry_type == 'Income').scalar() or 0.0
    total_expenses = db.session.query(db.func.sum(AccountEntry.amount)).filter(AccountEntry.entry_type == 'Expense').scalar() or 0.0
    net_profit = total_income - total_expenses

    # Low stock alerts
    stock_items = StockItem.query.all()
    low_stock_items = [s for s in stock_items if s.is_low_stock]
    low_stock_count = len(low_stock_items)

    # Recent Records
    recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(5).all()
    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_patients=total_patients,
        total_prescriptions=total_prescriptions,
        total_bills=total_bills,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=net_profit,
        low_stock_count=low_stock_count,
        low_stock_items=low_stock_items[:5],
        recent_patients=recent_patients,
        recent_bills=recent_bills
    )

# -------------------------------
# PATIENT MANAGEMENT ROUTES
# -------------------------------

@app.route('/patients')
@login_required
def patients_list():
    search_query = request.args.get('search', '').strip()
    query = Patient.query
    if search_query:
        query = query.filter(
            (Patient.name.ilike(f'%{search_query}%')) |
            (Patient.phone.ilike(f'%{search_query}%')) |
            (Patient.patient_code.ilike(f'%{search_query}%'))
        )
    patients = query.order_by(Patient.created_at.desc()).all()
    return render_template('patients/list.html', patients=patients, search_query=search_query)


@app.route('/patients/create', methods=['GET', 'POST'])
@login_required
def patients_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = int(request.form.get('age', 0))
        gender = request.form.get('gender', 'Male')
        blood_group = request.form.get('blood_group', '')
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        emergency_contact = request.form.get('emergency_contact', '').strip()
        medical_history = request.form.get('medical_history', '').strip()

        patient_code = generate_code('PAT')

        patient = Patient(
            patient_code=patient_code,
            name=name,
            age=age,
            gender=gender,
            blood_group=blood_group,
            phone=phone,
            email=email,
            address=address,
            emergency_contact=emergency_contact,
            medical_history=medical_history
        )
        db.session.add(patient)
        db.session.commit()
        flash(f'Patient {name} registered successfully with Code {patient_code}!', 'success')
        return redirect(url_for('patients_list'))

    return render_template('patients/form.html', patient=None)


@app.route('/patients/<int:patient_id>')
@login_required
def patients_view(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template('patients/view.html', patient=patient)


@app.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
def patients_edit(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form.get('name', '').strip()
        patient.age = int(request.form.get('age', 0))
        patient.gender = request.form.get('gender', 'Male')
        patient.blood_group = request.form.get('blood_group', '')
        patient.phone = request.form.get('phone', '').strip()
        patient.email = request.form.get('email', '').strip()
        patient.address = request.form.get('address', '').strip()
        patient.emergency_contact = request.form.get('emergency_contact', '').strip()
        patient.medical_history = request.form.get('medical_history', '').strip()

        db.session.commit()
        flash(f'Patient profile for {patient.name} updated.', 'success')
        return redirect(url_for('patients_view', patient_id=patient.id))

    return render_template('patients/form.html', patient=patient)


@app.route('/patients/<int:patient_id>/delete', methods=['POST'])
@login_required
def patients_delete(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    name = patient.name
    db.session.delete(patient)
    db.session.commit()
    flash(f'Patient record for {name} deleted.', 'info')
    return redirect(url_for('patients_list'))


@app.route('/patients/<int:patient_id>/vitals', methods=['GET', 'POST'])
@login_required
def patients_vitals(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        bp = request.form.get('bp', '').strip()
        pulse = request.form.get('pulse', '').strip()
        temp = request.form.get('temp', '').strip()
        weight = request.form.get('weight', '').strip()
        spo2 = request.form.get('spo2', '').strip()
        nurse_name = request.form.get('nurse_name', '').strip()
        notes = request.form.get('notes', '').strip()

        vital = PatientVital(
            patient_id=patient.id,
            bp=bp,
            pulse=pulse,
            temp=temp,
            weight=weight,
            spo2=spo2,
            nurse_name=nurse_name,
            notes=notes,
            recorded_at=datetime.utcnow()
        )
        db.session.add(vital)
        db.session.commit()
        flash(f'Nurse Vitals check recorded for patient {patient.name}!', 'success')
        return redirect(url_for('patients_list'))

    latest_vitals = PatientVital.query.filter_by(patient_id=patient.id).order_by(PatientVital.recorded_at.desc()).first()
    return render_template('patients/vitals.html', patient=patient, latest_vitals=latest_vitals)


@app.route('/api/patients/<int:patient_id>/latest-vitals')
@login_required
def api_latest_vitals(patient_id):
    vital = PatientVital.query.filter_by(patient_id=patient_id).order_by(PatientVital.recorded_at.desc()).first()
    if vital:
        return jsonify({
            'found': True,
            'bp': vital.bp or '',
            'pulse': vital.pulse or '',
            'temp': vital.temp or '',
            'weight': vital.weight or '',
            'spo2': vital.spo2 or '',
            'nurse_name': vital.nurse_name or 'Nurse',
            'notes': vital.notes or '',
            'recorded_at': vital.recorded_at.strftime('%B %d, %Y %I:%M %p')
        })
    return jsonify({'found': False})

# -------------------------------
# E-PRESCRIPTION MANAGEMENT ROUTES
# -------------------------------

@app.route('/prescriptions')
@login_required
def prescriptions_list():
    prescriptions = Prescription.query.order_by(Prescription.created_at.desc()).all()
    return render_template('prescriptions/list.html', prescriptions=prescriptions)


@app.route('/prescriptions/create', methods=['GET', 'POST'])
@login_required
def prescription_create():
    if request.method == 'POST':
        patient_id = int(request.form.get('patient_id', 0))
        doctor_name = request.form.get('doctor_name', '').strip()
        diagnosis = request.form.get('diagnosis', '').strip()
        vitals_bp = request.form.get('vitals_bp', '').strip()
        vitals_pulse = request.form.get('vitals_pulse', '').strip()
        vitals_temp = request.form.get('vitals_temp', '').strip()
        vitals_weight = request.form.get('vitals_weight', '').strip()
        advice = request.form.get('advice', '').strip()

        prescription_no = generate_code('RX')

        rx = Prescription(
            prescription_no=prescription_no,
            patient_id=patient_id,
            doctor_name=doctor_name,
            diagnosis=diagnosis,
            vitals_bp=vitals_bp,
            vitals_pulse=vitals_pulse,
            vitals_temp=vitals_temp,
            vitals_weight=vitals_weight,
            advice=advice,
            status='Active'
        )
        db.session.add(rx)
        db.session.commit()

        # Save medicine items
        med_names = request.form.getlist('medicine_name[]')
        units = request.form.getlist('unit[]')
        dosages = request.form.getlist('dosage[]')
        durations = request.form.getlist('duration[]')
        qtys = request.form.getlist('qty[]')
        foods = request.form.getlist('food[]')
        stock_ids = request.form.getlist('medicine_id[]')

        for i in range(len(med_names)):
            if med_names[i].strip():
                stock_id = int(stock_ids[i]) if i < len(stock_ids) and stock_ids[i].isdigit() else None
                rx_unit = units[i] if i < len(units) else 'Tablet'
                rx_dosage = dosages[i].strip() if i < len(dosages) else ''
                rx_duration = durations[i].strip() if i < len(durations) else ''
                rx_qty = int(qtys[i]) if i < len(qtys) and qtys[i].isdigit() else 1
                rx_food = foods[i] if i < len(foods) else 'After Food'

                rx_item = PrescriptionItem(
                    prescription_id=rx.id,
                    medicine_id=stock_id,
                    medicine_name=med_names[i].strip(),
                    unit=rx_unit,
                    dosage=rx_dosage,
                    frequency=rx_dosage,
                    duration=rx_duration,
                    qty=rx_qty,
                    food=rx_food,
                    instructions=rx_food
                )
                db.session.add(rx_item)

        db.session.commit()
        flash(f'E-Prescription {prescription_no} generated successfully!', 'success')
        return redirect(url_for('prescriptions_print', rx_id=rx.id))

    patient_id_arg = request.args.get('patient_id', type=int)
    initial_vitals = None
    if patient_id_arg:
        initial_vitals = PatientVital.query.filter_by(patient_id=patient_id_arg).order_by(PatientVital.recorded_at.desc()).first()

    patients = Patient.query.order_by(Patient.name).all()
    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    stock_items_json = [{'id': s.id, 'name': s.item_name, 'category': s.category or 'Tablet', 'qty': s.quantity} for s in stock_items]

    return render_template(
        'prescriptions/create.html',
        patients=patients,
        stock_items=stock_items,
        stock_items_json=stock_items_json,
        selected_patient_id=patient_id_arg,
        initial_vitals=initial_vitals
    )


@app.route('/prescriptions/<int:rx_id>/print')
@login_required
def prescriptions_print(rx_id):
    prescription = Prescription.query.get_or_404(rx_id)
    return render_template('prescriptions/view.html', prescription=prescription)

# -------------------------------
# STOCK MANAGEMENT ROUTES
# -------------------------------

@app.route('/stock')
@login_required
def stock_list():
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    query = StockItem.query
    if search_query:
        query = query.filter((StockItem.item_name.ilike(f'%{search_query}%')) | (StockItem.batch_number.ilike(f'%{search_query}%')))
    if category_filter:
        query = query.filter(StockItem.category == category_filter)

    items = query.order_by(StockItem.item_name).all()
    return render_template('stock/list.html', items=items, search_query=search_query, selected_category=category_filter)


@app.route('/stock/create', methods=['GET', 'POST'])
@login_required
def stock_create():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', 'Tablet')
        batch_number = request.form.get('batch_number', '').strip()
        supplier_name = request.form.get('supplier_name', '').strip()
        cost_price = float(request.form.get('cost_price', 0.0))
        selling_price = float(request.form.get('selling_price', 0.0))
        quantity = int(request.form.get('quantity', 0))
        
        tablets_per_strip = int(request.form.get('tablets_per_strip', 1) or 1)
        strip_quantity = int(request.form.get('strip_quantity', 0) or 0)
        strip_price = float(request.form.get('strip_price', 0.0) or 0.0)

        min_reorder_level = int(request.form.get('min_reorder_level', 10))
        expiry_str = request.form.get('expiry_date', '').strip()
        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None

        item = StockItem(
            item_name=item_name,
            category=category,
            batch_number=batch_number,
            supplier_name=supplier_name,
            cost_price=cost_price,
            selling_price=selling_price,
            quantity=quantity,
            tablets_per_strip=tablets_per_strip,
            strip_quantity=strip_quantity,
            strip_price=strip_price,
            min_reorder_level=min_reorder_level,
            expiry_date=expiry_date
        )
        db.session.add(item)
        db.session.commit()
        flash(f'Stock item "{item_name}" added to inventory.', 'success')
        return redirect(url_for('stock_list'))

    return render_template('stock/form.html', item=None)


@app.route('/stock/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def stock_edit(item_id):
    item = StockItem.query.get_or_404(item_id)
    if request.method == 'POST':
        item.item_name = request.form.get('item_name', '').strip()
        item.category = request.form.get('category', 'Tablet')
        item.batch_number = request.form.get('batch_number', '').strip()
        item.supplier_name = request.form.get('supplier_name', '').strip()
        item.cost_price = float(request.form.get('cost_price', 0.0))
        item.selling_price = float(request.form.get('selling_price', 0.0))
        item.quantity = int(request.form.get('quantity', 0))
        
        item.tablets_per_strip = int(request.form.get('tablets_per_strip', 1) or 1)
        item.strip_quantity = int(request.form.get('strip_quantity', 0) or 0)
        item.strip_price = float(request.form.get('strip_price', 0.0) or 0.0)

        item.min_reorder_level = int(request.form.get('min_reorder_level', 10))
        expiry_str = request.form.get('expiry_date', '').strip()
        item.expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d').date() if expiry_str else None

        db.session.commit()
        flash(f'Stock item "{item.item_name}" updated.', 'success')
        return redirect(url_for('stock_list'))

    return render_template('stock/form.html', item=item)


@app.route('/stock/<int:item_id>/delete', methods=['POST'])
@login_required
def stock_delete(item_id):
    item = StockItem.query.get_or_404(item_id)
    name = item.item_name
    db.session.delete(item)
    db.session.commit()
    flash(f'Item "{name}" removed from stock inventory.', 'info')
    return redirect(url_for('stock_list'))

# -------------------------------
# SUPPLIER PURCHASES & STOCK INWARD
# -------------------------------

@app.route('/purchases')
@login_required
def purchases_list():
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = PurchaseBill.query
    if search_query:
        query = query.filter((PurchaseBill.purchase_no.ilike(f'%{search_query}%')) | (PurchaseBill.supplier_name.ilike(f'%{search_query}%')) | (PurchaseBill.supplier_invoice_no.ilike(f'%{search_query}%')))
    if status_filter:
        query = query.filter(PurchaseBill.payment_status == status_filter)

    purchases = query.order_by(PurchaseBill.created_at.desc()).all()
    return render_template('purchases/list.html', purchases=purchases, search_query=search_query, selected_status=status_filter)


@app.route('/purchases/create', methods=['GET', 'POST'])
@login_required
def purchases_create():
    if request.method == 'POST':
        supplier_name = request.form.get('supplier_name', '').strip()
        supplier_invoice_no = request.form.get('supplier_invoice_no', '').strip()
        date_str = request.form.get('purchase_date', '').strip()
        purchase_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()

        total_amount = float(request.form.get('total_amount', 0.0))
        payment_status = request.form.get('payment_status', 'Paid')
        payment_method = request.form.get('payment_method', 'Bank Transfer')
        notes = request.form.get('notes', '').strip()

        paid_amount = total_amount if payment_status == 'Paid' else (total_amount / 2.0 if payment_status == 'Partial' else 0.0)

        purchase_no = generate_code('PUR')

        purchase = PurchaseBill(
            purchase_no=purchase_no,
            supplier_name=supplier_name,
            supplier_invoice_no=supplier_invoice_no,
            total_amount=total_amount,
            paid_amount=paid_amount,
            payment_status=payment_status,
            payment_method=payment_method,
            purchase_date=purchase_date,
            notes=notes
        )
        db.session.add(purchase)
        db.session.commit()

        # Process Line Items & Update/Add Stock
        stock_ids = request.form.getlist('stock_id[]')
        item_names = request.form.getlist('item_name[]')
        categories = request.form.getlist('category[]')
        batch_numbers = request.form.getlist('batch_number[]')
        strips_list = request.form.getlist('strip_quantity[]')
        tabs_per_strip_list = request.form.getlist('tablets_per_strip[]')
        quantities = request.form.getlist('quantity[]')
        cost_prices = request.form.getlist('cost_price[]')
        selling_prices = request.form.getlist('selling_price[]')
        expiry_dates = request.form.getlist('expiry_date[]')

        for i in range(len(item_names)):
            if item_names[i].strip():
                stk_id = int(stock_ids[i]) if i < len(stock_ids) and stock_ids[i].isdigit() else None
                cat = categories[i] if i < len(categories) else 'Tablet'
                batch = batch_numbers[i].strip() if i < len(batch_numbers) else ''
                strips = int(strips_list[i]) if i < len(strips_list) and strips_list[i].isdigit() else 0
                tabs_per_strip = int(tabs_per_strip_list[i]) if i < len(tabs_per_strip_list) and tabs_per_strip_list[i].isdigit() else 1
                qty = int(quantities[i]) if i < len(quantities) and quantities[i].isdigit() else (strips * tabs_per_strip)
                cost = float(cost_prices[i]) if i < len(cost_prices) and cost_prices[i] else 0.0
                sell = float(selling_prices[i]) if i < len(selling_prices) and selling_prices[i] else 0.0
                exp_str = expiry_dates[i].strip() if i < len(expiry_dates) else ''
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date() if exp_str else None

                item_total_cost = cost * qty

                pur_item = PurchaseBillItem(
                    purchase_bill_id=purchase.id,
                    stock_id=stk_id,
                    item_name=item_names[i].strip(),
                    category=cat,
                    batch_number=batch,
                    tablets_per_strip=tabs_per_strip,
                    strip_quantity=strips,
                    quantity=qty,
                    cost_price=cost,
                    selling_price=sell,
                    total_cost=item_total_cost,
                    expiry_date=exp_date
                )
                db.session.add(pur_item)

                # INWARD STOCK UPDATE / CREATION LOGIC
                if stk_id:
                    stk = StockItem.query.get(stk_id)
                    if stk:
                        stk.quantity += qty # AUTO INWARD INCREMENT
                        stk.cost_price = cost
                        stk.selling_price = sell
                        if batch: stk.batch_number = batch
                        if exp_date: stk.expiry_date = exp_date
                        if supplier_name: stk.supplier_name = supplier_name
                        if tabs_per_strip > 1: stk.tablets_per_strip = tabs_per_strip
                else:
                    # Check if matching item exists by name
                    existing_stk = StockItem.query.filter_by(item_name=item_names[i].strip()).first()
                    if existing_stk:
                        existing_stk.quantity += qty # AUTO INWARD INCREMENT
                        existing_stk.cost_price = cost
                        existing_stk.selling_price = sell
                        if batch: existing_stk.batch_number = batch
                        if exp_date: existing_stk.expiry_date = exp_date
                        if supplier_name: existing_stk.supplier_name = supplier_name
                        pur_item.stock_id = existing_stk.id
                    else:
                        new_stk = StockItem(
                            item_name=item_names[i].strip(),
                            category=cat,
                            batch_number=batch,
                            supplier_name=supplier_name,
                            cost_price=cost,
                            selling_price=sell,
                            quantity=qty,
                            tablets_per_strip=tabs_per_strip,
                            strip_quantity=strips,
                            min_reorder_level=20,
                            expiry_date=exp_date
                        )
                        db.session.add(new_stk)
                        db.session.flush()
                        pur_item.stock_id = new_stk.id

        # AUTO LOG EXPENSE IN FINANCIAL LEDGER
        if paid_amount > 0:
            ledger_entry = AccountEntry(
                transaction_no=generate_code('TXN'),
                entry_type='Expense',
                category='Medicine Purchase',
                amount=paid_amount,
                reference_no=purchase_no,
                description=f'Supplier Purchase Bill from {supplier_name} ({supplier_invoice_no or purchase_no})',
                payment_method=payment_method,
                date=purchase_date
            )
            db.session.add(ledger_entry)

        db.session.commit()
        flash(f'Supplier Purchase Bill {purchase_no} recorded and Stock Inventory updated!', 'success')
        return redirect(url_for('purchases_print', purchase_id=purchase.id))

    stock_items = StockItem.query.order_by(StockItem.item_name).all()
    return render_template('purchases/create.html', stock_items=stock_items, today_date=date.today().strftime('%Y-%m-%d'))


@app.route('/purchases/<int:purchase_id>/print')
@login_required
def purchases_print(purchase_id):
    purchase = PurchaseBill.query.get_or_404(purchase_id)
    return render_template('purchases/view.html', purchase=purchase)


@app.route('/purchases/<int:purchase_id>/delete', methods=['POST'])
@login_required
def purchases_delete(purchase_id):
    purchase = PurchaseBill.query.get_or_404(purchase_id)
    pur_no = purchase.purchase_no
    db.session.delete(purchase)
    db.session.commit()
    flash(f'Purchase bill {pur_no} deleted.', 'info')
    return redirect(url_for('purchases_list'))

# -------------------------------
# MEDICAL BILLING MANAGEMENT ROUTES
# -------------------------------

@app.route('/billing')
@login_required
def billing_list():
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Bill.query
    if search_query:
        query = query.filter((Bill.bill_no.ilike(f'%{search_query}%')) | (Bill.patient_name.ilike(f'%{search_query}%')))
    if status_filter:
        query = query.filter(Bill.payment_status == status_filter)

    bills = query.order_by(Bill.created_at.desc()).all()
    return render_template('billing/list.html', bills=bills, search_query=search_query, selected_status=status_filter)


@app.route('/billing/create', methods=['GET', 'POST'])
@login_required
def billing_create():
    if request.method == 'POST':
        patient_id_val = request.form.get('patient_id', '').strip()
        patient_id = int(patient_id_val) if patient_id_val.isdigit() else None
        prescription_id_val = request.form.get('prescription_id', '').strip()
        prescription_id = int(prescription_id_val) if prescription_id_val.isdigit() else None

        patient_name = request.form.get('patient_name', '').strip()
        patient_phone = request.form.get('patient_phone', '').strip()
        doctor_name = request.form.get('doctor_name', '').strip()

        subtotal = float(request.form.get('subtotal', 0.0))
        discount_percent = float(request.form.get('discount_percent', 0.0))
        discount_amount = float(request.form.get('discount_amount', 0.0))
        tax_percent = float(request.form.get('tax_percent', 0.0))
        tax_amount = float(request.form.get('tax_amount', 0.0))
        total_amount = float(request.form.get('total_amount', 0.0))

        payment_status = request.form.get('payment_status', 'Paid')
        payment_method = request.form.get('payment_method', 'Cash')
        notes = request.form.get('notes', '').strip()

        paid_amount = total_amount if payment_status == 'Paid' else (total_amount / 2.0 if payment_status == 'Partial' else 0.0)

        bill_no = generate_code('INV')

        bill = Bill(
            bill_no=bill_no,
            patient_id=patient_id,
            prescription_id=prescription_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            doctor_name=doctor_name,
            subtotal=subtotal,
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            tax_percent=tax_percent,
            tax_amount=tax_amount,
            total_amount=total_amount,
            paid_amount=paid_amount,
            payment_status=payment_status,
            payment_method=payment_method,
            notes=notes
        )
        db.session.add(bill)
        db.session.commit()

        # Save Line Items & Deduct Stock
        stock_ids = request.form.getlist('stock_id[]')
        item_names = request.form.getlist('item_name[]')
        item_types = request.form.getlist('item_type[]')
        prices = request.form.getlist('unit_price[]')
        quantities = request.form.getlist('quantity[]')

        for i in range(len(item_names)):
            if item_names[i].strip():
                stk_id = int(stock_ids[i]) if i < len(stock_ids) and stock_ids[i].isdigit() else None
                u_price = float(prices[i]) if i < len(prices) else 0.0
                qty = int(quantities[i]) if i < len(quantities) else 1
                row_total = u_price * qty

                b_item = BillItem(
                    bill_id=bill.id,
                    stock_id=stk_id,
                    item_name=item_names[i].strip(),
                    item_type=item_types[i] if i < len(item_types) else 'Medicine',
                    unit_price=u_price,
                    quantity=qty,
                    total_price=row_total
                )
                db.session.add(b_item)

                # Inventory Auto-Deduction
                if stk_id:
                    stk = StockItem.query.get(stk_id)
                    if stk:
                        stk.quantity = max(0, stk.quantity - qty)

        # Sync Paid Amount into Financial Ledger (Income)
        if paid_amount > 0:
            ledger_entry = AccountEntry(
                transaction_no=generate_code('TXN'),
                entry_type='Income',
                category='Medical Billing Revenue',
                amount=paid_amount,
                reference_no=bill_no,
                bill_id=bill.id,
                description=f'Revenue from Bill {bill_no} ({patient_name})',
                payment_method=payment_method,
                date=date.today()
            )
            db.session.add(ledger_entry)

        # Update prescription status if converted
        if prescription_id:
            rx = Prescription.query.get(prescription_id)
            if rx:
                rx.status = 'Billed'

        db.session.commit()
        flash(f'Invoice {bill_no} generated successfully!', 'success')
        return redirect(url_for('billing_print', bill_id=bill.id))

    patient_id_arg = request.args.get('patient_id', type=int)
    rx_id_arg = request.args.get('prescription_id', type=int)

    selected_patient = Patient.query.get(patient_id_arg) if patient_id_arg else None
    prescription = Prescription.query.get(rx_id_arg) if rx_id_arg else None

    patients = Patient.query.order_by(Patient.name).all()
    stock_items = StockItem.query.order_by(StockItem.item_name).all()

    # If converted from prescription, pre-populate items
    initial_items = []
    if prescription:
        for rx_item in prescription.items:
            # find price from stock if matched
            stk_price = 10.0
            if rx_item.stock_item:
                stk_price = rx_item.stock_item.selling_price
            initial_items.append({
                'stock_id': rx_item.medicine_id,
                'name': rx_item.medicine_name,
                'price': stk_price,
                'qty': rx_item.qty if rx_item.qty else 1
            })

    return render_template(
        'billing/create.html',
        patients=patients,
        stock_items=stock_items,
        selected_patient=selected_patient,
        prescription=prescription,
        initial_items=initial_items
    )


@app.route('/billing/<int:bill_id>/print')
@login_required
def billing_print(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    return render_template('billing/invoice.html', bill=bill)


@app.route('/billing/<int:bill_id>/delete', methods=['POST'])
@login_required
def billing_delete(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    bill_no = bill.bill_no
    db.session.delete(bill)
    db.session.commit()
    flash(f'Invoice {bill_no} deleted.', 'info')
    return redirect(url_for('billing_list'))

# -------------------------------
# ACCOUNT MANAGEMENT ROUTES
# -------------------------------

@app.route('/accounts')
@login_required
def accounts_list():
    search_query = request.args.get('search', '').strip()
    type_filter = request.args.get('type', '').strip()

    query = AccountEntry.query
    if search_query:
        query = query.filter((AccountEntry.transaction_no.ilike(f'%{search_query}%')) | (AccountEntry.category.ilike(f'%{search_query}%')))
    if type_filter:
        query = query.filter(AccountEntry.entry_type == type_filter)

    entries = query.order_by(AccountEntry.created_at.desc()).all()
    return render_template('accounts/list.html', entries=entries, search_query=search_query, selected_type=type_filter)


@app.route('/accounts/create', methods=['GET', 'POST'])
@login_required
def accounts_create():
    if request.method == 'POST':
        entry_type = request.form.get('entry_type', 'Expense')
        category = request.form.get('category', 'Other')
        amount = float(request.form.get('amount', 0.0))
        reference_no = request.form.get('reference_no', '').strip()
        description = request.form.get('description', '').strip()
        payment_method = request.form.get('payment_method', 'Cash')
        date_str = request.form.get('date', '').strip()
        txn_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()

        transaction_no = generate_code('TXN')

        entry = AccountEntry(
            transaction_no=transaction_no,
            entry_type=entry_type,
            category=category,
            amount=amount,
            reference_no=reference_no,
            description=description,
            payment_method=payment_method,
            date=txn_date
        )
        db.session.add(entry)
        db.session.commit()
        flash(f'Financial ledger transaction {transaction_no} logged.', 'success')
        return redirect(url_for('accounts_list'))

    return render_template('accounts/form.html', today_date=date.today().strftime('%Y-%m-%d'))


@app.route('/accounts/<int:entry_id>/delete', methods=['POST'])
@login_required
def accounts_delete(entry_id):
    entry = AccountEntry.query.get_or_404(entry_id)
    txn_no = entry.transaction_no
    db.session.delete(entry)
    db.session.commit()
    flash(f'Ledger transaction {txn_no} deleted.', 'info')
    return redirect(url_for('accounts_list'))


@app.route('/accounts/summary')
@login_required
def accounts_summary():
    total_income = db.session.query(db.func.sum(AccountEntry.amount)).filter(AccountEntry.entry_type == 'Income').scalar() or 0.0
    total_expenses = db.session.query(db.func.sum(AccountEntry.amount)).filter(AccountEntry.entry_type == 'Expense').scalar() or 0.0
    net_profit = total_income - total_expenses

    # Income Category Breakdown
    income_rows = db.session.query(AccountEntry.category, db.func.sum(AccountEntry.amount))\
        .filter(AccountEntry.entry_type == 'Income')\
        .group_by(AccountEntry.category).all()
    income_categories = {r[0]: r[1] for r in income_rows}

    # Expense Category Breakdown
    expense_rows = db.session.query(AccountEntry.category, db.func.sum(AccountEntry.amount))\
        .filter(AccountEntry.entry_type == 'Expense')\
        .group_by(AccountEntry.category).all()
    expense_categories = {r[0]: r[1] for r in expense_rows}

    return render_template(
        'accounts/summary.html',
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
        income_categories=income_categories,
        expense_categories=expense_categories
    )

# =========================================================================
# SUPER ADMIN PANEL & SUBSCRIPTION MANAGEMENT ROUTES
# =========================================================================

@app.route('/superadmin/dashboard')
@login_required
@superadmin_required
def superadmin_dashboard():
    total_packages = SubscriptionPackage.query.count()
    total_subscriptions = Subscription.query.count()
    pending_subscriptions = Subscription.query.filter_by(status='Pending').count()
    active_subscriptions = Subscription.query.filter_by(status='Approved').count()
    
    # SaaS Revenue metric
    approved_subs = Subscription.query.filter_by(status='Approved').all()
    total_saas_revenue = sum([sub.package.price for sub in approved_subs if sub.package])
    
    recent_requests = Subscription.query.order_by(Subscription.created_at.desc()).limit(10).all()
    recent_packages = SubscriptionPackage.query.order_by(SubscriptionPackage.created_at.desc()).limit(5).all()

    return render_template(
        'superadmin/dashboard.html',
        total_packages=total_packages,
        total_subscriptions=total_subscriptions,
        pending_subscriptions=pending_subscriptions,
        active_subscriptions=active_subscriptions,
        total_saas_revenue=total_saas_revenue,
        recent_requests=recent_requests,
        recent_packages=recent_packages
    )


@app.route('/superadmin/packages')
@login_required
@superadmin_required
def superadmin_packages():
    packages = SubscriptionPackage.query.order_by(SubscriptionPackage.created_at.desc()).all()
    return render_template('superadmin/packages.html', packages=packages)


@app.route('/superadmin/packages/create', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_package_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        billing_cycle = request.form.get('billing_cycle', 'Monthly')
        price = float(request.form.get('price', 0.0))
        duration_days = int(request.form.get('duration_days', 30))
        description = request.form.get('description', '').strip()
        features = request.form.get('features', '').strip()
        is_active = True if request.form.get('is_active') == 'on' else False

        if not name:
            flash('Package name is required.', 'danger')
            return redirect(url_for('superadmin_package_create'))

        package = SubscriptionPackage(
            name=name,
            billing_cycle=billing_cycle,
            price=price,
            duration_days=duration_days,
            description=description,
            features=features,
            is_active=is_active
        )
        db.session.add(package)
        db.session.commit()
        flash(f'Subscription package "{name}" created successfully!', 'success')
        return redirect(url_for('superadmin_packages'))

    return render_template('superadmin/package_form.html', package=None)


@app.route('/superadmin/packages/<int:package_id>/edit', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_package_edit(package_id):
    package = SubscriptionPackage.query.get_or_404(package_id)
    if request.method == 'POST':
        package.name = request.form.get('name', '').strip()
        package.billing_cycle = request.form.get('billing_cycle', 'Monthly')
        package.price = float(request.form.get('price', 0.0))
        package.duration_days = int(request.form.get('duration_days', 30))
        package.description = request.form.get('description', '').strip()
        package.features = request.form.get('features', '').strip()
        package.is_active = True if request.form.get('is_active') == 'on' else False

        db.session.commit()
        flash(f'Package "{package.name}" updated successfully.', 'success')
        return redirect(url_for('superadmin_packages'))

    return render_template('superadmin/package_form.html', package=package)


@app.route('/superadmin/packages/<int:package_id>/toggle-status', methods=['POST'])
@login_required
@superadmin_required
def superadmin_package_toggle_status(package_id):
    package = SubscriptionPackage.query.get_or_404(package_id)
    package.is_active = not package.is_active
    db.session.commit()
    status_str = "activated" if package.is_active else "deactivated"
    flash(f'Package "{package.name}" has been {status_str}.', 'info')
    return redirect(url_for('superadmin_packages'))


@app.route('/superadmin/packages/<int:package_id>/delete', methods=['POST'])
@login_required
@superadmin_required
def superadmin_package_delete(package_id):
    package = SubscriptionPackage.query.get_or_404(package_id)
    name = package.name
    db.session.delete(package)
    db.session.commit()
    flash(f'Subscription package "{name}" deleted.', 'info')
    return redirect(url_for('superadmin_packages'))


@app.route('/superadmin/subscriptions')
@login_required
@superadmin_required
def superadmin_subscriptions():
    status_filter = request.args.get('status', 'all').strip()
    query = Subscription.query
    if status_filter != 'all':
        query = query.filter(Subscription.status == status_filter.capitalize())

    subscriptions = query.order_by(Subscription.created_at.desc()).all()
    return render_template('superadmin/subscriptions.html', subscriptions=subscriptions, status_filter=status_filter)


@app.route('/superadmin/subscriptions/<int:sub_id>/approve', methods=['POST'])
@login_required
@superadmin_required
def superadmin_subscription_approve(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    sub.status = 'Approved'
    sub.start_date = datetime.utcnow()
    days_to_add = sub.package.duration_days if sub.package else 30
    sub.end_date = datetime.utcnow() + timedelta(days=days_to_add)
    db.session.commit()

    flash(f'Subscription for "{sub.clinic_name}" approved! Active until {sub.end_date.strftime("%Y-%m-%d")}.', 'success')
    return redirect(url_for('superadmin_subscriptions'))


@app.route('/superadmin/subscriptions/<int:sub_id>/reject', methods=['POST'])
@login_required
@superadmin_required
def superadmin_subscription_reject(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    sub.status = 'Rejected'
    db.session.commit()
    flash(f'Subscription request for "{sub.clinic_name}" has been rejected.', 'info')
    return redirect(url_for('superadmin_subscriptions'))


@app.route('/superadmin/users', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_users():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'clinic_admin')
        clinic_name = request.form.get('clinic_name', '').strip() or f"{full_name}'s Clinic"
        package_id = request.form.get('package_id', '')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('superadmin_users'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('User with this username or email already exists.', 'warning')
            return redirect(url_for('superadmin_users'))

        new_user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role=role,
            is_active_user=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        if package_id and package_id.isdigit():
            pkg = SubscriptionPackage.query.get(int(package_id))
            if pkg:
                sub = Subscription(
                    user_id=new_user.id,
                    package_id=pkg.id,
                    clinic_name=clinic_name,
                    billing_cycle=pkg.billing_cycle,
                    status='Approved',
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=pkg.duration_days)
                )
                db.session.add(sub)
                db.session.commit()

        flash(f'Clinic User "{new_user.full_name}" ({role}) created successfully!', 'success')
        return redirect(url_for('superadmin_users'))

    packages = SubscriptionPackage.query.filter_by(is_active=True).all()
    users = User.query.filter(User.role != 'superadmin').order_by(User.created_at.desc()).all()
    return render_template('superadmin/users.html', users=users, packages=packages)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        new_password = request.form.get('new_password', '').strip()

        if not full_name or not email or not username:
            flash('Full Name, Email, and Username are required.', 'danger')
            return redirect(url_for('profile'))

        existing_user = User.query.filter((User.id != current_user.id) & ((User.username == username) | (User.email == email))).first()
        if existing_user:
            flash('Username or Email is already taken by another account.', 'warning')
            return redirect(url_for('profile'))

        current_user.full_name = full_name
        current_user.email = email
        current_user.username = username

        if new_password:
            current_user.set_password(new_password)
            flash('Profile details and password updated successfully!', 'success')
        else:
            flash('Profile details updated successfully!', 'success')

        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('profile.html')



@app.route('/superadmin/users/create', methods=['GET', 'POST'])
@login_required
@superadmin_required
def superadmin_user_create():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'clinic_admin')
        clinic_name = request.form.get('clinic_name', '').strip() or f"{full_name}'s Clinic"
        package_id = request.form.get('package_id', '')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('superadmin_user_create'))

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('User with this username or email already exists.', 'warning')
            return redirect(url_for('superadmin_user_create'))

        new_user = User(
            username=username,
            email=email,
            full_name=full_name or username,
            role=role,
            is_active_user=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        if package_id and package_id.isdigit():
            pkg = SubscriptionPackage.query.get(int(package_id))
            if pkg:
                sub = Subscription(
                    user_id=new_user.id,
                    package_id=pkg.id,
                    clinic_name=clinic_name,
                    billing_cycle=pkg.billing_cycle,
                    status='Approved',
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=pkg.duration_days)
                )
                db.session.add(sub)
                db.session.commit()

        flash(f'Clinic User "{new_user.full_name}" ({role}) created successfully!', 'success')
        return redirect(url_for('superadmin_users'))

    packages = SubscriptionPackage.query.filter_by(is_active=True).all()
    return render_template('superadmin/user_form.html', packages=packages)





# =========================================================================
# CLIENT SUBSCRIPTION & PLAN SELECTION ROUTES
# =========================================================================

@app.route('/subscription/plans')
def plans_list():
    packages = SubscriptionPackage.query.filter_by(is_active=True).all()
    
    monthly_packages = [p for p in packages if p.billing_cycle == 'Monthly']
    quarterly_packages = [p for p in packages if p.billing_cycle == 'Quarterly']
    yearly_packages = [p for p in packages if p.billing_cycle == 'Yearly']

    return render_template(
        'subscription/plans.html',
        packages=packages,
        monthly_packages=monthly_packages,
        quarterly_packages=quarterly_packages,
        yearly_packages=yearly_packages
    )


@app.route('/subscription/checkout/<int:package_id>', methods=['GET', 'POST'])
@login_required
def subscription_checkout(package_id):
    package = SubscriptionPackage.query.get_or_404(package_id)
    if request.method == 'POST':
        clinic_name = request.form.get('clinic_name', '').strip() or f"{current_user.full_name}'s Clinic"
        payment_method = request.form.get('payment_method', 'Credit Card').strip()
        payment_reference = request.form.get('payment_reference', '').strip() or f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        payment_notes = request.form.get('payment_notes', '').strip() or f"Paid via {payment_method}"

        existing_sub = Subscription.query.filter_by(user_id=current_user.id, status='Pending').first()
        if existing_sub:
            flash('You already have a pending subscription request under review by the Super Admin.', 'warning')
            return redirect(url_for('my_subscription_plan'))

        subscription = Subscription(
            user_id=current_user.id,
            package_id=package.id,
            clinic_name=clinic_name,
            billing_cycle=package.billing_cycle,
            status='Pending',
            payment_reference=payment_reference,
            payment_notes=payment_notes
        )
        db.session.add(subscription)
        db.session.commit()

        flash(f'Payment processed! Subscription request for "{package.name}" ({package.billing_cycle}) submitted for Super Admin activation.', 'success')
        return redirect(url_for('my_subscription_plan'))

    return render_template('subscription/checkout.html', package=package)


@app.route('/subscription/subscribe/<int:package_id>', methods=['POST'])
@login_required
def subscribe_package(package_id):
    package = SubscriptionPackage.query.get_or_404(package_id)
    clinic_name = request.form.get('clinic_name', '').strip() or f"{current_user.full_name}'s Clinic"
    payment_reference = request.form.get('payment_reference', '').strip()
    payment_notes = request.form.get('payment_notes', '').strip()

    # Check if there is already a pending subscription
    existing_sub = Subscription.query.filter_by(user_id=current_user.id, status='Pending').first()
    if existing_sub:
        flash('You already have a pending subscription request awaiting Super Admin approval.', 'warning')
        return redirect(url_for('my_subscription_plan'))

    subscription = Subscription(
        user_id=current_user.id,
        package_id=package.id,
        clinic_name=clinic_name,
        billing_cycle=package.billing_cycle,
        status='Pending',
        payment_reference=payment_reference,
        payment_notes=payment_notes
    )
    db.session.add(subscription)
    db.session.commit()

    flash(f'Subscription request for package "{package.name}" submitted! Awaiting Super Admin approval.', 'success')
    return redirect(url_for('my_subscription_plan'))



@app.route('/subscription/my-plan')
@login_required
def my_subscription_plan():
    user_subs = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.created_at.desc()).all()
    active_sub = current_user.active_subscription
    latest_sub = current_user.latest_subscription

    return render_template(
        'subscription/my_plan.html',
        user_subs=user_subs,
        active_sub=active_sub,
        latest_sub=latest_sub
    )

if __name__ == '__main__':
    print("Hospital Management System running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)

