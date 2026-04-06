"""
Seed data for Wine Stock Management System.
Pre-populates the database with suppliers, wines, sales (glass + bottle),
purchases, and comp drinks following the fractional stock logic.

STOCK LOGIC:
  - Each wine has glasses_per_bottle (typically 4–6 for 750ml bottles)
  - Bottle sale deducts 1.0 from stock
  - Glass sale deducts 1/glasses_per_bottle from stock
  - Comp drink also deducts (same as a sale, just not revenue)
  - Stock can be fractional: e.g. 8.5 = 8 full bottles + half bottle open
"""

from datetime import date, timedelta
import random

from app import app, db, init_db
from models import Supplier, Wine, WineSale, WinePurchase, WineComp, Spirit, SubIngredient, CocktailRecipe, CocktailIngredient, BarSale, BarWaste, SpiritPurchase


def seed_suppliers():
    """Create suppliers matching the reference images."""
    suppliers_data = [
        {
            'name': 'FEVBRE',
            'contact_email': 'orders@fevbre.ie',
            'contact_phone': '+353 1 234 5678',
            'contact_whatsapp': '+353 87 123 4567',
            'order_method': 'email',
            'delivery_cutoff_time': '14:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Anything',
        },
        {
            'name': 'CLASSIC DRINKS',
            'contact_email': 'sales@classicdrinks.ie',
            'contact_phone': '+353 1 345 6789',
            'contact_whatsapp': '+353 87 234 5678',
            'order_method': 'email',
            'delivery_cutoff_time': '12:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Anything',
        },
        {
            'name': 'GREEN ACRES',
            'contact_email': 'info@greenacres.ie',
            'contact_phone': '+353 1 456 7890',
            'order_method': 'phone',
            'delivery_cutoff_time': '15:00',
            'typical_delivery_days': 2,
            'minimum_order_note': 'Anything',
        },
        {
            'name': 'CAUBET WINES',
            'contact_email': 'orders@caubetwines.ie',
            'contact_phone': '+353 1 567 8901',
            'contact_whatsapp': '+353 86 345 6789',
            'order_method': 'whatsapp',
            'delivery_cutoff_time': '13:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Min 36 bottles',
        },
        {
            'name': 'BARRY & FITZWILLIAM',
            'contact_email': 'orders@barryfitz.ie',
            'contact_phone': '+353 1 678 9012',
            'contact_whatsapp': '+353 85 456 7890',
            'order_method': 'email',
            'delivery_cutoff_time': '14:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Anything',
        },
        {
            'name': 'CLASSIC GOURMET',
            'contact_email': 'sales@classicgourmet.ie',
            'contact_phone': '+353 1 789 0123',
            'order_method': 'email',
            'delivery_cutoff_time': '11:00',
            'typical_delivery_days': 2,
            'minimum_order_note': 'Min 36 bottles',
        },
        {
            'name': 'LAROUSSE',
            'contact_email': 'info@larousse.ie',
            'contact_phone': '+353 1 890 1234',
            'order_method': 'phone',
            'delivery_cutoff_time': '14:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Anything',
        },
        {
            'name': 'TINDAL',
            'contact_email': 'orders@tindal.ie',
            'contact_phone': '+353 1 901 2345',
            'contact_whatsapp': '+353 87 567 8901',
            'order_method': 'email',
            'delivery_cutoff_time': '13:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Min 24 bottles',
        },
        {
            'name': 'CASSIDY WINES',
            'contact_email': 'sales@cassidywines.ie',
            'contact_phone': '+353 1 012 3456',
            'order_method': 'email',
            'delivery_cutoff_time': '15:00',
            'typical_delivery_days': 2,
            'minimum_order_note': None,
        },
        {
            'name': 'NOMAD',
            'contact_email': 'hello@nomadwines.ie',
            'contact_phone': '+353 1 123 7890',
            'order_method': 'email',
            'delivery_cutoff_time': '14:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Min 24 bottles',
        },
        {
            'name': 'MORGANS WINES',
            'contact_email': 'orders@morganswines.ie',
            'contact_phone': '+353 1 234 8901',
            'order_method': 'phone',
            'delivery_cutoff_time': '12:00',
            'typical_delivery_days': 2,
            'minimum_order_note': 'Anything',
        },
        {
            'name': 'WINE MASON',
            'contact_email': 'info@winemason.ie',
            'contact_phone': '+353 1 345 9012',
            'order_method': 'email',
            'delivery_cutoff_time': '14:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Min 18 bottles',
        },
        {
            'name': 'EDWARD DILLON',
            'contact_email': 'orders@edwarddillon.ie',
            'contact_phone': '+353 1 456 0123',
            'order_method': 'email',
            'delivery_cutoff_time': '11:00',
            'typical_delivery_days': 1,
            'minimum_order_note': None,
        },
        {
            'name': 'LE CAVEAU',
            'contact_email': 'sales@lecaveau.ie',
            'contact_phone': '+353 1 567 1234',
            'order_method': 'phone',
            'delivery_cutoff_time': '13:00',
            'typical_delivery_days': 2,
            'minimum_order_note': None,
        },
        {
            'name': 'CONATY',
            'contact_email': 'orders@conaty.ie',
            'contact_phone': '+353 1 678 2345',
            'order_method': 'phone',
            'delivery_cutoff_time': '14:00',
            'typical_delivery_days': 1,
            'minimum_order_note': 'Anything',
        },
    ]

    created = []
    for s_data in suppliers_data:
        if not Supplier.query.filter_by(name=s_data['name']).first():
            supplier = Supplier(**s_data)
            db.session.add(supplier)
            created.append(s_data['name'])

    db.session.commit()
    print(f"✓ Created {len(created)} suppliers: {', '.join(created)}")
    return {s.name: s.id for s in Supplier.query.all()}


