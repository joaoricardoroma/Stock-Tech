"""
Seed data for Wine Stock Management System.
Pre-populates the database with suppliers and wines from the reference images.
"""

from datetime import date, timedelta
import random

from app import app, db, init_db
from models import Supplier, Wine, WineSale, WinePurchase


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
    """Create wines matching the reference spreadsheets."""
    wines_data = [
        # FEVBRE wines
        {'name': 'SVB NZ Main Divide', 'supplier': 'FEVBRE', 'cost_price': 12.00, 'glasses': 5, 'margin': 70, 'stock': 15},
        {'name': 'Chardonnay Jordan South Africa', 'supplier': 'FEVBRE', 'cost_price': 15.30, 'glasses': 4, 'margin': 70, 'stock': 8},
        {'name': 'Albarino Martin Codax', 'supplier': 'FEVBRE', 'cost_price': 13.00, 'glasses': 5, 'margin': 70, 'stock': 14},
        {'name': 'Esparao Alentejo Reserva', 'supplier': 'FEVBRE', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 15},
        {'name': 'Pouilly Fume Ch. de Tracy', 'supplier': 'FEVBRE', 'cost_price': 23.00, 'glasses': 4, 'margin': 70, 'stock': 4},
        {'name': 'Chablis le Verger', 'supplier': 'FEVBRE', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 6},
        {'name': 'CDR Le Caillou White', 'supplier': 'FEVBRE', 'cost_price': 10.50, 'glasses': 5, 'margin': 70, 'stock': 12},
        {'name': 'Argentinian Malbec', 'supplier': 'FEVBRE', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 10},
        {'name': 'Pinot Noir NZ Main Divide', 'supplier': 'FEVBRE', 'cost_price': 14.50, 'glasses': 4, 'margin': 70, 'stock': 7},
        {'name': 'Meerkat', 'supplier': 'FEVBRE', 'cost_price': 8.50, 'glasses': 5, 'margin': 70, 'stock': 20},
        {'name': 'Alentejo Esparao RED', 'supplier': 'FEVBRE', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 9},
        {'name': "Nero d'Avola", 'supplier': 'FEVBRE', 'cost_price': 9.80, 'glasses': 5, 'margin': 70, 'stock': 11},
        {'name': 'Bourgogne Valmoisine', 'supplier': 'FEVBRE', 'cost_price': 19.00, 'glasses': 4, 'margin': 70, 'stock': 5},
        # CLASSIC DRINKS
        {'name': 'Albarino Terras Gauda', 'supplier': 'CLASSIC DRINKS', 'cost_price': 16.50, 'glasses': 4, 'margin': 70, 'stock': 6},
        {'name': 'Overture', 'supplier': 'CLASSIC DRINKS', 'cost_price': 9.50, 'glasses': 5, 'margin': 70, 'stock': 12},
        {'name': 'Valpolicella Vega Sicilia', 'supplier': 'CLASSIC DRINKS', 'cost_price': 14.00, 'glasses': 4, 'margin': 70, 'stock': 8},
        {'name': 'Clos du Pape', 'supplier': 'CLASSIC DRINKS', 'cost_price': 45.00, 'glasses': 4, 'margin': 70, 'stock': 3},
        {'name': 'Gevrey Chambertin', 'supplier': 'CLASSIC DRINKS', 'cost_price': 38.00, 'glasses': 4, 'margin': 70, 'stock': 2},
        # CAUBET WINES
        {'name': 'Pinot Grigio', 'supplier': 'CAUBET WINES', 'cost_price': 8.50, 'glasses': 5, 'margin': 70, 'stock': 18},
        {'name': 'Muscadet', 'supplier': 'CAUBET WINES', 'cost_price': 9.00, 'glasses': 5, 'margin': 70, 'stock': 12},
        {'name': 'Macon-Peronne', 'supplier': 'CAUBET WINES', 'cost_price': 14.00, 'glasses': 4, 'margin': 70, 'stock': 6},
        {'name': 'Saint-Veran', 'supplier': 'CAUBET WINES', 'cost_price': 17.00, 'glasses': 4, 'margin': 70, 'stock': 5},
        {'name': 'Saint-Aubin Thomas Morey', 'supplier': 'CAUBET WINES', 'cost_price': 25.00, 'glasses': 4, 'margin': 70, 'stock': 3},
        # BARRY & FITZWILLIAM
        {'name': 'Rioja Reserva Beronia', 'supplier': 'BARRY & FITZWILLIAM', 'cost_price': 13.50, 'glasses': 4, 'margin': 70, 'stock': 8},
        {'name': 'Chateau Neuf du Pape Gabriel Meffre', 'supplier': 'BARRY & FITZWILLIAM', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 4},
        {'name': 'Pedro Ximenes Noe', 'supplier': 'BARRY & FITZWILLIAM', 'cost_price': 28.00, 'glasses': 6, 'margin': 70, 'stock': 2},
        # CLASSIC GOURMET
        {'name': 'Pouilly Fuisse', 'supplier': 'CLASSIC GOURMET', 'cost_price': 24.00, 'glasses': 4, 'margin': 70, 'stock': 4},
        {'name': 'Saint-Amour', 'supplier': 'CLASSIC GOURMET', 'cost_price': 18.00, 'glasses': 4, 'margin': 70, 'stock': 5},
        {'name': 'Chateau Cap de Faugeres', 'supplier': 'CLASSIC GOURMET', 'cost_price': 19.00, 'glasses': 4, 'margin': 70, 'stock': 3},
        {'name': 'Saint Emilion Grand Cru', 'supplier': 'CLASSIC GOURMET', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 2},
        # LAROUSSE
        {'name': 'Touraine SVB Vincent La Cour', 'supplier': 'LAROUSSE', 'cost_price': 12.00, 'glasses': 5, 'margin': 70, 'stock': 10},
        {'name': 'Gruner Veltliner Heinz W', 'supplier': 'LAROUSSE', 'cost_price': 13.50, 'glasses': 4, 'margin': 70, 'stock': 7},
        # LE CAVEAU
        {'name': 'Chianti', 'supplier': 'LE CAVEAU', 'cost_price': 11.00, 'glasses': 5, 'margin': 70, 'stock': 14},
        {'name': 'Corbieres', 'supplier': 'LE CAVEAU', 'cost_price': 9.50, 'glasses': 5, 'margin': 70, 'stock': 10},
        {'name': 'Cahors', 'supplier': 'LE CAVEAU', 'cost_price': 10.00, 'glasses': 5, 'margin': 70, 'stock': 8},
        {'name': 'Cotes de Nuits Village', 'supplier': 'LE CAVEAU', 'cost_price': 22.00, 'glasses': 4, 'margin': 70, 'stock': 3},
        {'name': 'Nuits-Saint-Georges', 'supplier': 'LE CAVEAU', 'cost_price': 32.00, 'glasses': 4, 'margin': 70, 'stock': 2},
        # CASSIDY WINES
        {'name': 'Shiraz McRae Wood', 'supplier': 'CASSIDY WINES', 'cost_price': 16.00, 'glasses': 4, 'margin': 70, 'stock': 6},
        {'name': 'Ribera Del Duero Emilio Moro', 'supplier': 'CASSIDY WINES', 'cost_price': 18.00, 'glasses': 4, 'margin': 70, 'stock': 5},
        {'name': 'ROSE Cotes de Provence', 'supplier': 'CASSIDY WINES', 'cost_price': 14.50, 'glasses': 4, 'margin': 70, 'stock': 7},
        # TINDAL
        {'name': 'SVB Pech des Cades', 'supplier': 'TINDAL', 'cost_price': 7.95, 'glasses': 5, 'margin': 70, 'stock': 35},
        {'name': 'Antinori', 'supplier': 'TINDAL', 'cost_price': 15.00, 'glasses': 4, 'margin': 70, 'stock': 7},
        # EDWARD DILLON
        {'name': 'Champagne Ruinart BLC de BLC', 'supplier': 'EDWARD DILLON', 'cost_price': 55.00, 'glasses': 5, 'margin': 65, 'stock': 3},
        {'name': 'Champagne Dom Perignon', 'supplier': 'EDWARD DILLON', 'cost_price': 120.00, 'glasses': 5, 'margin': 60, 'stock': 2},
        {'name': 'Champagne Veuve Clicquot Rose', 'supplier': 'EDWARD DILLON', 'cost_price': 52.00, 'glasses': 5, 'margin': 65, 'stock': 4},
        # NOMAD
        {'name': 'White Sancerre', 'supplier': 'NOMAD', 'cost_price': 18.00, 'glasses': 4, 'margin': 70, 'stock': 6},
        {'name': 'Bourgogne Chardonnay Closel', 'supplier': 'NOMAD', 'cost_price': 16.00, 'glasses': 4, 'margin': 70, 'stock': 5},
        {'name': 'Chassagne Montrachet', 'supplier': 'NOMAD', 'cost_price': 35.00, 'glasses': 4, 'margin': 70, 'stock': 2},
        # WINE MASON
        {'name': 'German Riesling Wagner Stempel', 'supplier': 'WINE MASON', 'cost_price': 15.00, 'glasses': 4, 'margin': 70, 'stock': 6},
        {'name': 'Fleurie', 'supplier': 'WINE MASON', 'cost_price': 16.00, 'glasses': 4, 'margin': 70, 'stock': 5},
    ]

    created = 0
    for w_data in wines_data:
        if not Wine.query.filter_by(name=w_data['name']).first():
            wine = Wine(
                name=w_data['name'],
                supplier_id=supplier_map.get(w_data['supplier']),
                cost_price=w_data['cost_price'],
                glasses_per_bottle=w_data['glasses'],
                target_margin_percent=w_data['margin'],
                minimum_stock_threshold=3,
                current_stock_qty=w_data['stock'],
            )
            wine.calculate_prices()
            db.session.add(wine)
            created += 1

    db.session.commit()
    print(f"✓ Created {created} wines")


