from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='superadmin') # superadmin, doctor, pharmacist, accountant
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def active_subscription(self):
        from datetime import datetime
        sub = Subscription.query.filter_by(user_id=self.id, status='Approved').order_by(Subscription.created_at.desc()).first()
        if sub and sub.end_date and sub.end_date < datetime.utcnow():
            sub.status = 'Expired'
            db.session.commit()
            return None
        return sub

    @property
    def latest_subscription(self):
        return Subscription.query.filter_by(user_id=self.id).order_by(Subscription.created_at.desc()).first()



class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False) # Male, Female, Other
    blood_group = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact = db.Column(db.String(50), nullable=True)
    medical_history = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prescriptions = db.relationship('Prescription', backref='patient', lazy=True, cascade='all, delete-orphan')
    bills = db.relationship('Bill', backref='patient', lazy=True, cascade='all, delete-orphan')
    vitals_records = db.relationship('PatientVital', backref='patient', lazy=True, cascade='all, delete-orphan')


class PatientVital(db.Model):
    __tablename__ = 'patient_vitals'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    bp = db.Column(db.String(30), nullable=True) # e.g. 120/80
    pulse = db.Column(db.String(30), nullable=True) # e.g. 72 bpm
    temp = db.Column(db.String(30), nullable=True) # e.g. 98.6 °F
    weight = db.Column(db.String(30), nullable=True) # e.g. 65 kg
    spo2 = db.Column(db.String(30), nullable=True) # e.g. 98%
    nurse_name = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)


class StockItem(db.Model):
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False) # Tablet, Syrup, Injection, Ointment, Equipment, Supplies
    batch_number = db.Column(db.String(50), nullable=True)
    supplier_name = db.Column(db.String(100), nullable=True)
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    
    # Strip / Pack helper fields for Tablets & Capsules
    tablets_per_strip = db.Column(db.Integer, default=1)
    strip_quantity = db.Column(db.Integer, default=0)
    strip_price = db.Column(db.Float, default=0.0)

    min_reorder_level = db.Column(db.Integer, nullable=False, default=10)
    expiry_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_reorder_level


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_no = db.Column(db.String(30), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_name = db.Column(db.String(120), nullable=False)
    diagnosis = db.Column(db.Text, nullable=True)
    vitals_bp = db.Column(db.String(20), nullable=True) # e.g. 120/80
    vitals_pulse = db.Column(db.String(20), nullable=True) # e.g. 72 bpm
    vitals_temp = db.Column(db.String(20), nullable=True) # e.g. 98.6 F
    vitals_weight = db.Column(db.String(20), nullable=True) # e.g. 70 kg
    advice = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Active') # Active, Billed, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('PrescriptionItem', backref='prescription', lazy=True, cascade='all, delete-orphan')


class PrescriptionItem(db.Model):
    __tablename__ = 'prescription_items'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=True)
    medicine_name = db.Column(db.String(150), nullable=False)
    unit = db.Column(db.String(50), default='Tablet') # e.g. Tablet, Bottle, Vial, Capsule
    dosage = db.Column(db.String(50), nullable=False) # e.g., 500mg, 1-0-1
    duration = db.Column(db.String(50), nullable=False) # e.g., 5 Days
    qty = db.Column(db.Integer, default=1) # e.g. 10
    food = db.Column(db.String(50), default='After Food') # After Food, Before Food, Empty Stomach, At Bedtime, With Food
    frequency = db.Column(db.String(50), nullable=True) # e.g., 1-0-1 or Twice Daily
    instructions = db.Column(db.String(200), nullable=True)

    stock_item = db.relationship('StockItem', lazy=True)


class Bill(db.Model):
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_no = db.Column(db.String(30), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    patient_name = db.Column(db.String(120), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=True)
    doctor_name = db.Column(db.String(120), nullable=True)
    
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    tax_percent = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    
    payment_status = db.Column(db.String(20), default='Paid') # Paid, Partial, Unpaid
    payment_method = db.Column(db.String(30), default='Cash') # Cash, Card, UPI, NetBanking, Insurance
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('BillItem', backref='bill', lazy=True, cascade='all, delete-orphan')
    prescription = db.relationship('Prescription', lazy=True)


class BillItem(db.Model):
    __tablename__ = 'bill_items'
    
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=True)
    item_name = db.Column(db.String(150), nullable=False)
    item_type = db.Column(db.String(50), default='Medicine') # Medicine, Consultation, Lab Test, Nursing, Procedure, Other
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False, default=0.0)


class AccountEntry(db.Model):
    __tablename__ = 'account_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_no = db.Column(db.String(30), unique=True, nullable=False)
    entry_type = db.Column(db.String(20), nullable=False) # Income, Expense
    category = db.Column(db.String(80), nullable=False) # Medical Billing Revenue, Pharmacy Sales, Medicine Purchase, Staff Salaries, Utilities & Rent, Equipment & Maintenance, Other
    amount = db.Column(db.Float, nullable=False, default=0.0)
    reference_no = db.Column(db.String(50), nullable=True) # e.g. Bill No or Invoice No
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(30), default='Cash')
    date = db.Column(db.Date, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PurchaseBill(db.Model):
    __tablename__ = 'purchase_bills'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_no = db.Column(db.String(30), unique=True, nullable=False)
    supplier_name = db.Column(db.String(120), nullable=False)
    supplier_invoice_no = db.Column(db.String(50), nullable=True)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_status = db.Column(db.String(20), default='Paid') # Paid, Partial, Unpaid
    payment_method = db.Column(db.String(30), default='Bank Transfer')
    purchase_date = db.Column(db.Date, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('PurchaseBillItem', backref='purchase_bill', lazy=True, cascade='all, delete-orphan')


class PurchaseBillItem(db.Model):
    __tablename__ = 'purchase_bill_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_bill_id = db.Column(db.Integer, db.ForeignKey('purchase_bills.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=True)
    item_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='Tablet')
    batch_number = db.Column(db.String(50), nullable=True)
    
    tablets_per_strip = db.Column(db.Integer, default=1)
    strip_quantity = db.Column(db.Integer, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=0) # total units
    cost_price = db.Column(db.Float, nullable=False, default=0.0) # unit cost price
    selling_price = db.Column(db.Float, nullable=False, default=0.0) # unit selling price
    total_cost = db.Column(db.Float, nullable=False, default=0.0)
    expiry_date = db.Column(db.Date, nullable=True)

    stock_item = db.relationship('StockItem', lazy=True)


class SubscriptionPackage(db.Model):
    __tablename__ = 'subscription_packages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    billing_cycle = db.Column(db.String(20), nullable=False, default='Monthly') # Monthly, Quarterly, Yearly
    price = db.Column(db.Float, nullable=False, default=0.0)
    duration_days = db.Column(db.Integer, nullable=False, default=30) # 30 for Monthly, 90 for Quarterly, 365 for Yearly
    description = db.Column(db.Text, nullable=True)
    features = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscriptions = db.relationship('Subscription', backref='package', lazy=True)


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('subscription_packages.id'), nullable=False)
    clinic_name = db.Column(db.String(150), nullable=False)
    billing_cycle = db.Column(db.String(20), nullable=False, default='Monthly') # Monthly, Quarterly, Yearly
    status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Approved, Rejected, Expired
    payment_reference = db.Column(db.String(100), nullable=True)
    payment_notes = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('user_subscriptions', lazy=True))