def seed_wines(supplier_map):
    """
    Create wines. glasses_per_bottle is carefully set per wine style:
    - Standard 750ml still wine: 5 glasses (typical restaurant pour ~150ml)
    - Premium/expensive wines sold mostly by glass: 4 glasses (175ml pour)
    - Dessert/sherry (half bottles or served smaller): 6 glasses
    - Champagne (150ml pours): 5 glasses
    """
    wines_data = [
        # FEVBRE wines
        {'name': 'SVB NZ Main Divide', 'supplier': 'FEVBRE', 'cost_price': 12.00, 'glasses': 5, 'margin': 70, 'stock': 18.0},
        {'name': 'Chardonnay Jordan South Africa', 'supplier': 'FEVBRE', 'cost_price': 15.30, 'glasses': 5, 'margin': 70, 'stock': 9.6},   # 9 btl + 3 glasses open
        {'name': 'Albarino Martin Codax', 'supplier': 'FEVBRE', 'cost_price': 13.00, 'glasses': 5, 'margin': 70, 'stock': 14.4},           # 14 btl + 2 glasses
        {'name': 'Esparao Alentejo Reserva', 'supplier': 'FEVBRE', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 15.0},
        {'name': 'Pouilly Fume Ch. de Tracy', 'supplier': 'FEVBRE', 'cost_price': 23.00, 'glasses': 4, 'margin': 70, 'stock': 4.5},        # 4 btl + 2 glasses
        {'name': 'Chablis le Verger', 'supplier': 'FEVBRE', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 6.25},               # 6 btl + 1 glass
        {'name': 'CDR Le Caillou White', 'supplier': 'FEVBRE', 'cost_price': 10.50, 'glasses': 5, 'margin': 70, 'stock': 12.0},
        {'name': 'Argentinian Malbec', 'supplier': 'FEVBRE', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 10.8},              # 10 btl + 4 glasses
        {'name': 'Pinot Noir NZ Main Divide', 'supplier': 'FEVBRE', 'cost_price': 14.50, 'glasses': 5, 'margin': 70, 'stock': 7.0},
        {'name': 'Meerkat', 'supplier': 'FEVBRE', 'cost_price': 8.50, 'glasses': 5, 'margin': 70, 'stock': 20.0},
        {'name': 'Alentejo Esparao RED', 'supplier': 'FEVBRE', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 9.2},             # 9 btl + 1 glass
        {'name': "Nero d'Avola", 'supplier': 'FEVBRE', 'cost_price': 9.80, 'glasses': 5, 'margin': 70, 'stock': 11.6},                    # 11 btl + 3 glasses
        {'name': 'Bourgogne Valmoisine', 'supplier': 'FEVBRE', 'cost_price': 19.00, 'glasses': 4, 'margin': 70, 'stock': 5.0},
        # CLASSIC DRINKS
        {'name': 'Albarino Terras Gauda', 'supplier': 'CLASSIC DRINKS', 'cost_price': 16.50, 'glasses': 5, 'margin': 70, 'stock': 6.4},    # 6 btl + 2 glasses
        {'name': 'Overture', 'supplier': 'CLASSIC DRINKS', 'cost_price': 9.50, 'glasses': 5, 'margin': 70, 'stock': 12.0},
        {'name': 'Valpolicella Vega Sicilia', 'supplier': 'CLASSIC DRINKS', 'cost_price': 14.00, 'glasses': 5, 'margin': 70, 'stock': 8.0},
        {'name': 'Clos du Pape', 'supplier': 'CLASSIC DRINKS', 'cost_price': 45.00, 'glasses': 4, 'margin': 70, 'stock': 3.75},            # 3 btl + 3 glasses
        {'name': 'Gevrey Chambertin', 'supplier': 'CLASSIC DRINKS', 'cost_price': 38.00, 'glasses': 4, 'margin': 70, 'stock': 2.5},        # 2 btl + 2 glasses
        # CAUBET WINES
        {'name': 'Pinot Grigio', 'supplier': 'CAUBET WINES', 'cost_price': 8.50, 'glasses': 5, 'margin': 70, 'stock': 18.0},
        {'name': 'Muscadet', 'supplier': 'CAUBET WINES', 'cost_price': 9.00, 'glasses': 5, 'margin': 70, 'stock': 12.0},
        {'name': 'Macon-Peronne', 'supplier': 'CAUBET WINES', 'cost_price': 14.00, 'glasses': 5, 'margin': 70, 'stock': 6.6},              # 6 btl + 3 glasses
        {'name': 'Saint-Veran', 'supplier': 'CAUBET WINES', 'cost_price': 17.00, 'glasses': 4, 'margin': 70, 'stock': 5.0},
        {'name': 'Saint-Aubin Thomas Morey', 'supplier': 'CAUBET WINES', 'cost_price': 25.00, 'glasses': 4, 'margin': 70, 'stock': 3.25},  # 3 btl + 1 glass
        # BARRY & FITZWILLIAM
        {'name': 'Rioja Reserva Beronia', 'supplier': 'BARRY & FITZWILLIAM', 'cost_price': 13.50, 'glasses': 5, 'margin': 70, 'stock': 8.0},
        {'name': 'Chateau Neuf du Pape Gabriel Meffre', 'supplier': 'BARRY & FITZWILLIAM', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 4.0},
        {'name': 'Pedro Ximenes Noe', 'supplier': 'BARRY & FITZWILLIAM', 'cost_price': 28.00, 'glasses': 6, 'margin': 70, 'stock': 2.5},   # 2 btl + 3 glasses (6-glass sherry)
        # CLASSIC GOURMET
        {'name': 'Pouilly Fuisse', 'supplier': 'CLASSIC GOURMET', 'cost_price': 24.00, 'glasses': 4, 'margin': 70, 'stock': 4.0},
        {'name': 'Saint-Amour', 'supplier': 'CLASSIC GOURMET', 'cost_price': 18.00, 'glasses': 5, 'margin': 70, 'stock': 5.0},
        {'name': 'Chateau Cap de Faugeres', 'supplier': 'CLASSIC GOURMET', 'cost_price': 19.00, 'glasses': 4, 'margin': 70, 'stock': 3.0},
        {'name': 'Saint Emilion Grand Cru', 'supplier': 'CLASSIC GOURMET', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 2.5}, # 2 btl + 2 glasses
        # LAROUSSE
        {'name': 'Touraine SVB Vincent La Cour', 'supplier': 'LAROUSSE', 'cost_price': 12.00, 'glasses': 5, 'margin': 70, 'stock': 10.0},
        {'name': 'Gruner Veltliner Heinz W', 'supplier': 'LAROUSSE', 'cost_price': 13.50, 'glasses': 4, 'margin': 70, 'stock': 7.5},       # 7 btl + 2 glasses
        # LE CAVEAU
        {'name': 'Chianti', 'supplier': 'LE CAVEAU', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 14.0},
        {'name': 'Corbieres', 'supplier': 'LE CAVEAU', 'cost_price': 9.50, 'glasses': 5, 'margin': 70, 'stock': 10.0},
        {'name': 'Cahors', 'supplier': 'LE CAVEAU', 'cost_price': 10.00, 'glasses': 5, 'margin': 70, 'stock': 8.4},                        # 8 btl + 2 glasses
        {'name': 'Cotes de Nuits Village', 'supplier': 'LE CAVEAU', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 3.0},
        {'name': 'Nuits-Saint-Georges', 'supplier': 'LE CAVEAU', 'cost_price': 32.00, 'glasses': 4, 'margin': 70, 'stock': 2.0},
        # CASSIDY WINES
        {'name': 'Shiraz McRae Wood', 'supplier': 'CASSIDY WINES', 'cost_price': 16.00, 'glasses': 5, 'margin': 70, 'stock': 6.0},
        {'name': 'Ribera Del Duero Emilio Moro', 'supplier': 'CASSIDY WINES', 'cost_price': 18.00, 'glasses': 4, 'margin': 70, 'stock': 5.0},
        {'name': 'ROSE Cotes de Provence', 'supplier': 'CASSIDY WINES', 'cost_price': 14.50, 'glasses': 5, 'margin': 70, 'stock': 7.0},
        # TINDAL
        {'name': 'SVB Pech des Cades', 'supplier': 'TINDAL', 'cost_price': 7.95, 'glasses': 5, 'margin': 70, 'stock': 35.0},
        {'name': 'Antinori', 'supplier': 'TINDAL', 'cost_price': 15.00, 'glasses': 4, 'margin': 70, 'stock': 7.0},
        # EDWARD DILLON
        {'name': 'Champagne Ruinart BLC de BLC', 'supplier': 'EDWARD DILLON', 'cost_price': 55.00, 'glasses': 5, 'margin': 65, 'stock': 3.4},  # 3 btl + 2 glasses
        {'name': 'Champagne Dom Perignon', 'supplier': 'EDWARD DILLON', 'cost_price': 120.00, 'glasses': 5, 'margin': 60, 'stock': 2.0},
        {'name': 'Champagne Veuve Clicquot Rose', 'supplier': 'EDWARD DILLON', 'cost_price': 52.00, 'glasses': 5, 'margin': 65, 'stock': 4.6},  # 4 btl + 3 glasses
        # NOMAD
        {'name': 'White Sancerre', 'supplier': 'NOMAD', 'cost_price': 18.00, 'glasses': 4, 'margin': 70, 'stock': 6.0},
        {'name': 'Bourgogne Chardonnay Closel', 'supplier': 'NOMAD', 'cost_price': 16.00, 'glasses': 5, 'margin': 70, 'stock': 5.2},       # 5 btl + 1 glass
        {'name': 'Chassagne Montrachet', 'supplier': 'NOMAD', 'cost_price': 35.00, 'glasses': 4, 'margin': 70, 'stock': 2.0},
        # WINE MASON
        {'name': 'German Riesling Wagner Stempel', 'supplier': 'WINE MASON', 'cost_price': 15.00, 'glasses': 4, 'margin': 70, 'stock': 6.25},  # 6 btl + 1 glass
        {'name': 'Fleurie', 'supplier': 'WINE MASON', 'cost_price': 16.00, 'glasses': 5, 'margin': 70, 'stock': 5.0},
    ]

    alert_wines = ['Gevrey Chambertin', 'Champagne Dom Perignon']
    created = 0
    for w_data in wines_data:
        if not Wine.query.filter_by(name=w_data['name']).first():
            # Bump stock by 12 bottles so only the chosen alert_wines trigger low stock
            stock = w_data['stock'] if w_data['name'] in alert_wines else w_data['stock'] + 12
            wine = Wine(
                name=w_data['name'],
                supplier_id=supplier_map.get(w_data['supplier']),
                cost_price=w_data['cost_price'],
                glasses_per_bottle=w_data['glasses'],
                target_margin_percent=w_data['margin'],
                minimum_stock_threshold=3,
                current_stock_qty=stock,
            )
            wine.calculate_prices()
            db.session.add(wine)
            created += 1

    db.session.commit()
    print(f"✓ Created {created} wines (with fractional stock levels)")


