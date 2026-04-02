"""
Wine Stock Management System — Database Models
SQLAlchemy models for Supplier, Wine, WineSale, WinePurchase.
"""

from datetime import datetime, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Simple admin user for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'


class Supplier(db.Model):
    """Wine supplier with contact and ordering details."""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    contact_email = db.Column(db.String(200), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_whatsapp = db.Column(db.String(50), nullable=True)
    order_method = db.Column(db.String(20), nullable=False, default='email')
    # order_method: 'email', 'phone', 'whatsapp'
    delivery_cutoff_time = db.Column(db.String(10), nullable=True)  # e.g. "14:00"
    typical_delivery_days = db.Column(db.Integer, nullable=True, default=1)
    minimum_order_note = db.Column(db.String(200), nullable=True)  # e.g. "min 36 bottles"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    wines = db.relationship('Wine', backref='supplier', lazy='dynamic')

    def __repr__(self):
        return f'<Supplier {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'contact_whatsapp': self.contact_whatsapp,
            'order_method': self.order_method,
            'delivery_cutoff_time': self.delivery_cutoff_time,
            'typical_delivery_days': self.typical_delivery_days,
            'minimum_order_note': self.minimum_order_note,
        }


class Wine(db.Model):
    """Wine product with pricing, stock, and supplier link."""
    __tablename__ = 'wines'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    glasses_per_bottle = db.Column(db.Integer, nullable=False, default=5)
    target_margin_percent = db.Column(db.Float, nullable=False, default=70.0)
    net_vat_price = db.Column(db.Float, nullable=True)  # calculated: cost_price * (1 + margin)
    retail_price = db.Column(db.Float, nullable=True)    # net_vat_price * 1.23 (23% VAT)
    minimum_stock_threshold = db.Column(db.Integer, nullable=False, default=3)
    current_stock_qty = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sales = db.relationship('WineSale', backref='wine', lazy='dynamic')
    purchases = db.relationship('WinePurchase', backref='wine', lazy='dynamic')

    @property
    def stock_value(self):
        """Total value of current stock at cost price."""
        return round(self.current_stock_qty * self.cost_price, 2)

    @property
    def is_below_threshold(self):
        """Check if stock is below the minimum threshold."""
        return self.current_stock_qty < self.minimum_stock_threshold

    def calculate_prices(self):
        """Recalculate net VAT and retail prices from cost and margin."""
        if self.cost_price and self.target_margin_percent:
            margin_multiplier = 1 / (1 - (self.target_margin_percent / 100))
            self.net_vat_price = round(self.cost_price * margin_multiplier, 2)
            self.retail_price = round(self.net_vat_price * 1.23, 2)  # 23% VAT

    def __repr__(self):
        return f'<Wine {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else 'N/A',
            'cost_price': self.cost_price,
            'glasses_per_bottle': self.glasses_per_bottle,
            'target_margin_percent': self.target_margin_percent,
            'net_vat_price': self.net_vat_price,
            'retail_price': self.retail_price,
            'minimum_stock_threshold': self.minimum_stock_threshold,
            'current_stock_qty': self.current_stock_qty,
            'stock_value': self.stock_value,
            'is_below_threshold': self.is_below_threshold,
        }


class WineSale(db.Model):
    """Record of wine sold on a given date."""
    __tablename__ = 'wine_sales'

    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    quantity_sold = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WineSale {self.wine.name if self.wine else "?"} x{self.quantity_sold} on {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'wine_id': self.wine_id,
            'wine_name': self.wine.name if self.wine else 'N/A',
            'date': self.date.isoformat(),
            'quantity_sold': self.quantity_sold,
        }


class WinePurchase(db.Model):
    """
    Record of wine purchased / ordered from supplier.

    CRITICAL RULE: Purchased wine is tracked here. It shows as a "Plus"
    in the weekly sales/orders view, but it MUST NOT be added to
    Wine.current_stock_qty until is_invoice_cleared is True.
    """
    __tablename__ = 'wine_purchases'

    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'), nullable=False)
    date_ordered = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    quantity_ordered = db.Column(db.Integer, nullable=False, default=1)
    is_invoice_cleared = db.Column(db.Boolean, nullable=False, default=False)
    date_cleared = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        status = "CLEARED" if self.is_invoice_cleared else "PENDING"
        return f'<WinePurchase {self.wine.name if self.wine else "?"} x{self.quantity_ordered} [{status}]>'

    def to_dict(self):
        return {
            'id': self.id,
            'wine_id': self.wine_id,
            'wine_name': self.wine.name if self.wine else 'N/A',
            'date_ordered': self.date_ordered.isoformat(),
            'quantity_ordered': self.quantity_ordered,
            'is_invoice_cleared': self.is_invoice_cleared,
            'date_cleared': self.date_cleared.isoformat() if self.date_cleared else None,
        }
