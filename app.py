"""
Wine Stock Management System — Flask Application
Main app with routes, API endpoints, and authentication.
"""

import logging
import os
import io
import uuid
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

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

# Use Neon PostgreSQL from .env, fall back to local SQLite for dev
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///wine_stock.db')
# Ensure SQLAlchemy accepts the postgresql:// URI from Neon
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Invoice image upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'invoices')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp', 'heic'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    # Week navigation via ?week_offset=N (0=this week, -1=last, +1=next)
    try:
        week_offset = int(request.args.get('week_offset', 0))
    except (ValueError, TypeError):
        week_offset = 0

    wines = Wine.query.order_by(Wine.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()

    # --- Weekly Sales Data (Mon-Sun of selected week) ---
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    week_label = f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"

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

    # invoice counts per wine for gallery column
    invoice_counts = {}
    for wine in wines:
        count = WinePurchase.query.filter_by(
            wine_id=wine.id,
            is_invoice_cleared=True
        ).filter(WinePurchase.invoice_image_path.isnot(None)).count()
        invoice_counts[wine.id] = count

    # Add invoice_count into wines_data
    for w in wines_data:
        w['invoice_count'] = invoice_counts.get(w['id'], 0)


    return render_template('wine_stock.html',
                           wines=wines_data,
                           suppliers=suppliers,
                           weekly_data=weekly_data,
                           pending_purchases=pending_purchases,
                           low_stock_wines=low_stock_wines,
                           kpis=kpis,
                           today=today.isoformat(),
                           week_offset=week_offset,
                           week_label=week_label)


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
    REQUIRES: A photo/scan of the invoice uploaded as multipart form field 'invoice_image'.
    CRITICAL: This is the ONLY place where purchased quantity gets added to Wine.current_stock_qty.
    """
    purchase = WinePurchase.query.get_or_404(purchase_id)

    if purchase.is_invoice_cleared:
        return jsonify({'error': 'Invoice already cleared'}), 400

    # Require invoice image
    if 'invoice_image' not in request.files:
        return jsonify({'error': 'Invoice image is required to clear this invoice.'}), 400

    file = request.files['invoice_image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Please upload a valid image or PDF (jpg, png, gif, pdf, webp).'}), 400

    # Save file with unique name — compress images using Pillow
    ext = file.filename.rsplit('.', 1)[1].lower()
    is_image = ext in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic'}

    if is_image:
        # Always save compressed images as JPEG
        unique_name = f"invoice_{purchase_id}_{uuid.uuid4().hex[:8]}.jpg"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        try:
            img = Image.open(file.stream)
            # Convert to RGB (handles RGBA, palette, HEIC, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            # Resize if wider than 1200px, maintain aspect ratio
            max_width = 1200
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)
            # Save compressed JPEG (quality 75 — good quality, ~80% smaller)
            img.save(save_path, format='JPEG', quality=75, optimize=True)
        except Exception as compress_err:
            # Fall back to saving the original if Pillow fails
            app.logger.warning(f'Pillow compression failed: {compress_err}, saving original')
            file.seek(0)
            file.save(save_path)
    else:
        # PDFs saved as-is
        unique_name = f"invoice_{purchase_id}_{uuid.uuid4().hex[:8]}.{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)

    purchase.invoice_image_path = f"uploads/invoices/{unique_name}"
    purchase.invoice_image_original = secure_filename(file.filename)
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


@app.route('/api/wine/<int:wine_id>/invoices')
@login_required
def get_wine_invoices(wine_id):
    """Get all cleared invoices with images for a wine."""
    purchases = WinePurchase.query.filter_by(
        wine_id=wine_id,
        is_invoice_cleared=True
    ).filter(
        WinePurchase.invoice_image_path.isnot(None)
    ).order_by(WinePurchase.date_cleared.desc()).all()

    invoices = []
    for p in purchases:
        invoices.append({
            'id': p.id,
            'date_ordered': p.date_ordered.isoformat(),
            'date_cleared': p.date_cleared.isoformat() if p.date_cleared else None,
            'quantity_ordered': p.quantity_ordered,
            'image_url': f"/static/{p.invoice_image_path}",
            'image_original': p.invoice_image_original,
        })

    return jsonify({'invoices': invoices, 'wine_id': wine_id})


@app.route('/api/monthly-report-data')
@login_required
def monthly_report_data():
    """Return full month breakdown for PDF generation."""
    today = date.today()
    first_of_month = today.replace(day=1)

    # All sales and purchases this month
    month_sales = WineSale.query.filter(WineSale.date >= first_of_month).all()
    month_purchases = WinePurchase.query.filter(WinePurchase.date_ordered >= first_of_month).all()
    wines = Wine.query.order_by(Wine.name).all()

    # Build week-by-week data for this month
    # Find all Mon–Sun weeks that overlap the month
    weeks = []
    # Start from the Monday of the week containing first_of_month
    wk_start = first_of_month - timedelta(days=first_of_month.weekday())
    while wk_start <= today:
        wk_end = wk_start + timedelta(days=6)
        wk_sales = [s for s in month_sales if wk_start <= s.date <= wk_end]
        wk_purchases = [p for p in month_purchases if wk_start <= p.date_ordered <= wk_end]

        days = []
        for i in range(7):
            d = wk_start + timedelta(days=i)
            d_sales = [s for s in wk_sales if s.date == d]
            d_purchases = [p for p in wk_purchases if p.date_ordered == d]
            wine_details = {}
            for s in d_sales:
                wn = s.wine.name if s.wine else 'Unknown'
                wine_details.setdefault(wn, {'sold': 0, 'ordered': 0})
                wine_details[wn]['sold'] += s.quantity_sold
            for p in d_purchases:
                wn = p.wine.name if p.wine else 'Unknown'
                wine_details.setdefault(wn, {'sold': 0, 'ordered': 0})
                wine_details[wn]['ordered'] += p.quantity_ordered
            days.append({
                'date': d.isoformat(),
                'day_name': d.strftime('%A'),
                'date_formatted': d.strftime('%d %b'),
                'total_sold': sum(s.quantity_sold for s in d_sales),
                'total_ordered': sum(p.quantity_ordered for p in d_purchases),
                'wine_details': wine_details,
            })

        weeks.append({
            'label': f"{wk_start.strftime('%d %b')} – {wk_end.strftime('%d %b')}",
            'start': wk_start.isoformat(),
            'end': wk_end.isoformat(),
            'days': days,
            'total_sold': sum(d['total_sold'] for d in days),
            'total_ordered': sum(d['total_ordered'] for d in days),
        })
        wk_start += timedelta(weeks=1)

    # Per-wine monthly summary
    wine_summary = []
    for wine in wines:
        sold = sum(s.quantity_sold for s in month_sales if s.wine_id == wine.id)
        ordered = sum(p.quantity_ordered for p in month_purchases if p.wine_id == wine.id)
        revenue = (wine.retail_price or 0) * sold
        cost = wine.cost_price * sold
        if sold > 0 or ordered > 0:
            wine_summary.append({
                'name': wine.name,
                'sold': sold,
                'ordered': ordered,
                'revenue': round(revenue, 2),
                'profit': round(revenue - cost, 2),
                'current_stock': wine.current_stock_qty,
            })

    return jsonify({
        'month_label': today.strftime('%B %Y'),
        'generated_at': datetime.now().strftime('%d %b %Y %H:%M'),
        'weeks': weeks,
        'wine_summary': sorted(wine_summary, key=lambda x: x['sold'], reverse=True),
        'kpis': {
            'total_sold': sum(s.quantity_sold for s in month_sales),
            'total_ordered': sum(p.quantity_ordered for p in month_purchases),
            'total_revenue': round(sum(
                (w.retail_price or 0) * sum(s.quantity_sold for s in month_sales if s.wine_id == w.id)
                for w in wines
            ), 2),
        }
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