def seed_sales_and_comps():
    """
    Create realistic mixed sales (glass + bottle) and comp drinks.

    Sales logic:
      - High-volume, affordable wines: mostly bottle sales
      - Premium/expensive wines: mostly glass sales (people order 1-2 glasses)
      - Random glass quantity 1-3, bottle quantity 1-2
      - Each bottle sale deducts 1.0 from stock
      - Each glass sale deducts 1/glasses_per_bottle from stock
      - Comps: ~5-10% of sales are comps (free drinks)
    """
    if WineSale.query.count() > 0:
        print("✓ Sales data already exists, skipping")
        return

    today = date.today()
    wines = Wine.query.all()

    # Classify wines into categories for realistic selling patterns
    house_wines = [w for w in wines if w.cost_price <= 13.0]   # Cheap/house — sell by bottle
    mid_wines   = [w for w in wines if 13.0 < w.cost_price <= 20.0]  # Mid range — mix
    premium_wines = [w for w in wines if w.cost_price > 20.0]  # Premium — mostly by glass

    def add_sale(wine, qty, sale_type, sale_date):
        """Record a sale and deduct from stock."""
        gpb = wine.glasses_per_bottle
        deduction = (qty / gpb) if sale_type == 'glass' else qty
        # Only record if there's enough stock
        if wine.current_stock_qty >= deduction:
            sale = WineSale(
                wine_id=wine.id,
                date=sale_date,
                quantity_sold=qty,
                sale_type=sale_type,
            )
            wine.current_stock_qty = round(wine.current_stock_qty - deduction, 4)
            db.session.add(sale)
            return True
        return False

    def add_comp(wine, qty, sale_type, comp_date):
        """Record a comp drink and deduct from stock."""
        gpb = wine.glasses_per_bottle
        deduction = (qty / gpb) if sale_type == 'glass' else qty
        if wine.current_stock_qty >= deduction:
            comp = WineComp(
                wine_id=wine.id,
                date=comp_date,
                quantity=qty,
                sale_type=sale_type,
            )
            wine.current_stock_qty = round(wine.current_stock_qty - deduction, 4)
            db.session.add(comp)
            return True
        return False

    # Seed purchases first to ensure stock is added before sales eat it
    # Generate 30 days of activity
    for day_offset in range(29, -1, -1):  # oldest to newest so stock stays positive
        sale_date = today - timedelta(days=day_offset)
        is_weekend = sale_date.weekday() >= 4  # Friday, Sat, Sun busier

        # Daily sales volume (higher on weekends)
        bottle_sales_count = random.randint(4, 8) if is_weekend else random.randint(2, 5)
        glass_sales_count  = random.randint(8, 16) if is_weekend else random.randint(4, 10)

        # Bottle sales (house wines mostly)
        for _ in range(bottle_sales_count):
            wine = random.choice(house_wines + mid_wines)
            qty = random.randint(1, 2)
            add_sale(wine, qty, 'bottle', sale_date)

        # Glass sales (all price ranges — mostly mid/premium by glass)
        for _ in range(glass_sales_count):
            wine = random.choice(mid_wines + premium_wines)
            qty = random.randint(1, 3)
            add_sale(wine, qty, 'glass', sale_date)

        # Comp drinks: ~2-4 per day (mix glass + occasional bottle)
        comp_count = random.randint(1, 4)
        for _ in range(comp_count):
            wine = random.choice(wines)
            # Comps are almost always by the glass
            sale_type = 'glass' if random.random() < 0.85 else 'bottle'
            qty = random.randint(1, 2)
            add_comp(wine, qty, sale_type, sale_date)

    db.session.commit()
    print(f"✓ Created realistic sales (glass + bottle) and comp drinks for last 30 days")