def seed_sales():
    """Create sample sales data for the current week and month."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    wines = Wine.query.all()

    if WineSale.query.count() > 0:
        print("✓ Sales data already exists, skipping")
        return

    # Generate sales for the past 30 days
    for day_offset in range(30):
        sale_date = today - timedelta(days=day_offset)
        # Random number of wines sold each day (5-15)
        num_sales = random.randint(5, 15)
        for _ in range(num_sales):
            wine = random.choice(wines)
            qty = random.randint(1, 3)
            sale = WineSale(
                wine_id=wine.id,
                date=sale_date,
                quantity_sold=qty
            )
            db.session.add(sale)

    db.session.commit()
    print(f"✓ Created sample sales data for last 30 days")


def seed_purchases():
    """Create sample purchase data including some pending invoices."""
    if WinePurchase.query.count() > 0:
        print("✓ Purchase data already exists, skipping")
        return

    today = date.today()
    wines = Wine.query.all()

    # Create some cleared purchases (past)
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
            db.session.add(purchase)

    # Create some pending purchases (recent)
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
    print(f"✓ Created sample purchase data with pending invoices")


def run_seed():
    """Run all seeders."""
    with app.app_context():
        print("\n🍷 Seeding Wine Stock Database...\n")
        supplier_map = seed_suppliers()
        seed_wines(supplier_map)
        seed_sales()
        seed_purchases()
        print("\n✅ Database seeded successfully!\n")


if __name__ == '__main__':
    init_db()
    run_seed()
