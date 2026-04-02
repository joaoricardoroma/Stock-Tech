"""
Wine Stock Management System — Flask Application
Main app with routes, API endpoints, and authentication.
"""

import os
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, flash, session
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Supplier, Wine, WineSale, WinePurchase

# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'wine-stock-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wine_stock.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('wine_stock'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('wine_stock'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Main Dashboard Route
# ---------------------------------------------------------------------------

@app.route('/')
@login_required
def index():
    return redirect(url_for('wine_stock'))


@app.route('/wine-stock')
@login_required
def wine_stock():
    """Main wine stock dashboard.  Gathers all data for the template."""

    wines = Wine.query.order_by(Wine.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()

    # --- Weekly Sales Data (Mon-Sun of current week) ---
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # Monday of this week
    sunday = monday + timedelta(days=6)

    weekly_sales = WineSale.query.filter(
        WineSale.date >= monday,
        WineSale.date <= sunday
    ).all()

    weekly_purchases = WinePurchase.query.filter(
        WinePurchase.date_ordered >= monday,
        WinePurchase.date_ordered <= sunday
    ).all()

    # Build day-by-day data
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        day_sales = [s for s in weekly_sales if s.date == day_date]
        day_purchases = [p for p in weekly_purchases if p.date_ordered == day_date]

        total_sold = sum(s.quantity_sold for s in day_sales)
        total_ordered = sum(p.quantity_ordered for p in day_purchases)

        # Wine-level detail for clicked day
        wine_details = {}
        for s in day_sales:
            wname = s.wine.name if s.wine else 'Unknown'
            if wname not in wine_details:
                wine_details[wname] = {'sold': 0, 'ordered': 0, 'wine_id': s.wine_id}
            wine_details[wname]['sold'] += s.quantity_sold

        for p in day_purchases:
            wname = p.wine.name if p.wine else 'Unknown'
            if wname not in wine_details:
                wine_details[wname] = {'sold': 0, 'ordered': 0, 'wine_id': p.wine_id}
            wine_details[wname]['ordered'] += p.quantity_ordered

        weekly_data.append({
            'day_name': day_names[i],
            'date': day_date.isoformat(),
            'date_formatted': day_date.strftime('%d %b'),
            'total_sold': total_sold,
            'total_ordered': total_ordered,
            'is_today': day_date == today,
            'is_past': day_date < today,
            'wine_details': wine_details,
        })

    # --- Pending Purchases (not yet cleared) ---
    pending_purchases = WinePurchase.query.filter_by(is_invoice_cleared=False).all()

    # --- Low Stock Alerts ---
    low_stock_wines = [w for w in wines if w.is_below_threshold]

    # --- KPI Calculations ---
    total_stock_value = sum(w.stock_value for w in wines)
    total_cost_spent = sum(w.cost_price * w.current_stock_qty for w in wines)

    # Monthly sales data for profit calculation
    first_of_month = today.replace(day=1)
    month_sales = WineSale.query.filter(WineSale.date >= first_of_month).all()

    total_revenue = 0
    total_cost_of_sold = 0
    wine_sales_count = {}
    wine_margin_data = {}

    for sale in month_sales:
        wine = sale.wine
        if wine:
            revenue = (wine.retail_price or 0) * sale.quantity_sold
            cost = wine.cost_price * sale.quantity_sold
            total_revenue += revenue
            total_cost_of_sold += cost

            if wine.name not in wine_sales_count:
                wine_sales_count[wine.name] = 0
            wine_sales_count[wine.name] += sale.quantity_sold

            if wine.name not in wine_margin_data:
                wine_margin_data[wine.name] = wine.target_margin_percent or 0

    total_profit = round(total_revenue - total_cost_of_sold, 2)
    top_wine = max(wine_sales_count, key=wine_sales_count.get) if wine_sales_count else 'N/A'
    top_wine_qty = wine_sales_count.get(top_wine, 0) if top_wine != 'N/A' else 0
    highest_margin_wine = max(wine_margin_data, key=wine_margin_data.get) if wine_margin_data else 'N/A'
    highest_margin_pct = wine_margin_data.get(highest_margin_wine, 0) if highest_margin_wine != 'N/A' else 0

    # Wine data enriched with monthly sales
    wines_data = []
    for w in wines:
        monthly_sold = sum(
            s.quantity_sold for s in month_sales if s.wine_id == w.id
        )
        last_sale = WineSale.query.filter_by(wine_id=w.id).order_by(
            WineSale.date.desc()
        ).first()
        last_sold_date = last_sale.date.strftime('%d %b') if last_sale else 'Never'

        wines_data.append({
            **w.to_dict(),
            'monthly_sold': monthly_sold,
            'last_sold_date': last_sold_date,
        })

    kpis = {
        'total_stock_value': round(total_stock_value, 2),
        'total_cost_spent': round(total_cost_spent, 2),
        'total_profit': total_profit,
        'total_revenue': round(total_revenue, 2),
        'top_wine': top_wine,
        'top_wine_qty': top_wine_qty,
        'highest_margin_wine': highest_margin_wine,
        'highest_margin_pct': round(highest_margin_pct, 1),
        'low_stock_count': len(low_stock_wines),
        'total_wines': len(wines),
    }

    return render_template('wine_stock.html',
                           wines=wines_data,
                           suppliers=suppliers,
                           weekly_data=weekly_data,
                           pending_purchases=pending_purchases,
                           low_stock_wines=low_stock_wines,
                           kpis=kpis,
                           today=today.isoformat())


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route('/api/wine/sale', methods=['POST'])
@login_required
def record_sale():
    """Record a wine sale."""
    data = request.get_json()
    wine_id = data.get('wine_id')
    quantity = data.get('quantity', 1)
    sale_date = data.get('date', date.today().isoformat())

    wine = Wine.query.get_or_404(wine_id)

    if wine.current_stock_qty < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400

    sale = WineSale(
        wine_id=wine_id,
        quantity_sold=quantity,
        date=datetime.strptime(sale_date, '%Y-%m-%d').date()
    )
    wine.current_stock_qty -= quantity
    db.session.add(sale)
    db.session.commit()

    return jsonify({'success': True, 'new_stock': wine.current_stock_qty, 'sale': sale.to_dict()})


@app.route('/api/wine/purchase', methods=['POST'])
@login_required
def record_purchase():
    """Record a wine purchase order. Does NOT add to stock until invoice is cleared."""
    data = request.get_json()
    wine_id = data.get('wine_id')
    quantity = data.get('quantity', 1)
    order_date = data.get('date', date.today().isoformat())

    wine = Wine.query.get_or_404(wine_id)

    purchase = WinePurchase(
        wine_id=wine_id,
        quantity_ordered=quantity,
        date_ordered=datetime.strptime(order_date, '%Y-%m-%d').date()
    )
    db.session.add(purchase)
    db.session.commit()

    return jsonify({'success': True, 'purchase': purchase.to_dict()})


@app.route('/api/wine/clear-invoice/<int:purchase_id>', methods=['POST'])
@login_required
def clear_invoice(purchase_id):
    """
    Mark a purchase invoice as cleared.
    CRITICAL: This is the ONLY place where purchased quantity
    gets added to Wine.current_stock_qty.
    """
    purchase = WinePurchase.query.get_or_404(purchase_id)

    if purchase.is_invoice_cleared:
        return jsonify({'error': 'Invoice already cleared'}), 400

    purchase.is_invoice_cleared = True
    purchase.date_cleared = datetime.utcnow()

    # NOW add to stock
    wine = Wine.query.get(purchase.wine_id)
    wine.current_stock_qty += purchase.quantity_ordered

    db.session.commit()

    return jsonify({
        'success': True,
        'new_stock': wine.current_stock_qty,
        'purchase': purchase.to_dict()
    })


@app.route('/api/wine/<int:wine_id>', methods=['GET'])
@login_required
def get_wine(wine_id):
    """Get single wine details."""
    wine = Wine.query.get_or_404(wine_id)
    return jsonify(wine.to_dict())


@app.route('/api/wine/<int:wine_id>', methods=['PUT'])
@login_required
def update_wine(wine_id):
    """Update wine information."""
    wine = Wine.query.get_or_404(wine_id)
    data = request.get_json()

    wine.name = data.get('name', wine.name)
    wine.supplier_id = data.get('supplier_id', wine.supplier_id)
    wine.cost_price = float(data.get('cost_price', wine.cost_price))
    wine.glasses_per_bottle = int(data.get('glasses_per_bottle', wine.glasses_per_bottle))
    wine.target_margin_percent = float(data.get('target_margin_percent', wine.target_margin_percent))
    wine.minimum_stock_threshold = int(data.get('minimum_stock_threshold', wine.minimum_stock_threshold))
    wine.current_stock_qty = int(data.get('current_stock_qty', wine.current_stock_qty))

    wine.calculate_prices()
    db.session.commit()

    return jsonify({'success': True, 'wine': wine.to_dict()})


@app.route('/api/wine', methods=['POST'])
@login_required
def add_wine():
    """Add a new wine."""
    data = request.get_json()

    wine = Wine(
        name=data['name'],
        supplier_id=data.get('supplier_id'),
        cost_price=float(data.get('cost_price', 0)),
        glasses_per_bottle=int(data.get('glasses_per_bottle', 5)),
        target_margin_percent=float(data.get('target_margin_percent', 70)),
        minimum_stock_threshold=int(data.get('minimum_stock_threshold', 3)),
        current_stock_qty=int(data.get('current_stock_qty', 0)),
    )
    wine.calculate_prices()
    db.session.add(wine)
    db.session.commit()

    return jsonify({'success': True, 'wine': wine.to_dict()}), 201


@app.route('/api/supplier', methods=['POST'])
@login_required
def add_supplier():
    """Add a new supplier."""
    data = request.get_json()

    supplier = Supplier(
        name=data['name'],
        contact_email=data.get('contact_email'),
        contact_phone=data.get('contact_phone'),
        contact_whatsapp=data.get('contact_whatsapp'),
        order_method=data.get('order_method', 'email'),
        delivery_cutoff_time=data.get('delivery_cutoff_time'),
        typical_delivery_days=int(data.get('typical_delivery_days', 1)),
        minimum_order_note=data.get('minimum_order_note'),
    )
    db.session.add(supplier)
    db.session.commit()

    return jsonify({'success': True, 'supplier': supplier.to_dict()}), 201


@app.route('/api/wines/weekly-sales')
@login_required
def weekly_sales_api():
    """Get weekly sales data as JSON."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    sales = WineSale.query.filter(
        WineSale.date >= monday,
        WineSale.date <= sunday
    ).all()

    return jsonify([s.to_dict() for s in sales])


# ---------------------------------------------------------------------------
# DB Initialization
# ---------------------------------------------------------------------------

def init_db():
    """Create tables and seed admin user if not exists."""
    with app.app_context():
        db.create_all()

        # Create admin user
        if not User.query.filter_by(username='Admin').first():
            admin = User(
                username='Admin',
                password_hash=generate_password_hash('123')
            )
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created (Admin / 123)")
        else:
            print("✓ Admin user already exists")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