def seed_purchases():
    """Create sample purchase data including some pending invoices."""
    if WinePurchase.query.count() > 0:
        print("✓ Purchase data already exists, skipping")
        return

    today = date.today()
    wines = Wine.query.all()

    # Create cleared purchases (past 2 weeks)
    for day_offset in range(14, 2, -3):
        purchase_date = today - timedelta(days=day_offset)
        num_purchases = random.randint(2, 5)
        for _ in range(num_purchases):
            wine = random.choice(wines)
            qty = random.randint(6, 24)
            purchase = WinePurchase(
                wine_id=wine.id,
                date_ordered=purchase_date,
                quantity_ordered=qty,
                is_invoice_cleared=True
            )
            # NOTE: cleared purchases already added to stock via current_stock_qty in seed,
            # so we don't double-add here — these are just historical records.
            db.session.add(purchase)

    # Create some pending purchases (recent — not yet cleared)
    for _ in range(4):
        wine = random.choice(wines)
        qty = random.randint(6, 18)
        purchase = WinePurchase(
            wine_id=wine.id,
            date_ordered=today - timedelta(days=random.randint(0, 2)),
            quantity_ordered=qty,
            is_invoice_cleared=False
        )
        db.session.add(purchase)

    db.session.commit()
    print(f"✓ Created sample purchase records (cleared + pending invoices)")

