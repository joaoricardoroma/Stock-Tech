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
import json

load_dotenv()

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, flash, session
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_caching import Cache
from flask_compress import Compress
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload, selectinload

from models import (db, User, Supplier, Wine, WineSale, WinePurchase, WineComp, CorkedWine,
                     Spirit, SpiritSale, SpiritPurchase, SubIngredient,
                     CocktailRecipe, CocktailIngredient, BarSale, BarWaste)

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
_engine_options = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
# pool_size / max_overflow only supported for non-SQLite engines
if not _db_url.startswith('sqlite'):
    _engine_options['pool_size'] = 5
    _engine_options['max_overflow'] = 10
    _engine_options['connect_args'] = {'connect_timeout': 10}  # PostgreSQL only
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = _engine_options

# Invoice image upload config
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'invoices')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp', 'heic'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 3600  # 1-hour browser cache for static assets
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
Compress(app)  # gzip all responses automatically (saves ~70% bandwidth on JSON & HTML)

# ---------------------------------------------------------------------------
# Cache — SimpleCache (in-process, single worker)
# Upgrade to RedisCache by changing CACHE_TYPE + CACHE_REDIS_URL in .env
# when running multiple Gunicorn workers.
# ---------------------------------------------------------------------------
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 600,  # 10 minutes
})

# Auto-invalidate cache after every DB commit — covers all write routes
# (sales, purchases, waste, CRUD) without touching each route individually.
from sqlalchemy import event as sa_event

@sa_event.listens_for(db.session, 'after_commit')
def _clear_cache_on_commit(session):
    cache.clear()

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
    first_of_month = today.replace(day=1)

    # Eager-load .wine on all weekly queries → .wine.name in the loop below is free
    weekly_sales = (WineSale.query
                    .options(joinedload(WineSale.wine))
                    .filter(WineSale.date >= monday, WineSale.date <= sunday)
                    .all())
    weekly_purchases = (WinePurchase.query
                        .options(joinedload(WinePurchase.wine))
                        .filter(WinePurchase.date_ordered >= monday,
                                WinePurchase.date_ordered <= sunday)
                        .all())
    weekly_comps = (WineComp.query
                    .options(joinedload(WineComp.wine))
                    .filter(WineComp.date >= monday, WineComp.date <= sunday)
                    .all())

    # Build day-by-day data
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = []
    weekly_comps_data = []

    for i in range(7):
        day_date = monday + timedelta(days=i)
        day_sales = [s for s in weekly_sales if s.date == day_date]
        day_purchases = [p for p in weekly_purchases if p.date_ordered == day_date]
        day_comps = [c for c in weekly_comps if c.date == day_date]

        total_sold = sum(s.quantity_sold for s in day_sales)
        total_ordered = sum(p.quantity_ordered for p in day_purchases)
        total_comps = sum(c.quantity for c in day_comps)

        wine_details = {}
        for s in day_sales:
            wname = s.wine.name if s.wine else 'Unknown'  # already in identity map
            if wname not in wine_details:
                wine_details[wname] = {'sold': 0, 'ordered': 0, 'wine_id': s.wine_id,
                                        'glasses_sold': 0, 'bottles_sold': 0}
            wine_details[wname]['sold'] += s.quantity_sold
            if s.sale_type == 'glass':
                wine_details[wname]['glasses_sold'] += s.quantity_sold
            else:
                wine_details[wname]['bottles_sold'] += s.quantity_sold

        for p in day_purchases:
            wname = p.wine.name if p.wine else 'Unknown'  # already in identity map
            if wname not in wine_details:
                wine_details[wname] = {'sold': 0, 'ordered': 0, 'wine_id': p.wine_id,
                                        'glasses_sold': 0, 'bottles_sold': 0}
            wine_details[wname]['ordered'] += p.quantity_ordered

        comp_details = {}
        for c in day_comps:
            wname = c.wine.name if c.wine else 'Unknown'  # already in identity map
            wine_obj = c.wine
            if wname not in comp_details:
                comp_details[wname] = {'total': 0, 'glasses': 0, 'bottles': 0, 'wine_id': c.wine_id, 'cost': 0.0}
            comp_details[wname]['total'] += c.quantity
            if c.sale_type == 'glass':
                comp_details[wname]['glasses'] += c.quantity
                if wine_obj:
                    gpb = wine_obj.glasses_per_bottle or 1
                    comp_details[wname]['cost'] = round(
                        comp_details[wname]['cost'] + (wine_obj.cost_price / gpb) * c.quantity, 2)
            else:
                comp_details[wname]['bottles'] += c.quantity
                if wine_obj:
                    comp_details[wname]['cost'] = round(
                        comp_details[wname]['cost'] + wine_obj.cost_price * c.quantity, 2)

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

        weekly_comps_data.append({
            'day_name': day_names[i],
            'date': day_date.isoformat(),
            'date_formatted': day_date.strftime('%d %b'),
            'total_comps': total_comps,
            'is_today': day_date == today,
            'is_past': day_date < today,
            'comp_details': comp_details,
        })

    # --- Pending Purchases (not yet cleared) ---
    pending_purchases = WinePurchase.query.filter_by(is_invoice_cleared=False).all()

    # --- Low Stock Alerts ---
    low_stock_wines = [w for w in wines if w.is_below_threshold]

    # --- KPIs (cached 10 min, cleared on any write) ---
    kpis = cache.get('wine_kpis')
    if kpis is None:
        total_stock_value = sum(w.stock_value for w in wines)
        total_cost_spent = sum(w.cost_price * w.current_stock_qty for w in wines)

        # Eager-load .wine so revenue loop has no hidden queries
        month_sales = (WineSale.query
                       .options(joinedload(WineSale.wine))
                       .filter(WineSale.date >= first_of_month)
                       .all())

        total_revenue = 0.0
        total_cost_of_sold = 0.0
        wine_sales_count = {}
        wine_margin_data = {}

        for sale in month_sales:
            wine = sale.wine  # already loaded — zero extra queries
            if wine:
                if sale.sale_type == 'glass':
                    gpb = wine.glasses_per_bottle or 1
                    unit_price = (wine.retail_price or 0) / gpb
                    unit_cost = wine.cost_price / gpb
                else:
                    unit_price = wine.retail_price or 0
                    unit_cost = wine.cost_price
                total_revenue += unit_price * sale.quantity_sold
                total_cost_of_sold += unit_cost * sale.quantity_sold
                wine_sales_count[wine.name] = wine_sales_count.get(wine.name, 0) + sale.quantity_sold
                if wine.name not in wine_margin_data:
                    wine_margin_data[wine.name] = wine.target_margin_percent or 0

        total_profit = round(total_revenue - total_cost_of_sold, 2)
        top_wine = max(wine_sales_count, key=wine_sales_count.get) if wine_sales_count else 'N/A'
        top_wine_qty = wine_sales_count.get(top_wine, 0) if top_wine != 'N/A' else 0
        highest_margin_wine = max(wine_margin_data, key=wine_margin_data.get) if wine_margin_data else 'N/A'
        highest_margin_pct = wine_margin_data.get(highest_margin_wine, 0) if highest_margin_wine != 'N/A' else 0

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
        cache.set('wine_kpis', kpis, timeout=600)

    # ── FIXED N+1: one GROUP BY for monthly sold per wine (was O(N×M) python filter) ──
    monthly_sold_rows = (db.session.query(WineSale.wine_id,
                                          db.func.sum(WineSale.quantity_sold))
                         .filter(WineSale.date >= first_of_month)
                         .group_by(WineSale.wine_id)
                         .all())
    monthly_sold_by_wine = {r[0]: int(r[1] or 0) for r in monthly_sold_rows}

    # ── FIXED N+1: one GROUP BY for last-sold date per wine (was N WineSale queries) ──
    last_sold_rows = (db.session.query(WineSale.wine_id,
                                       db.func.max(WineSale.date))
                      .group_by(WineSale.wine_id)
                      .all())
    last_sold_map = {r[0]: r[1] for r in last_sold_rows}

    # ── FIXED N+1: one GROUP BY for invoice counts (was N WinePurchase.count() queries) ──
    inv_count_rows = (db.session.query(WinePurchase.wine_id,
                                       db.func.count(WinePurchase.id))
                      .filter(WinePurchase.is_invoice_cleared == True,
                              WinePurchase.invoice_image_path.isnot(None))
                      .group_by(WinePurchase.wine_id)
                      .all())
    invoice_counts = {r[0]: int(r[1] or 0) for r in inv_count_rows}

    # Build wines_data with zero per-wine DB queries
    wines_data = []
    for w in wines:
        last_date = last_sold_map.get(w.id)
        d = w.to_dict()
        d['monthly_sold'] = monthly_sold_by_wine.get(w.id, 0)
        d['last_sold_date'] = last_date.strftime('%d %b') if last_date else 'Never'
        d['invoice_count'] = invoice_counts.get(w.id, 0)
        wines_data.append(d)

    week_comps_total = sum(d['total_comps'] for d in weekly_comps_data)

    # Get corked wines per supplier for display
    corked_by_supplier = {}
    recent_corked = CorkedWine.query.order_by(CorkedWine.date.desc()).limit(200).all()
    for c in recent_corked:
        sid = c.supplier_id
        if sid not in corked_by_supplier:
            corked_by_supplier[sid] = []
        corked_by_supplier[sid].append(c.to_dict())

    return render_template('wine_stock.html',
                           wines=wines_data,
                           suppliers=suppliers,
                           weekly_data=weekly_data,
                           weekly_comps_data=weekly_comps_data,
                           week_comps_total=week_comps_total,
                           pending_purchases=pending_purchases,
                           low_stock_wines=low_stock_wines,
                           kpis=kpis,
                           today=today.isoformat(),
                           week_offset=week_offset,
                           week_label=week_label,
                           corked_by_supplier=corked_by_supplier)



# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route('/api/wine/sale', methods=['POST'])
@login_required
def record_sale():
    """Record a wine sale (glass, bottle, or pairing)."""
    data = request.get_json()
    sale_date_str = data.get('date', date.today().isoformat())
    sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date()
    sale_type = data.get('sale_type', 'bottle')

    if sale_type == 'pairing':
        items = data.get('items', [])
        if not items:
            return jsonify({'error': 'No items provided for pairing'}), 400
        pairing_id = str(uuid.uuid4())
        results = []
        for item in items:
            wine = Wine.query.get_or_404(item['wine_id'])
            qty_glasses = float(item.get('quantity_glasses', 1))
            gpb = wine.glasses_per_bottle if wine.glasses_per_bottle else 1
            deduction = qty_glasses / gpb
            if wine.current_stock_qty < deduction:
                return jsonify({'error': f'Insufficient stock for {wine.name}'}), 400
            sale = WineSale(
                wine_id=wine.id,
                quantity_sold=qty_glasses,
                sale_type='pairing',
                pairing_group_id=pairing_id,
                date=sale_date
            )
            wine.current_stock_qty = round(wine.current_stock_qty - deduction, 4)
            db.session.add(sale)
            results.append({'wine': wine.name, 'deduction': round(deduction, 4)})
        db.session.commit()
        return jsonify({'success': True, 'pairing_id': pairing_id, 'items': results})

    # Standard glass or bottle sale
    wine_id = data.get('wine_id')
    quantity = data.get('quantity', 1)
    wine = Wine.query.get_or_404(wine_id)

    if sale_type == 'glass':
        gpb = wine.glasses_per_bottle if wine.glasses_per_bottle else 1
        deduction = quantity / gpb
    else:
        deduction = quantity

    if wine.current_stock_qty < deduction:
        return jsonify({'error': 'Insufficient stock'}), 400

    sale = WineSale(
        wine_id=wine_id,
        quantity_sold=quantity,
        sale_type=sale_type,
        date=sale_date
    )
    wine.current_stock_qty = round(wine.current_stock_qty - deduction, 4)
    db.session.add(sale)
    db.session.commit()

    return jsonify({
        'success': True,
        'new_stock': wine.current_stock_qty,
        'stock_display': wine.stock_display,
        'sale': sale.to_dict()
    })


