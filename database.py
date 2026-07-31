from models import db, User, SubscriptionPackage

def seed_default_packages():
    defaults = [
        {
            'name': 'Basic Starter',
            'billing_cycle': 'Monthly',
            'price': 29.00,
            'duration_days': 30,
            'description': 'Perfect for small single-doctor clinics getting started.',
            'features': 'Patient Management, Electronic Prescriptions, Basic Billing & Invoicing, Email Support',
            'is_active': True
        },
        {
            'name': 'Professional Care',
            'billing_cycle': 'Quarterly',
            'price': 79.00,
            'duration_days': 90,
            'description': 'Ideal for growing multi-doctor clinics requiring complete inventory & accounting.',
            'features': 'All Starter Features, Pharmacy & Stock Management, Advanced Accounting & Expense Tracking, Priority Support, Detailed Analytics',
            'is_active': True
        },
        {
            'name': 'Enterprise Clinic',
            'billing_cycle': 'Yearly',
            'price': 299.00,
            'duration_days': 365,
            'description': 'Full-suite hospital management system for high-volume clinics and health centers.',
            'features': 'All Professional Features, Unlimited Operations, Custom Invoice Branding, Dedicated Account Manager, 24/7 Phone & Email Support',
            'is_active': True
        }
    ]

    for d in defaults:
        existing = SubscriptionPackage.query.filter_by(name=d['name'], billing_cycle=d['billing_cycle']).first()
        if not existing:
            p = SubscriptionPackage(**d)
            db.session.add(p)
    db.session.commit()


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_default_packages()

def check_superadmin_exists():
    return User.query.filter_by(role='superadmin').first() is not None