def seed_bar_suppliers():
    bar_supplier_names = ['Connalty', 'Celtic Whiskey']
    created = 0
    for name in bar_supplier_names:
        if not Supplier.query.filter_by(name=name).first():
            s = Supplier(name=name, order_method='phone',
                         typical_delivery_days=2, minimum_order_note='Min. 6 bottles')
            db.session.add(s)
            created += 1
    db.session.commit()
    print(f"✓ Created {created} bar suppliers")
    return {s.name: s.id for s in Supplier.query.all()}

def seed_spirits(supplier_map):
    # Cost price = net cost per 700ml bottle, stock = bottles on hand
    # Measure = 35.5ml (Irish standard), margin varies by category
    # Suppliers: Celtic Whiskey for all whiskey, Connalty for everything else
    def m(cost, stock, cat, mg, sup, min_s=1):
        mpb = 700 / 35.5
        cpm = cost / mpb
        mult = 1 / (1 - mg / 100)
        shot = round(cpm * mult * 1.23, 2)
        cock = round(cpm * mult, 2)
        return {'cost_price': cost, 'stock_bottles': stock, 'category': cat,
                'margin': mg, 'supplier': sup, 'min_stock': min_s,
                'shot_retail_price': shot, 'cocktail_price_per_measure': cock}

    C = 'Connalty'; W = 'Celtic Whiskey'
    spirits_data = {
        # GINS
        'Gunpowder':            m(34.11, 1.50, 'gin',     70, C),
        'Tanqueray':            m(25.69, 2.00, 'gin',     72, C, 2),
        'Bombay Sapphire':      m(25.67, 2.00, 'gin',     72, C, 2),
        'Hendricks':            m(37.97, 1.50, 'gin',     68, C),
        'Monkey 47':            m(46.84, 1.25, 'gin',     65, C),
        'Tanqueray 0%':         m(17.89, 1.75, 'gin',     70, C),
        'Dingle Gin':           m(25.61, 0.75, 'gin',     70, W),
        # VODKAS
        'Smirnoff':             m(20.40, 0.75, 'vodka',   73, C, 2),
        'Belvedere':            m(29.87, 1.00, 'vodka',   68, C),
        'Grey Goose':           m(43.55, 1.25, 'vodka',   65, C),
        'Ketel One':            m(28.11, 1.25, 'vodka',   70, C),
        'Dingle Vodka':         m(21.59, 0.75, 'vodka',   70, W),
        # WHISKEY / WHISKY
        'Jameson':              m(26.02, 1.75, 'whiskey', 72, W, 2),
        'Jameson Cask Mates':   m(30.08, 1.25, 'whiskey', 70, W),
        'Jameson 18 Years':     m(170.54, 0.25,'whiskey', 60, W),
        'Jameson Barrel Select':m(40.07, 0.75, 'whiskey', 68, W),
        'Green Spot':           m(46.29, 0.75, 'whiskey', 67, W),
        'Red Spot':             m(95.89, 0.50, 'whiskey', 62, W),
        'Blackbush':            m(23.86, 0.75, 'whiskey', 72, W),
        'Bushmills 10y':        m(33.25, 1.00, 'whiskey', 70, W),
        'Connemara':            m(31.15, 0.75, 'whiskey', 70, W),
        'Johnnie Walker Black': m(30.94, 0.25, 'whiskey', 70, C),
        'Johnnie Walker Red':   m(21.95, 0.25, 'whiskey', 72, C),
        'Famous Grouse':        m(20.18, 0.25, 'whiskey', 72, C),
        'Glenmorangie':         m(40.26, 1.00, 'whiskey', 68, C),
        'Southern Comfort':     m(23.45, 1.25, 'whiskey', 72, C),
        'Red Breast 12':        m(54.07, 1.50, 'whiskey', 65, W),
        'Jack Daniels':         m(28.41, 1.25, 'whiskey', 70, C),
        'Drambuie':             m(30.16, 1.25, 'whiskey', 70, C),
        'Woodford Reserve':     m(37.68, 0.75, 'whiskey', 68, C),
        'Makers Mark':          m(31.70, 1.50, 'whiskey', 70, C),
        'Teeling Whiskey':      m(26.56, 1.50, 'whiskey', 70, W, 2),
        'Middleton Very Rare':  m(219.51, 1.25,'whiskey', 58, W),
        'Macallan Rare Cask':   m(234.96, 1.00,'whiskey', 58, W),
        'Teeling 30 Years':     m(545.43, 0.25,'whiskey', 55, W),
        'The Taoscan':          m(600.00, 0.75,'whiskey', 55, W),
        # RUM / TEQUILA
        'Bacardi':              m(21.99, 0.75, 'rum',     73, C),
        'Captain Morgan':       m(19.96, 1.25, 'rum',     73, C, 2),
        'Havana 3 Years':       m(23.07, 0.75, 'rum',     72, C),
        'Zacapa':               m(56.58, 0.25, 'rum',     65, C),
        'Kraken':               m(26.68, 1.25, 'rum',     70, C),
        'Fuba Cachaca':         m(26.67, 1.00, 'rum',     70, C),
        'Jose Cuervo Silver':   m(22.93, 2.00, 'tequila', 73, C, 2),
        # BRANDY / COGNAC
        'Hennessy VS':          m(36.11, 0.50, 'brandy',  68, C),
        'Hennessy VSOP':        m(53.77, 1.00, 'brandy',  65, C),
        'Hennessy XO':          m(170.92, 0.25,'brandy',  60, C),
        'Armagnac Delord VSOP': m(27.11, 0.75, 'brandy',  68, C),
        'Armagnac Delord XO':   m(38.09, 0.50, 'brandy',  65, C),
        'Calvados XO':          m(52.53, 0.25, 'brandy',  65, C),
        'Calvados VSOP':        m(25.37, 1.25, 'brandy',  68, C),
        'Grand Marnier':        m(35.01, 1.00, 'brandy',  68, C),
        'Poire William':        m(34.23, 0.25, 'brandy',  68, C),
        'Grappa':               m(30.20, 2.25, 'brandy',  70, C),
        'Midori Melon Liqueur': m(25.48, 1.25, 'liqueur', 70, C),
        'Remy Martin Louis XIII': m(1783.33, 0.25,'brandy',55, C),
        # LIQUEURS
        'Baileys':              m(17.60, 1.50, 'liqueur', 72, C, 2),
        'Tia Maria':            m(18.25, 1.25, 'liqueur', 72, C),
        'Amaretto':             m(20.95, 1.00, 'liqueur', 70, C),
        'Frangelico':           m(20.03, 1.00, 'liqueur', 70, C),
        'Kahlua':               m(17.51, 1.25, 'liqueur', 72, C),
        'Chambord':             m(20.00, 1.00, 'liqueur', 70, C),
        'Sambucca':             m(19.79, 1.25, 'liqueur', 70, C),
        'Limoncello Meletti':   m(16.50, 1.25, 'liqueur', 72, C),
        # APERITIFS / VERMOUTH
        'Martini Dry':          m(11.22, 1.00, 'liqueur', 72, C),
        'Martini Bianco':       m(11.22, 1.75, 'liqueur', 72, C),
        'Martini Rosso':        m(11.22, 0.75, 'liqueur', 72, C),
        'Valentia Island Vermouth': m(24.59, 0.25,'liqueur',68, C),
        'Cointreau':            m(25.81, 0.75, 'liqueur', 70, C),
        'St Germain':           m(29.22, 1.00, 'liqueur', 68, C),
        'Campari':              m(21.05, 1.25, 'liqueur', 70, C),
        'Ricard':               m(25.35, 0.50, 'liqueur', 68, C),
        'Aperol':               m(16.73, 0.75, 'liqueur', 72, C),
        # CREMES & LIQUEURS
        'Creme de Cassis':      m(18.17, 0.75, 'liqueur', 70, C),
        'Creme de Fraise':      m(17.24, 1.75, 'liqueur', 70, C),
        'Creme de Framboise':   m(18.17, 1.25, 'liqueur', 70, C),
        'Creme de Menthe':      m(14.76, 1.75, 'liqueur', 70, C),
        'Creme de Cacao':       m(15.66, 0.50, 'liqueur', 70, C),
        'Grenadine Syrup':      m(7.53,  0.75, 'liqueur', 72, C),
        'Blue Curacao':         m(17.67, 1.00, 'liqueur', 70, C),
    }

    created = 0
    # Explicitly low-stock spirits for demonstration (just 3)
    LOW_STOCK_NAMES = {'Poire William', 'Champagne Ruinart BLC de BLC', 'Zacapa'}
    for name, d in spirits_data.items():
        if not Spirit.query.filter_by(name=name).first():
            measures = round(d['stock_bottles'] * (700 / 35.5), 2)
            # Boost most spirits well above threshold; keep only 3 intentionally low
            if name not in LOW_STOCK_NAMES:
                measures = max(measures, round((d['min_stock'] + 3) * (700 / 35.5), 2))
            spirit = Spirit(
                name=name,
                category=d['category'],
                bottle_size_ml=700,
                measure_ml=35.5,
                cost_price=d['cost_price'],
                target_margin_percent=d['margin'],
                shot_retail_price=d['shot_retail_price'],
                cocktail_price_per_measure=d['cocktail_price_per_measure'],
                current_measures=measures,
                minimum_stock_bottles=d['min_stock'],
                supplier_name=d['supplier'],
            )
            db.session.add(spirit)
            created += 1
    db.session.commit()
    print(f"✓ Created {created} spirits ({len(spirits_data)} total)")
    return {s.name: s.id for s in Spirit.query.all()}