@app.route('/api/wine/comp', methods=['POST'])
@login_required
def record_comp():
    """
    Record a complimentary (free) drink.
    DEDUCTS from stock — comps consume real inventory,
    they are just not counted as revenue.
    """
    data = request.get_json()
    wine_id = data.get('wine_id')
    quantity = data.get('quantity', 1)
    sale_type = data.get('sale_type', 'glass')  # 'glass' or 'bottle'
    comp_date = data.get('date', date.today().isoformat())

    wine = Wine.query.get_or_404(wine_id)

    # Calculate stock deduction (same logic as a sale)
    if sale_type == 'glass':
        gpb = wine.glasses_per_bottle if wine.glasses_per_bottle else 1
        deduction = quantity / gpb
    else:
        deduction = quantity

    if wine.current_stock_qty < deduction:
        return jsonify({'error': 'Insufficient stock for this comp'}), 400

    comp = WineComp(
        wine_id=wine_id,
        quantity=quantity,
        sale_type=sale_type,
        date=datetime.strptime(comp_date, '%Y-%m-%d').date()
    )
    wine.current_stock_qty = round(wine.current_stock_qty - deduction, 4)
    db.session.add(comp)
    db.session.commit()

    return jsonify({
        'success': True,
        'new_stock': wine.current_stock_qty,
        'stock_display': wine.stock_display,
        'comp': comp.to_dict()
    })


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

    # NOW add to stock (whole bottles purchased)
    wine = Wine.query.get(purchase.wine_id)
    wine.current_stock_qty = round(wine.current_stock_qty + purchase.quantity_ordered, 4)

    db.session.commit()

    return jsonify({
        'success': True,
        'new_stock': wine.current_stock_qty,
        'stock_display': wine.stock_display,
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

    # Eager-load .wine → .wine.name in loops below fires zero extra queries
    month_sales = (WineSale.query
                   .options(joinedload(WineSale.wine))
                   .filter(WineSale.date >= first_of_month).all())
    month_purchases = (WinePurchase.query
                       .options(joinedload(WinePurchase.wine))
                       .filter(WinePurchase.date_ordered >= first_of_month).all())
    month_comps = (WineComp.query
                   .options(joinedload(WineComp.wine))
                   .filter(WineComp.date >= first_of_month).all())
    wines = Wine.query.order_by(Wine.name).all()

    # Pre-index by wine_id → O(1) lookup in summary loop (was O(N×M) per-wine filter)
    sales_by_wine = {}
    for s in month_sales:
        sales_by_wine.setdefault(s.wine_id, []).append(s)
    comps_by_wine = {}
    for c in month_comps:
        comps_by_wine.setdefault(c.wine_id, []).append(c)
    purchases_by_wine = {}
    for p in month_purchases:
        purchases_by_wine.setdefault(p.wine_id, []).append(p)

    # Build week-by-week data for this month
    weeks = []
    wk_start = first_of_month - timedelta(days=first_of_month.weekday())
    while wk_start <= today:
        wk_end = wk_start + timedelta(days=6)
        wk_sales = [s for s in month_sales if wk_start <= s.date <= wk_end]
        wk_purchases = [p for p in month_purchases if wk_start <= p.date_ordered <= wk_end]
        wk_comps = [c for c in month_comps if wk_start <= c.date <= wk_end]

        days = []
        for i in range(7):
            d = wk_start + timedelta(days=i)
            d_sales = [s for s in wk_sales if s.date == d]
            d_purchases = [p for p in wk_purchases if p.date_ordered == d]
            d_comps = [c for c in wk_comps if c.date == d]

            wine_details = {}
            for s in d_sales:
                wn = s.wine.name if s.wine else 'Unknown'  # already in identity map
                wine_details.setdefault(wn, {'sold': 0, 'ordered': 0, 'glasses_sold': 0, 'bottles_sold': 0})
                wine_details[wn]['sold'] += s.quantity_sold
                if s.sale_type == 'glass':
                    wine_details[wn]['glasses_sold'] += s.quantity_sold
                else:
                    wine_details[wn]['bottles_sold'] += s.quantity_sold

            for p in d_purchases:
                wn = p.wine.name if p.wine else 'Unknown'  # already in identity map
                wine_details.setdefault(wn, {'sold': 0, 'ordered': 0, 'glasses_sold': 0, 'bottles_sold': 0})
                wine_details[wn]['ordered'] += p.quantity_ordered

            comp_details = {}
            for c in d_comps:
                wn = c.wine.name if c.wine else 'Unknown'
                wine_obj = c.wine
                comp_details.setdefault(wn, {'total': 0, 'glasses': 0, 'bottles': 0, 'cost': 0.0})
                comp_details[wn]['total'] += c.quantity
                if c.sale_type == 'glass':
                    comp_details[wn]['glasses'] += c.quantity
                    if wine_obj:
                        gpb = wine_obj.glasses_per_bottle or 1
                        comp_details[wn]['cost'] += round((wine_obj.cost_price / gpb) * c.quantity, 2)
                else:
                    comp_details[wn]['bottles'] += c.quantity
                    if wine_obj:
                        comp_details[wn]['cost'] += round(wine_obj.cost_price * c.quantity, 2)

            days.append({
                'date': d.isoformat(),
                'day_name': d.strftime('%A'),
                'date_formatted': d.strftime('%d %b'),
                'total_sold': sum(s.quantity_sold for s in d_sales),
                'total_ordered': sum(p.quantity_ordered for p in d_purchases),
                'total_comps': sum(c.quantity for c in d_comps),
                'wine_details': wine_details,
                'comp_details': comp_details,
            })

        weeks.append({
            'label': f"{wk_start.strftime('%d %b')} – {wk_end.strftime('%d %b')}",
            'start': wk_start.isoformat(),
            'end': wk_end.isoformat(),
            'days': days,
            'total_sold': sum(d['total_sold'] for d in days),
            'total_ordered': sum(d['total_ordered'] for d in days),
            'total_comps': sum(d['total_comps'] for d in days),
        })
        wk_start += timedelta(weeks=1)

    # Per-wine monthly summary — uses pre-indexed dicts, no per-wine queries
    total_revenue_all = 0.0
    wine_summary = []
    for wine in wines:
        w_sales = sales_by_wine.get(wine.id, [])
        w_comps = comps_by_wine.get(wine.id, [])
        w_purchases = purchases_by_wine.get(wine.id, [])

        sold_qty = sum(s.quantity_sold for s in w_sales)
        comps_qty = sum(c.quantity for c in w_comps)
        ordered = sum(p.quantity_ordered for p in w_purchases)

        revenue = 0.0
        cost = 0.0
        gpb = wine.glasses_per_bottle or 1
        for s in w_sales:
            if s.sale_type == 'glass':
                revenue += ((wine.retail_price or 0) / gpb) * s.quantity_sold
                cost += (wine.cost_price / gpb) * s.quantity_sold
            else:
                revenue += (wine.retail_price or 0) * s.quantity_sold
                cost += wine.cost_price * s.quantity_sold
        total_revenue_all += revenue

        # Compute comp cost (actual cost to the restaurant — cost_price after VAT, not retail)
        comp_cost = 0.0
        gpb = wine.glasses_per_bottle or 1
        for c in w_comps:
            if c.sale_type == 'glass':
                comp_cost += (wine.cost_price / gpb) * c.quantity
            else:
                comp_cost += wine.cost_price * c.quantity

        if sold_qty > 0 or ordered > 0 or comps_qty > 0:
            wine_summary.append({
                'name': wine.name,
                'sold': sold_qty,
                'comps': comps_qty,
                'comp_cost': round(comp_cost, 2),
                'ordered': ordered,
                'revenue': round(revenue, 2),
                'profit': round(revenue - cost, 2),
                'current_stock': wine.stock_display,
            })

    return jsonify({
        'month_label': today.strftime('%B %Y'),
        'generated_at': datetime.now().strftime('%d %b %Y %H:%M'),
        'weeks': weeks,
        'wine_summary': sorted(wine_summary, key=lambda x: x['sold'], reverse=True),
        'kpis': {
            'total_sold': sum(s.quantity_sold for s in month_sales),
            'total_ordered': sum(p.quantity_ordered for p in month_purchases),
            'total_comps': sum(c.quantity for c in month_comps),
            'total_revenue': round(total_revenue_all, 2),
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
    wine.current_stock_qty = float(data.get('current_stock_qty', wine.current_stock_qty))

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
        current_stock_qty=float(data.get('current_stock_qty', 0)),
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
# Stock History Routes
# ---------------------------------------------------------------------------

@app.route('/stock-history')
@login_required
def stock_history():
    """Stock history log page."""
    return render_template('stock_history.html', today=date.today().isoformat())


@app.route('/api/stock-history')
@login_required
def api_stock_history():
    """Return all stock change events for wine and bar, paginated and filterable."""
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')
    category = request.args.get('category', 'all')  # all, wine, bar
    event_type = request.args.get('event_type', 'all')  # all, purchase, sale, comp, corked, waste
    page = max(1, int(request.args.get('page', 1)))
    per_page = 100

    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else None
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None
    except ValueError:
        from_date = to_date = None

    events = []

    # ---- WINE PURCHASES ----
    if category in ('all', 'wine') and event_type in ('all', 'purchase'):
        q = WinePurchase.query.options(joinedload(WinePurchase.wine))
        if from_date:
            q = q.filter(WinePurchase.date_ordered >= from_date)
        if to_date:
            q = q.filter(WinePurchase.date_ordered <= to_date)
        for p in q.all():
            w = p.wine
            events.append({
                'id': f'wp-{p.id}',
                'type': 'purchase',
                'category': 'wine',
                'name': w.name if w else 'Unknown',
                'date': p.date_ordered.isoformat(),
                'quantity': f'+{p.quantity_ordered}',
                'quantity_raw': p.quantity_ordered,
                'unit': 'bottle' if p.quantity_ordered == 1 else 'bottles',
                'price': f'€{w.cost_price:.2f}' if w else '—',
                'price_raw': w.cost_price if w else 0,
                'status': 'cleared' if p.is_invoice_cleared else 'pending',
                'is_cleared': p.is_invoice_cleared,
                'date_cleared': p.date_cleared.isoformat() if p.date_cleared else None,
                'notes': f'Order of {p.quantity_ordered} bottles',
                'icon': 'fa-plus-circle',
                'color': '#34d399',
                'order_group_id': str(p.id),
            })

    # ---- WINE SALES ----
    if category in ('all', 'wine') and event_type in ('all', 'sale'):
        q = WineSale.query.options(joinedload(WineSale.wine))
        if from_date:
            q = q.filter(WineSale.date >= from_date)
        if to_date:
            q = q.filter(WineSale.date <= to_date)
        for s in q.all():
            w = s.wine
            qty_label = f'-{s.quantity_sold}g' if s.sale_type == 'glass' else f'-{s.quantity_sold}b'
            events.append({
                'id': f'ws-{s.id}',
                'type': 'sale',
                'category': 'wine',
                'name': w.name if w else 'Unknown',
                'date': s.date.isoformat(),
                'quantity': qty_label,
                'quantity_raw': -s.quantity_sold,
                'unit': s.sale_type,
                'price': f'€{w.retail_price:.2f}' if w and w.retail_price else '—',
                'price_raw': w.retail_price if w and w.retail_price else 0,
                'status': 'done',
                'is_cleared': True,
                'date_cleared': None,
                'notes': f'{s.sale_type.capitalize()} sale',
                'icon': 'fa-minus-circle',
                'color': '#fb7185',
                'order_group_id': s.pairing_group_id,
            })

    # ---- WINE COMPS ----
    if category in ('all', 'wine') and event_type in ('all', 'comp'):
        q = WineComp.query.options(joinedload(WineComp.wine))
        if from_date:
            q = q.filter(WineComp.date >= from_date)
        if to_date:
            q = q.filter(WineComp.date <= to_date)
        for c in q.all():
            w = c.wine
            events.append({
                'id': f'wc-{c.id}',
                'type': 'comp',
                'category': 'wine',
                'name': w.name if w else 'Unknown',
                'date': c.date.isoformat(),
                'quantity': f'-{c.quantity}',
                'quantity_raw': -c.quantity,
                'unit': c.sale_type,
                'price': '€0',
                'price_raw': 0,
                'status': 'done',
                'is_cleared': True,
                'date_cleared': None,
                'notes': f'Complimentary {c.sale_type}',
                'icon': 'fa-gift',
                'color': '#a78bfa',
                'order_group_id': None,
            })

    # ---- WINE CORKED ----
    if category in ('all', 'wine') and event_type in ('all', 'corked'):
        q = CorkedWine.query.options(joinedload(CorkedWine.wine))
        if from_date:
            q = q.filter(CorkedWine.date >= from_date)
        if to_date:
            q = q.filter(CorkedWine.date <= to_date)
        for c in q.all():
            w = c.wine
            events.append({
                'id': f'cw-{c.id}',
                'type': 'corked',
                'category': 'wine',
                'name': w.name if w else 'Unknown',
                'date': c.date.isoformat(),
                'quantity': f'-{c.quantity}',
                'quantity_raw': -c.quantity,
                'unit': 'bottle',
                'price': f'€{w.cost_price * c.quantity:.2f}' if w else '—',
                'price_raw': w.cost_price * c.quantity if w else 0,
                'status': 'done',
                'is_cleared': True,
                'date_cleared': None,
                'notes': c.notes or 'Corked / spoiled',
                'icon': 'fa-ban',
                'color': '#ef4444',
                'order_group_id': None,
            })

    # ---- BAR PURCHASES (Spirit) ----
    if category in ('all', 'bar') and event_type in ('all', 'purchase'):
        q = SpiritPurchase.query.options(joinedload(SpiritPurchase.spirit))
        if from_date:
            q = q.filter(SpiritPurchase.date_ordered >= from_date)
        if to_date:
            q = q.filter(SpiritPurchase.date_ordered <= to_date)
        for p in q.all():
            s = p.spirit
            events.append({
                'id': f'sp-{p.id}',
                'type': 'purchase',
                'category': 'bar',
                'name': s.name if s else 'Unknown',
                'date': p.date_ordered.isoformat(),
                'quantity': f'+{p.bottles_ordered}',
                'quantity_raw': p.bottles_ordered,
                'unit': 'bottle' if p.bottles_ordered == 1 else 'bottles',
                'price': f'€{p.cost_per_bottle:.2f}' if p.cost_per_bottle else '—',
                'price_raw': p.cost_per_bottle or 0,
                'status': 'cleared' if p.is_invoice_cleared else 'pending',
                'is_cleared': p.is_invoice_cleared,
                'date_cleared': p.date_cleared.isoformat() if p.date_cleared else None,
                'notes': p.notes or f'Order of {p.bottles_ordered} bottles',
                'icon': 'fa-plus-circle',
                'color': '#34d399',
                'order_group_id': str(p.id),
            })

    # ---- BAR SALES ----
    if category in ('all', 'bar') and event_type in ('all', 'sale'):
        q = BarSale.query.options(joinedload(BarSale.cocktail), joinedload(BarSale.spirit))
        if from_date:
            q = q.filter(BarSale.date >= from_date)
        if to_date:
            q = q.filter(BarSale.date <= to_date)
        for s in q.all():
            name = s.cocktail.name if s.sale_type == 'cocktail' and s.cocktail else (s.spirit.name if s.spirit else 'Unknown')
            events.append({
                'id': f'bs-{s.id}',
                'type': 'sale',
                'category': 'bar',
                'name': name,
                'date': s.date.isoformat(),
                'quantity': f'-{s.quantity}',
                'quantity_raw': -s.quantity,
                'unit': s.sale_type,
                'price': f'€{s.unit_price:.2f}' if s.unit_price else '—',
                'price_raw': s.unit_price or 0,
                'status': 'done',
                'is_cleared': True,
                'date_cleared': None,
                'notes': f'{s.sale_type.capitalize()} sale',
                'icon': 'fa-cocktail',
                'color': '#fb7185',
                'order_group_id': None,
            })

    # ---- BAR WASTE ----
    if category in ('all', 'bar') and event_type in ('all', 'waste'):
        q = BarWaste.query.options(
            joinedload(BarWaste.spirit),
            joinedload(BarWaste.sub_ingredient),
        )
        if from_date:
            q = q.filter(BarWaste.date >= from_date)
        if to_date:
            q = q.filter(BarWaste.date <= to_date)
        for w in q.all():
            name = 'Unknown'
            if w.waste_type == 'spirit' and w.spirit:
                name = w.spirit.name
            elif w.waste_type == 'sub_ingredient' and w.sub_ingredient:
                name = w.sub_ingredient.name
            events.append({
                'id': f'bw-{w.id}',
                'type': 'waste',
                'category': 'bar',
                'name': name,
                'date': w.date.isoformat(),
                'quantity': f'-{w.quantity}',
                'quantity_raw': -w.quantity,
                'unit': 'measures',
                'price': f'€{w.cost_impact:.2f}' if w.cost_impact else '—',
                'price_raw': w.cost_impact or 0,
                'status': 'done',
                'is_cleared': True,
                'date_cleared': None,
                'notes': w.reason or 'Waste / spillage',
                'icon': 'fa-trash',
                'color': '#fbbf24',
                'order_group_id': None,
            })

    # Sort by date descending
    events.sort(key=lambda x: x['date'], reverse=True)

    # Pagination
    total = len(events)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'events': events[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    })


# ---------------------------------------------------------------------------
# Corked Wine Route
# ---------------------------------------------------------------------------

@app.route('/api/wine/corked', methods=['POST'])
@login_required
def record_corked():
    """Record a corked (spoiled) wine bottle. Deducts from stock immediately."""
    supplier_id = request.form.get('supplier_id') or None
    wine_id = request.form.get('wine_id')
    quantity = int(request.form.get('quantity', 1))
    corked_date = request.form.get('date', date.today().isoformat())
    notes = request.form.get('notes', '').strip()

    wine = Wine.query.get_or_404(wine_id)

    if wine.current_stock_qty < quantity:
        return jsonify({'error': f'Insufficient stock (only {wine.stock_display} bottles)'}), 400

    # Handle optional image upload
    image_path = None
    image_original = None
    if 'corked_image' in request.files:
        file = request.files['corked_image']
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            is_image = ext in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic'}
            if is_image:
                unique_name = f"corked_{wine_id}_{uuid.uuid4().hex[:8]}.jpg"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                try:
                    img = Image.open(file.stream)
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    if img.width > 1200:
                        ratio = 1200 / img.width
                        img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
                    img.save(save_path, format='JPEG', quality=75, optimize=True)
                except Exception:
                    file.seek(0); file.save(save_path)
            else:
                unique_name = f"corked_{wine_id}_{uuid.uuid4().hex[:8]}.{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(save_path)
            image_path = f"uploads/invoices/{unique_name}"
            image_original = secure_filename(file.filename)

    corked = CorkedWine(
        wine_id=int(wine_id),
        supplier_id=int(supplier_id) if supplier_id else None,
        quantity=quantity,
        date=datetime.strptime(corked_date, '%Y-%m-%d').date(),
        image_path=image_path,
        image_original=image_original,
        notes=notes,
    )
    wine.current_stock_qty = round(wine.current_stock_qty - quantity, 4)
    db.session.add(corked)
    db.session.commit()

    return jsonify({
        'success': True,
        'new_stock': wine.current_stock_qty,
        'stock_display': wine.stock_display,
        'corked': corked.to_dict()
    })


# ---------------------------------------------------------------------------
# Wine Stock Check Routes
# ---------------------------------------------------------------------------

@app.route('/wine-stock/check')
@login_required
def wine_stock_check():
    """Stock check page — Virtual vs Real comparison for wines."""
    wines = Wine.query.order_by(Wine.name).all()
    return render_template('wine_check.html', wines=wines, today=date.today().isoformat())


@app.route('/api/wine/stock-check', methods=['POST'])
@login_required
def submit_wine_stock_check():
    """
    Accept {items: [{wine_id, real_qty}]}, update DB where different,
    return discrepancy list.
    """
    data = request.get_json()
    items = data.get('items', [])
    discrepancies = []

    # Bulk-load all wines referenced in a single query (eliminates N+1)
    wine_ids = [item['wine_id'] for item in items if item.get('wine_id')]
    wines_map = {w.id: w for w in Wine.query.filter(Wine.id.in_(wine_ids)).all()} if wine_ids else {}

    for item in items:
        wine = wines_map.get(item['wine_id'])
        if not wine:
            continue
        real_qty = float(item['real_qty'])
        virtual_qty = round(wine.current_stock_qty, 2)
        diff = round(real_qty - virtual_qty, 2)
        if abs(diff) > 0.0001:
            discrepancies.append({
                'wine_name': wine.name,
                'virtual_qty': virtual_qty,
                'real_qty': real_qty,
                'difference': diff,
            })
        wine.current_stock_qty = round(real_qty, 4)

    db.session.commit()
    return jsonify({'success': True, 'discrepancies': discrepancies})


# ---------------------------------------------------------------------------
# Bar Stock Check Routes
# ---------------------------------------------------------------------------

@app.route('/bar/check')
@login_required
def bar_stock_check():
    """Stock check page — Virtual vs Real comparison for bar spirits and sub-ingredients."""
    spirits = Spirit.query.order_by(Spirit.category, Spirit.name).all()
    sub_ingredients = SubIngredient.query.order_by(SubIngredient.category, SubIngredient.name).all()
    return render_template('bar_check.html',
                           spirits=spirits,
                           sub_ingredients=sub_ingredients,
                           today=date.today().isoformat())


@app.route('/api/bar/stock-check', methods=['POST'])
@login_required
def submit_bar_stock_check():
    """
    Accept {spirits: [{spirit_id, real_bottles}], sub_ingredients: [{id, real_stock}]},
    update DB where different, return discrepancy list.
    """
    data = request.get_json()
    discrepancies = []

    # Bulk-load all spirits and sub-ingredients referenced (eliminates N+1)
    spirit_ids = [i['spirit_id'] for i in data.get('spirits', []) if i.get('spirit_id')]
    spirits_map = {s.id: s for s in Spirit.query.filter(Spirit.id.in_(spirit_ids)).all()} if spirit_ids else {}

    sub_ids = [i['sub_ingredient_id'] for i in data.get('sub_ingredients', []) if i.get('sub_ingredient_id')]
    subs_map = {s.id: s for s in SubIngredient.query.filter(SubIngredient.id.in_(sub_ids)).all()} if sub_ids else {}

    for item in data.get('spirits', []):
        spirit = spirits_map.get(item['spirit_id'])
        if not spirit:
            continue
        real_bottles = float(item['real_bottles'])
        virtual_bottles = round(spirit.bottles_remaining, 2)
        diff = round(real_bottles - virtual_bottles, 2)
        if abs(diff) > 0.0001:
            discrepancies.append({
                'type': 'spirit',
                'name': spirit.name,
                'virtual_qty': virtual_bottles,
                'real_qty': real_bottles,
                'difference': diff,
                'unit': 'bottles',
            })
        # Convert real bottles back to measures and store
        spirit.current_measures = round(real_bottles * spirit.measures_per_bottle, 4)

    for item in data.get('sub_ingredients', []):
        sub = subs_map.get(item['sub_ingredient_id'])
        if not sub:
            continue
        real_stock = float(item['real_stock'])
        virtual_stock = round(sub.current_stock, 2)
        diff = round(real_stock - virtual_stock, 2)
        if abs(diff) > 0.0001:
            discrepancies.append({
                'type': 'sub_ingredient',
                'name': sub.name,
                'virtual_qty': virtual_stock,
                'real_qty': real_stock,
                'difference': diff,
                'unit': sub.unit,
            })
        sub.current_stock = round(real_stock, 4)

    db.session.commit()
    return jsonify({'success': True, 'discrepancies': discrepancies})


# ---------------------------------------------------------------------------
# BAR Routes
# ---------------------------------------------------------------------------

@app.route('/bar')
@login_required
def bar_stock():
    """Main Bar management page."""
    try:
        week_offset = int(request.args.get('week_offset', 0))
    except (ValueError, TypeError):
        week_offset = 0

    spirits = Spirit.query.order_by(Spirit.category, Spirit.name).all()
    sub_ingredients = SubIngredient.query.order_by(SubIngredient.category, SubIngredient.name).all()

    # Eager-load ingredients → spirit + sub_ingredient for each ingredient
    # so recipes_data = [r.to_dict() for r in recipes] fires ZERO extra queries
    recipes = (CocktailRecipe.query
               .options(
                   selectinload(CocktailRecipe.ingredients)
                   .joinedload(CocktailIngredient.spirit),
                   selectinload(CocktailRecipe.ingredients)
                   .joinedload(CocktailIngredient.sub_ingredient),
               )
               .order_by(CocktailRecipe.name).all())

    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    week_label = f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"
    first_of_month = today.replace(day=1)

    # Eager-load .cocktail and .spirit → loop name lookups are free
    weekly_bar_sales = (BarSale.query
                        .options(joinedload(BarSale.cocktail), joinedload(BarSale.spirit))
                        .filter(BarSale.date >= monday, BarSale.date <= sunday)
                        .all())
    weekly_purchases = SpiritPurchase.query.filter(
        SpiritPurchase.date_ordered >= monday, SpiritPurchase.date_ordered <= sunday
    ).all()
    weekly_waste = BarWaste.query.filter(
        BarWaste.date >= monday, BarWaste.date <= sunday
    ).all()

    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = []
    for i in range(7):
        day_date = monday + timedelta(days=i)
        day_sales = [s for s in weekly_bar_sales if s.date == day_date]
        day_waste = [w for w in weekly_waste if w.date == day_date]

        total_revenue = sum((s.unit_price or 0) * s.quantity for s in day_sales)
        total_waste_cost = sum(w.cost_impact or 0 for w in day_waste)

        sale_details = {}
        for s in day_sales:
            # .cocktail and .spirit are already in the identity map — no extra queries
            key = (s.cocktail.name if s.sale_type == 'cocktail' and s.cocktail
                   else (s.spirit.name if s.spirit else 'Unknown'))
            if key not in sale_details:
                sale_details[key] = {'qty': 0, 'revenue': 0, 'type': s.sale_type}
            sale_details[key]['qty'] += s.quantity
            sale_details[key]['revenue'] += round((s.unit_price or 0) * s.quantity, 2)

        weekly_data.append({
            'day_name': day_names[i],
            'date': day_date.isoformat(),
            'date_formatted': day_date.strftime('%d %b'),
            'total_revenue': round(total_revenue, 2),
            'total_units': sum(s.quantity for s in day_sales),
            'total_waste_cost': round(total_waste_cost, 2),
            'sale_details': sale_details,
            'is_today': day_date == today,
            'is_past': day_date < today,
        })

    # --- Bar KPIs (cached 10 min, cleared on any write) ---
    kpis = cache.get('bar_kpis')
    if kpis is None:
        month_bar_sales = (BarSale.query
                           .options(joinedload(BarSale.cocktail), joinedload(BarSale.spirit))
                           .filter(BarSale.date >= first_of_month)
                           .all())
        month_waste = BarWaste.query.filter(BarWaste.date >= first_of_month).all()
        month_purchases = SpiritPurchase.query.filter(
            SpiritPurchase.date_ordered >= first_of_month,
            SpiritPurchase.is_invoice_cleared == True
        ).all()

        total_revenue = sum((s.unit_price or 0) * s.quantity for s in month_bar_sales)
        total_waste_cost = sum(w.cost_impact or 0 for w in month_waste)
        total_purchase_cost = sum(
            (p.cost_per_bottle or 0) * p.bottles_ordered for p in month_purchases
        )

        # .cocktail / .spirit already loaded — no hidden queries per row
        cocktail_counts = {}
        shot_counts = {}
        for s in month_bar_sales:
            if s.sale_type == 'cocktail' and s.cocktail:
                cocktail_counts[s.cocktail.name] = cocktail_counts.get(s.cocktail.name, 0) + s.quantity
            elif s.sale_type == 'shot' and s.spirit:
                shot_counts[s.spirit.name] = shot_counts.get(s.spirit.name, 0) + s.quantity

        top_cocktail = max(cocktail_counts, key=cocktail_counts.get) if cocktail_counts else 'N/A'
        top_spirit_kpi = max(shot_counts, key=shot_counts.get) if shot_counts else 'N/A'
        total_stock_value = (sum(s.stock_value for s in spirits)
                             + sum(i.stock_value for i in sub_ingredients))

        kpis = {
            'total_revenue': round(total_revenue, 2),
            'total_waste_cost': round(total_waste_cost, 2),
            'total_purchase_cost': round(total_purchase_cost, 2),
            'total_stock_value': round(total_stock_value, 2),
            'low_stock_count': sum(1 for s in spirits if s.is_below_threshold),
            'total_spirits': len(spirits),
            'total_recipes': len(recipes),
            'top_cocktail': top_cocktail,
            'top_spirit': top_spirit_kpi,
        }
        cache.set('bar_kpis', kpis, timeout=600)

    low_stock_spirits = [s for s in spirits if s.is_below_threshold]
    pending_purchases = SpiritPurchase.query.filter_by(is_invoice_cleared=False).all()

    # ── FIXED N+1: last sold date per spirit — 2 aggregate queries instead of N queries ──
    # 1. Direct shot sales grouped by spirit
    direct_rows = (db.session.query(BarSale.spirit_id, db.func.max(BarSale.date))
                   .filter(BarSale.spirit_id.isnot(None))
                   .group_by(BarSale.spirit_id)
                   .all())
    spirit_last_map = {r[0]: r[1] for r in direct_rows}

    # 2. Via cocktail ingredient — join BarSale → CocktailIngredient grouped by spirit
    cocktail_rows = (db.session.query(CocktailIngredient.spirit_id,
                                      db.func.max(BarSale.date))
                     .join(BarSale, BarSale.cocktail_id == CocktailIngredient.recipe_id)
                     .filter(CocktailIngredient.spirit_id.isnot(None))
                     .group_by(CocktailIngredient.spirit_id)
                     .all())
    for r in cocktail_rows:
        existing = spirit_last_map.get(r[0])
        spirit_last_map[r[0]] = max(existing, r[1]) if existing else r[1]

    # Build spirits_data with zero per-spirit queries
    spirits_data = []
    for s in spirits:
        d = s.to_dict()
        last_date = spirit_last_map.get(s.id)
        d['last_sold_date'] = last_date.strftime('%d %b') if last_date else 'Never'
        spirits_data.append(d)

    # recipes ingredients already selectin-loaded above — to_dict() is free
    recipes_data = [r.to_dict() for r in recipes]
    sub_ingredients_data = [i.to_dict() for i in sub_ingredients]

    return render_template('bar_stock.html',
                           spirits=spirits_data,
                           sub_ingredients=sub_ingredients_data,
                           recipes=recipes_data,
                           weekly_data=weekly_data,
                           pending_purchases=[p.to_dict() for p in pending_purchases],
                           low_stock_spirits=[s.to_dict() for s in low_stock_spirits],
                           kpis=kpis,
                           today=today.isoformat(),
                           week_offset=week_offset,
                           week_label=week_label)




# --- Spirit CRUD ---

@app.route('/api/bar/spirit', methods=['POST'])
@login_required
def add_spirit():
    data = request.get_json()
    spirit = Spirit(
        name=data['name'],
        brand=data.get('brand'),
        category=data.get('category', 'vodka'),
        bottle_size_ml=float(data.get('bottle_size_ml', 700)),
        measure_ml=float(data.get('measure_ml', 25)),
        cost_price=float(data.get('cost_price', 0)),
        target_margin_percent=float(data.get('target_margin_percent', 70)),
        minimum_stock_bottles=int(data.get('minimum_stock_bottles', 1)),
        current_measures=float(data.get('current_measures', 0)),
        supplier_name=data.get('supplier_name'),
        notes=data.get('notes'),
    )
    # Manual override or auto-calculate
    if data.get('shot_retail_price'):
        spirit.shot_retail_price = float(data['shot_retail_price'])
        spirit.cocktail_price_per_measure = float(data.get('cocktail_price_per_measure', spirit.shot_retail_price))
    else:
        spirit.calculate_shot_price()
    db.session.add(spirit)
    db.session.commit()
    return jsonify({'success': True, 'spirit': spirit.to_dict()}), 201


@app.route('/api/bar/spirit/<int:spirit_id>', methods=['GET'])
@login_required
def get_spirit(spirit_id):
    spirit = Spirit.query.get_or_404(spirit_id)
    return jsonify(spirit.to_dict())


@app.route('/api/bar/spirit/<int:spirit_id>', methods=['PUT'])
@login_required
def update_spirit(spirit_id):
    spirit = Spirit.query.get_or_404(spirit_id)
    data = request.get_json()
    spirit.name = data.get('name', spirit.name)
    spirit.brand = data.get('brand', spirit.brand)
    spirit.category = data.get('category', spirit.category)
    spirit.bottle_size_ml = float(data.get('bottle_size_ml', spirit.bottle_size_ml))
    spirit.measure_ml = float(data.get('measure_ml', spirit.measure_ml))
    spirit.cost_price = float(data.get('cost_price', spirit.cost_price))
    spirit.target_margin_percent = float(data.get('target_margin_percent', spirit.target_margin_percent))
    spirit.minimum_stock_bottles = int(data.get('minimum_stock_bottles', spirit.minimum_stock_bottles))
    spirit.current_measures = float(data.get('current_measures', spirit.current_measures))
    spirit.supplier_name = data.get('supplier_name', spirit.supplier_name)
    spirit.notes = data.get('notes', spirit.notes)
    if data.get('shot_retail_price') is not None:
        spirit.shot_retail_price = float(data['shot_retail_price'])
    else:
        spirit.calculate_shot_price()
    if data.get('cocktail_price_per_measure') is not None:
        spirit.cocktail_price_per_measure = float(data['cocktail_price_per_measure'])
    db.session.commit()
    return jsonify({'success': True, 'spirit': spirit.to_dict()})


@app.route('/api/bar/spirit/<int:spirit_id>', methods=['DELETE'])
@login_required
def delete_spirit(spirit_id):
    spirit = Spirit.query.get_or_404(spirit_id)
    db.session.delete(spirit)
    db.session.commit()
    return jsonify({'success': True})


# --- Spirit Purchase ---

@app.route('/api/bar/spirit/purchase', methods=['POST'])
@login_required
def bar_record_purchase():
    data = request.get_json()
    spirit = Spirit.query.get_or_404(data['spirit_id'])
    purchase = SpiritPurchase(
        spirit_id=spirit.id,
        bottles_ordered=int(data.get('bottles_ordered', 1)),
        cost_per_bottle=float(data['cost_per_bottle']) if data.get('cost_per_bottle') else spirit.cost_price,
        date_ordered=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
        notes=data.get('notes'),
    )
    db.session.add(purchase)
    db.session.commit()
    return jsonify({'success': True, 'purchase': purchase.to_dict()})


@app.route('/api/bar/spirit/clear-invoice/<int:purchase_id>', methods=['POST'])
@login_required
def bar_clear_invoice(purchase_id):
    purchase = SpiritPurchase.query.get_or_404(purchase_id)
    if purchase.is_invoice_cleared:
        return jsonify({'error': 'Invoice already cleared'}), 400
    if 'invoice_image' not in request.files:
        return jsonify({'error': 'Invoice image is required.'}), 400
    file = request.files['invoice_image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Please upload a valid image or PDF.'}), 400
    ext = file.filename.rsplit('.', 1)[1].lower()
    is_image = ext in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic'}
    if is_image:
        unique_name = f"bar_invoice_{purchase_id}_{uuid.uuid4().hex[:8]}.jpg"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        try:
            img = Image.open(file.stream)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            if img.width > 1200:
                ratio = 1200 / img.width
                img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
            img.save(save_path, format='JPEG', quality=75, optimize=True)
        except Exception:
            file.seek(0); file.save(save_path)
    else:
        unique_name = f"bar_invoice_{purchase_id}_{uuid.uuid4().hex[:8]}.{ext}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)
    purchase.invoice_image_path = f"uploads/invoices/{unique_name}"
    purchase.invoice_image_original = secure_filename(file.filename)
    purchase.is_invoice_cleared = True
    purchase.date_cleared = datetime.utcnow()
    # Add measures to spirit
    spirit = Spirit.query.get(purchase.spirit_id)
    spirit.current_measures = round(spirit.current_measures + purchase.bottles_ordered * spirit.measures_per_bottle, 4)
    db.session.commit()
    return jsonify({'success': True, 'spirit': spirit.to_dict(), 'purchase': purchase.to_dict()})


# --- Bar Sale (cocktail or shot) ---

@app.route('/api/bar/sale', methods=['POST'])
@login_required
def bar_record_sale():
    """Record a bar sale. Deducts measures from spirit stock."""
    data = request.get_json()
    sale_type = data.get('sale_type', 'cocktail')
    quantity = int(data.get('quantity', 1))
    sale_date = datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date()

    if sale_type == 'cocktail':
        recipe = CocktailRecipe.query.get_or_404(data['cocktail_id'])
        unit_price = float(data.get('unit_price', recipe.sell_price))
        # Check & deduct stock for each ingredient
        for ing in recipe.ingredients:
            if ing.spirit_id and ing.spirit:
                needed = ing.quantity * quantity
                if ing.spirit.current_measures < needed:
                    return jsonify({'error': f'Insufficient measures of {ing.spirit.name}'}), 400
        for ing in recipe.ingredients:
            if ing.spirit_id and ing.spirit:
                ing.spirit.current_measures = round(ing.spirit.current_measures - ing.quantity * quantity, 4)
            elif ing.sub_ingredient_id and ing.sub_ingredient:
                ing.sub_ingredient.current_stock = round(
                    max(0, ing.sub_ingredient.current_stock - ing.quantity * quantity), 4)
        sale = BarSale(date=sale_date, sale_type='cocktail', cocktail_id=recipe.id,
                       quantity=quantity, unit_price=unit_price)
    else:  # shot
        spirit = Spirit.query.get_or_404(data['spirit_id'])
        measures = float(data.get('measures', 1))
        unit_price = float(data.get('unit_price', spirit.shot_retail_price or 0))
        needed = measures * quantity
        if spirit.current_measures < needed:
            return jsonify({'error': f'Insufficient measures of {spirit.name}'}), 400
        spirit.current_measures = round(spirit.current_measures - needed, 4)
        sale = BarSale(date=sale_date, sale_type='shot', spirit_id=spirit.id,
                       quantity=quantity, unit_price=unit_price)

    db.session.add(sale)
    db.session.commit()
    return jsonify({'success': True, 'sale': sale.to_dict()})


# --- Sub-Ingredient CRUD ---

@app.route('/api/bar/sub-ingredient', methods=['POST'])
@login_required
def add_sub_ingredient():
    data = request.get_json()
    item = SubIngredient(
        name=data['name'],
        category=data.get('category', 'mixer'),
        unit=data.get('unit', 'ml'),
        cost_per_unit=float(data.get('cost_per_unit', 0)),
        current_stock=float(data.get('current_stock', 0)),
        minimum_stock=float(data.get('minimum_stock', 0)),
        notes=data.get('notes'),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'sub_ingredient': item.to_dict()}), 201


@app.route('/api/bar/sub-ingredient/<int:item_id>', methods=['PUT'])
@login_required
def update_sub_ingredient(item_id):
    item = SubIngredient.query.get_or_404(item_id)
    data = request.get_json()
    item.name = data.get('name', item.name)
    item.category = data.get('category', item.category)
    item.unit = data.get('unit', item.unit)
    item.cost_per_unit = float(data.get('cost_per_unit', item.cost_per_unit))
    item.current_stock = float(data.get('current_stock', item.current_stock))
    item.minimum_stock = float(data.get('minimum_stock', item.minimum_stock))
    item.notes = data.get('notes', item.notes)
    db.session.commit()
    return jsonify({'success': True, 'sub_ingredient': item.to_dict()})


@app.route('/api/bar/sub-ingredient/<int:item_id>', methods=['DELETE'])
@login_required
def delete_sub_ingredient(item_id):
    item = SubIngredient.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# --- Cocktail Recipe CRUD ---

@app.route('/api/bar/cocktail', methods=['POST'])
@login_required
def add_cocktail():
    data = request.get_json()
    recipe = CocktailRecipe(
        name=data['name'],
        description=data.get('description'),
        sell_price=float(data.get('sell_price', 0)),
    )
    db.session.add(recipe)
    db.session.flush()  # get id before adding ingredients
    for ing_data in data.get('ingredients', []):
        ing = CocktailIngredient(
            recipe_id=recipe.id,
            spirit_id=ing_data.get('spirit_id'),
            sub_ingredient_id=ing_data.get('sub_ingredient_id'),
            quantity=float(ing_data.get('quantity', 1)),
            notes=ing_data.get('notes'),
        )
        db.session.add(ing)
    db.session.commit()
    return jsonify({'success': True, 'recipe': recipe.to_dict()}), 201


@app.route('/api/bar/cocktail/<int:recipe_id>', methods=['GET'])
@login_required
def get_cocktail(recipe_id):
    recipe = CocktailRecipe.query.get_or_404(recipe_id)
    return jsonify(recipe.to_dict())


@app.route('/api/bar/cocktail/<int:recipe_id>', methods=['PUT'])
@login_required
def update_cocktail(recipe_id):
    recipe = CocktailRecipe.query.get_or_404(recipe_id)
    data = request.get_json()
    recipe.name = data.get('name', recipe.name)
    recipe.description = data.get('description', recipe.description)
    recipe.sell_price = float(data.get('sell_price', recipe.sell_price))
    recipe.is_active = data.get('is_active', recipe.is_active)
    # Replace ingredients if provided
    if 'ingredients' in data:
        for ing in recipe.ingredients:
            db.session.delete(ing)
        db.session.flush()
        for ing_data in data['ingredients']:
            ing = CocktailIngredient(
                recipe_id=recipe.id,
                spirit_id=ing_data.get('spirit_id'),
                sub_ingredient_id=ing_data.get('sub_ingredient_id'),
                quantity=float(ing_data.get('quantity', 1)),
                notes=ing_data.get('notes'),
            )
            db.session.add(ing)
    db.session.commit()
    return jsonify({'success': True, 'recipe': recipe.to_dict()})


@app.route('/api/bar/cocktail/<int:recipe_id>', methods=['DELETE'])
@login_required
def delete_cocktail(recipe_id):
    recipe = CocktailRecipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({'success': True})


# --- Waste & Spillage ---

@app.route('/api/bar/waste', methods=['POST'])
@login_required
def bar_record_waste():
    data = request.get_json()
    waste_type = data.get('waste_type', 'spirit')
    quantity = float(data.get('quantity', 1))
    cost_impact = 0.0

    spirit_id = data.get('spirit_id')
    sub_id = data.get('sub_ingredient_id')

    if waste_type == 'spirit' and spirit_id:
        spirit = Spirit.query.get_or_404(spirit_id)
        cost_impact = round(spirit.cost_per_measure * quantity, 4)
        # Deduct from stock
        spirit.current_measures = round(max(0, spirit.current_measures - quantity), 4)
    elif waste_type == 'sub_ingredient' and sub_id:
        item = SubIngredient.query.get_or_404(sub_id)
        cost_impact = round(item.cost_per_unit * quantity, 4)
        item.current_stock = round(max(0, item.current_stock - quantity), 4)

    waste = BarWaste(
        date=datetime.strptime(data.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
        waste_type=waste_type,
        spirit_id=spirit_id if waste_type == 'spirit' else None,
        sub_ingredient_id=sub_id if waste_type == 'sub_ingredient' else None,
        quantity=quantity,
        reason=data.get('reason'),
        cost_impact=cost_impact,
    )
    db.session.add(waste)
    db.session.commit()
    return jsonify({'success': True, 'waste': waste.to_dict()})


@app.route('/api/bar/wastes')
@login_required
def get_bar_wastes():
    wastes = BarWaste.query.order_by(BarWaste.date.desc()).limit(100).all()
    return jsonify([w.to_dict() for w in wastes])


@app.route('/api/bar/stock-snapshot')
@login_required
def bar_stock_snapshot():
    spirits = Spirit.query.order_by(Spirit.category, Spirit.name).all()
    sub_ingredients = SubIngredient.query.order_by(SubIngredient.category, SubIngredient.name).all()
    return jsonify({
        'spirits': [s.to_dict() for s in spirits],
        'sub_ingredients': [i.to_dict() for i in sub_ingredients],
    })


@app.route('/api/bar/analysis')
@login_required
def bar_analysis():
    today = date.today()
    first_of_month = today.replace(day=1)
    # Eager-load .cocktail and .spirit → name lookups in loop are free
    sales = (BarSale.query
             .options(joinedload(BarSale.cocktail), joinedload(BarSale.spirit))
             .filter(BarSale.date >= first_of_month).all())
    wastes = BarWaste.query.filter(BarWaste.date >= first_of_month).all()
    purchases = SpiritPurchase.query.filter(
        SpiritPurchase.date_ordered >= first_of_month,
        SpiritPurchase.is_invoice_cleared == True
    ).all()

    total_revenue = sum((s.unit_price or 0) * s.quantity for s in sales)
    total_waste_cost = sum(w.cost_impact or 0 for w in wastes)
    total_purchase_cost = sum((p.cost_per_bottle or 0) * p.bottles_ordered for p in purchases)

    cocktail_breakdown = {}
    spirit_breakdown = {}
    for s in sales:
        if s.sale_type == 'cocktail' and s.cocktail:
            k = s.cocktail.name  # already in identity map
            if k not in cocktail_breakdown:
                cocktail_breakdown[k] = {'qty': 0, 'revenue': 0}
            cocktail_breakdown[k]['qty'] += s.quantity
            cocktail_breakdown[k]['revenue'] = round(
                cocktail_breakdown[k]['revenue'] + (s.unit_price or 0) * s.quantity, 2)
        elif s.sale_type == 'shot' and s.spirit:
            k = s.spirit.name  # already in identity map
            if k not in spirit_breakdown:
                spirit_breakdown[k] = {'qty': 0, 'revenue': 0}
            spirit_breakdown[k]['qty'] += s.quantity
            spirit_breakdown[k]['revenue'] = round(
                spirit_breakdown[k]['revenue'] + (s.unit_price or 0) * s.quantity, 2)

    return jsonify({
        'month_label': today.strftime('%B %Y'),
        'total_revenue': round(total_revenue, 2),
        'total_waste_cost': round(total_waste_cost, 2),
        'total_purchase_cost': round(total_purchase_cost, 2),
        'cocktail_breakdown': sorted(cocktail_breakdown.items(), key=lambda x: x[1]['revenue'], reverse=True),
        'spirit_breakdown': sorted(spirit_breakdown.items(), key=lambda x: x[1]['revenue'], reverse=True),
    })


# ---------------------------------------------------------------------------
# DB Initialization
# ---------------------------------------------------------------------------

def init_db():
    """Create tables and seed admin user if not exists."""
    with app.app_context():
        db.create_all()

        # Create Pearl user (primary account)
        existing = User.query.filter_by(username='Pearl').first()
        old_admin = User.query.filter_by(username='Admin').first()

        if existing:
            # Update password if Pearl already exists
            existing.password_hash = generate_password_hash('Pearl2000')
            db.session.commit()
            print("✓ Pearl user updated (Pearl / Pearl2000)")
        elif old_admin:
            # Migrate old Admin account to Pearl
            old_admin.username = 'Pearl'
            old_admin.password_hash = generate_password_hash('Pearl2000')
            db.session.commit()
            print("✓ Admin user migrated → Pearl (Pearl / Pearl2000)")
        else:
            admin = User(
                username='Pearl',
                password_hash=generate_password_hash('Pearl2000')
            )
            db.session.add(admin)
            db.session.commit()
            print("✓ Pearl user created (Pearl / Pearl2000)")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