def seed_sub_ingredients():
    # Registry only — no stock, no price tracking
    subs_data = [
        {'name': 'Simple Syrup',        'category': 'syrup',   'unit': 'ml'},
        {'name': 'Lime Juice',          'category': 'juice',   'unit': 'ml'},
        {'name': 'Lemon Juice',         'category': 'juice',   'unit': 'ml'},
        {'name': 'Espresso',            'category': 'other',   'unit': 'shot'},
        {'name': 'Passion Fruit Puree', 'category': 'fruit',   'unit': 'ml'},
        {'name': 'Prosecco',            'category': 'mixer',   'unit': 'ml'},
        {'name': 'Soda Water',          'category': 'mixer',   'unit': 'ml'},
        {'name': 'Angostura Bitters',   'category': 'mixer',   'unit': 'dash'},
        {'name': 'Egg White',           'category': 'dairy',   'unit': 'ml'},
        {'name': 'Cranberry Juice',     'category': 'juice',   'unit': 'ml'},
        {'name': 'Orange Peel',         'category': 'garnish', 'unit': 'pieces'},
        {'name': 'Mint Leaves',         'category': 'garnish', 'unit': 'pieces'},
        {'name': 'Salt',                'category': 'garnish', 'unit': 'g'},
    ]
    created = 0
    for d in subs_data:
        if not SubIngredient.query.filter_by(name=d['name']).first():
            sub = SubIngredient(name=d['name'], category=d['category'], unit=d['unit'],
                                cost_per_unit=0, current_stock=0, minimum_stock=0)
            db.session.add(sub)
            created += 1
    db.session.commit()
    print(f"✓ Created {created} sub-ingredients")
    return {s.name: s.id for s in SubIngredient.query.all()}

def seed_cocktails(spirit_map, sub_map):
    def ing(sname=None, subname=None, qty=1):
        d = {'qty': qty}
        if sname: d['spirit_id'] = spirit_map.get(sname)
        if subname: d['sub_id'] = sub_map.get(subname)
        return d

    cocktails = [
        {'name': 'Espresso Martini',  'desc': 'Grey Goose, Tia Maria, Espresso, Syrup', 'price': 13.50,
         'ings': [ing('Grey Goose',1), ing('Tia Maria',0.5), ing(subname='Espresso',qty=1), ing(subname='Simple Syrup',qty=15)]},
        {'name': 'Pornstar Martini',  'desc': 'Grey Goose, Passion Fruit, Prosecco', 'price': 14.00,
         'ings': [ing('Grey Goose',1), ing(subname='Passion Fruit Puree',qty=45), ing(subname='Simple Syrup',qty=15), ing(subname='Prosecco',qty=50)]},
        {'name': 'Whiskey Sour',      'desc': 'Jameson, Lemon, Syrup, Egg White', 'price': 13.00,
         'ings': [ing('Jameson',1.5), ing(subname='Lemon Juice',qty=30), ing(subname='Simple Syrup',qty=15), ing(subname='Egg White',qty=15), ing(subname='Angostura Bitters',qty=2)]},
        {'name': 'Margarita',         'desc': 'Jose Cuervo, Cointreau, Lime, Salt', 'price': 13.00,
         'ings': [ing('Jose Cuervo Silver',1.5), ing('Cointreau',0.5), ing(subname='Lime Juice',qty=30), ing(subname='Salt',qty=2)]},
        {'name': 'Aperol Spritz',     'desc': 'Aperol, Prosecco, Soda', 'price': 12.50,
         'ings': [ing('Aperol',1.5), ing(subname='Prosecco',qty=90), ing(subname='Soda Water',qty=30)]},
        {'name': 'Cosmopolitan',      'desc': 'Grey Goose, Cointreau, Cranberry, Lime', 'price': 13.50,
         'ings': [ing('Grey Goose',1), ing('Cointreau',0.5), ing(subname='Cranberry Juice',qty=30), ing(subname='Lime Juice',qty=15)]},
        {'name': 'Old Fashioned',     'desc': 'Woodford Reserve, Syrup, Bitters, Orange', 'price': 14.00,
         'ings': [ing('Woodford Reserve',1.5), ing(subname='Simple Syrup',qty=10), ing(subname='Angostura Bitters',qty=2), ing(subname='Orange Peel',qty=1)]},
        {'name': 'Negroni',           'desc': 'Hendricks, Campari, Martini Rosso', 'price': 13.50,
         'ings': [ing('Hendricks',1), ing('Campari',1), ing('Martini Rosso',1)]},
        {'name': 'Hugo Spritz',       'desc': 'St Germain, Prosecco, Soda, Mint', 'price': 12.50,
         'ings': [ing('St Germain',1), ing(subname='Prosecco',qty=90), ing(subname='Soda Water',qty=30), ing(subname='Mint Leaves',qty=3)]},
        {'name': 'Mojito',            'desc': 'Bacardi, Lime, Syrup, Mint, Soda', 'price': 12.50,
         'ings': [ing('Bacardi',1.5), ing(subname='Lime Juice',qty=30), ing(subname='Simple Syrup',qty=15), ing(subname='Mint Leaves',qty=6), ing(subname='Soda Water',qty=60)]},
    ]
    created = 0
    for c_data in cocktails:
        if not CocktailRecipe.query.filter_by(name=c_data['name']).first():
            recipe = CocktailRecipe(name=c_data['name'], description=c_data['desc'], sell_price=c_data['price'])
            db.session.add(recipe)
            db.session.flush()
            for ing_d in c_data['ings']:
                ci = CocktailIngredient(recipe_id=recipe.id, quantity=ing_d['qty'])
                if ing_d.get('spirit_id'):
                    ci.spirit_id = ing_d['spirit_id']
                elif ing_d.get('sub_id'):
                    ci.sub_ingredient_id = ing_d['sub_id']
                db.session.add(ci)
            created += 1
    db.session.commit()
    print(f"✓ Created {created} cocktail recipes")

def seed_bar_sales_and_waste():
    if BarSale.query.count() > 0:
        print("✓ Bar sale data already exists, skipping")
        return
    today = date.today()
    spirits = Spirit.query.all()
    recipes = CocktailRecipe.query.all()
    # High-volume spirits for more realistic shot data
    popular_spirits = [s for s in spirits if s.category in ('vodka', 'whiskey', 'rum', 'gin', 'tequila')]
    popular_spirits = popular_spirits or spirits
    for day_offset in range(29, -1, -1):
        sale_date = today - timedelta(days=day_offset)
        is_weekend = sale_date.weekday() >= 4
        shot_count = random.randint(12, 30) if is_weekend else random.randint(5, 12)
        for _ in range(shot_count):
            spirit = random.choice(popular_spirits)
            qty = random.randint(1, 3)
            if spirit.current_measures >= qty:
                spirit.current_measures -= qty
                price = spirit.shot_retail_price or 6.5
                bs = BarSale(date=sale_date, sale_type='shot', spirit_id=spirit.id, quantity=qty, unit_price=price)
                db.session.add(bs)
        if recipes:
            cocktail_count = random.randint(18, 40) if is_weekend else random.randint(6, 18)
            for _ in range(cocktail_count):
                recipe = random.choice(recipes)
                qty = random.randint(1, 2)
                bs = BarSale(date=sale_date, sale_type='cocktail', cocktail_id=recipe.id, quantity=qty, unit_price=recipe.sell_price)
                db.session.add(bs)
        if random.random() < 0.25:
            spirit = random.choice(spirits)
            bw = BarWaste(date=sale_date, waste_type='spirit', spirit_id=spirit.id,
                          quantity=1, reason='Spillage', cost_impact=spirit.cost_per_measure)
            db.session.add(bw)
    db.session.commit()
    print("✓ Created bar sales and waste for last 30 days")


def run_seed():
    """Run all seeders."""
    with app.app_context():
        print("\n🍷 Seeding Wine Stock Database...\n")
        supplier_map = seed_suppliers()
        seed_wines(supplier_map)
        seed_sales_and_comps()
        seed_purchases()

        print("\n🍹 Seeding Bar Stock Database...\n")
        supplier_map = seed_bar_suppliers()
        spirit_map = seed_spirits(supplier_map)
        sub_map = seed_sub_ingredients()
        seed_cocktails(spirit_map, sub_map)
        seed_bar_sales_and_waste()

        total_wine_sales = WineSale.query.count()
        total_comps = WineComp.query.count()
        glass_sales = WineSale.query.filter_by(sale_type='glass').count()
        bottle_sales = WineSale.query.filter_by(sale_type='bottle').count()
        total_bar_sales = BarSale.query.count()
        total_bar_wastes = BarWaste.query.count()

        print(f"\n📊 Summary:")
        print(f"   Wine Sales: {total_wine_sales} ({bottle_sales} bottle, {glass_sales} glass)")
        print(f"   Wine Comps: {total_comps}")
        print(f"   Purchases:  {WinePurchase.query.count()}")
        print(f"   Spirits:    {Spirit.query.count()}")
        print(f"   Bar Sales:  {total_bar_sales}")
        print(f"   Bar Wastes: {total_bar_wastes}")
        print(f"\n✅ Database seeded successfully!\n")


if __name__ == '__main__':
    init_db()
    run_seed()
