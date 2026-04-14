"""
Stock Management System — Database Models
SQLAlchemy models for Wine (Supplier, Wine, WineSale, WinePurchase, WineComp)
and Bar (Spirit, SpiritSale, SpiritPurchase, SubIngredient, CocktailRecipe,
CocktailIngredient, BarSale, BarWaste).
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
    wines_per_box = db.Column(db.Integer, nullable=False, default=6)
    minimum_stock_threshold = db.Column(db.Integer, nullable=False, default=3)
    # Now Float to support fractional bottles (glass sales deduct 1/glasses_per_bottle)
    current_stock_qty = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sales = db.relationship('WineSale', backref='wine', lazy='dynamic')
    purchases = db.relationship('WinePurchase', backref='wine', lazy='dynamic')
    comps = db.relationship('WineComp', backref='wine', lazy='dynamic')

    @property
    def stock_value(self):
        """Total value of current stock at cost price."""
        return round(self.current_stock_qty * self.cost_price, 2)

    @property
    def is_below_threshold(self):
        """Check if stock is below the minimum threshold."""
        return self.current_stock_qty < self.minimum_stock_threshold

    @property
    def stock_display(self):
        """
        Human-readable fractional stock.
        E.g. 8.5 → '8.5', 5.0 → '5', 4.75 → '4.75'
        Rounds to 2 decimal places and strips trailing zeros.
        """
        rounded = round(self.current_stock_qty, 2)
        # Format: remove unnecessary trailing zeros
        if rounded == int(rounded):
            return str(int(rounded))
        # Show up to 2 dp, strip trailing zero
        return f'{rounded:.2f}'.rstrip('0')

    def glasses_available(self):
        """Total glasses remaining across all partial and full bottles."""
        return round(self.current_stock_qty * self.glasses_per_bottle, 2)

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
            'wines_per_box': self.wines_per_box,
            'net_vat_price': self.net_vat_price,
            'retail_price': self.retail_price,
            'minimum_stock_threshold': self.minimum_stock_threshold,
            'current_stock_qty': round(self.current_stock_qty, 4),
            'stock_display': self.stock_display,
            'stock_value': self.stock_value,
            'is_below_threshold': self.is_below_threshold,
        }


class WineSale(db.Model):
    """Record of wine sold on a given date (glass or bottle)."""
    __tablename__ = 'wine_sales'

    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    quantity_sold = db.Column(db.Float, nullable=False, default=1)  # Float to support fractional pairing quantities
    # 'glass', 'bottle', or 'pairing' — determines stock deduction per unit
    sale_type = db.Column(db.String(10), nullable=False, default='bottle')
    # Groups multiple WineSale rows that belong to a single Pairing event
    pairing_group_id = db.Column(db.String(36), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WineSale {self.wine.name if self.wine else "?"} x{self.quantity_sold} {self.sale_type}(s) on {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'wine_id': self.wine_id,
            'wine_name': self.wine.name if self.wine else 'N/A',
            'date': self.date.isoformat(),
            'quantity_sold': self.quantity_sold,
            'sale_type': self.sale_type,
            'pairing_group_id': self.pairing_group_id,
        }


class CorkedWine(db.Model):
    """
    Record of a corked (spoiled/unusable) wine bottle.
    DEDUCTS from Wine.current_stock_qty immediately.
    Shown in red on the supplier card.
    """
    __tablename__ = 'corked_wines'

    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    image_path = db.Column(db.Text, nullable=True)       # optional photo (base64 string)
    image_original = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    wine = db.relationship('Wine', backref='corked_records', foreign_keys=[wine_id])
    supplier = db.relationship('Supplier', backref='corked_wines', foreign_keys=[supplier_id])

    def __repr__(self):
        return f'<CorkedWine {self.wine.name if self.wine else "?"} x{self.quantity} on {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'wine_id': self.wine_id,
            'wine_name': self.wine.name if self.wine else 'N/A',
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else 'N/A',
            'quantity': self.quantity,
            'date': self.date.isoformat(),
            'image_path': self.image_path,
            'notes': self.notes,
        }


class WineComp(db.Model):
    """
    Record of complimentary (free) drinks given out.
    IMPORTANT: Comps do NOT affect Wine.current_stock_qty.
    They are recorded purely for reporting purposes.
    """
    __tablename__ = 'wine_comps'

    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    # 'glass' or 'bottle'
    sale_type = db.Column(db.String(10), nullable=False, default='glass')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WineComp {self.wine.name if self.wine else "?"} x{self.quantity} {self.sale_type}(s) COMP on {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'wine_id': self.wine_id,
            'wine_name': self.wine.name if self.wine else 'N/A',
            'date': self.date.isoformat(),
            'quantity': self.quantity,
            'sale_type': self.sale_type,
        }


class WinePurchase(db.Model):
    """
    Record of wine purchased / ordered from supplier.
    Purchased wine is added directly to Wine.current_stock_qty when recorded.
    """
    __tablename__ = 'wine_purchases'

    id = db.Column(db.Integer, primary_key=True)
    wine_id = db.Column(db.Integer, db.ForeignKey('wines.id'), nullable=False)
    date_ordered = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    quantity_ordered = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WinePurchase {self.wine.name if self.wine else "?"} x{self.quantity_ordered}>'

    def to_dict(self):
        return {
            'id': self.id,
            'wine_id': self.wine_id,
            'wine_name': self.wine.name if self.wine else 'N/A',
            'date_ordered': self.date_ordered.isoformat(),
            'quantity_ordered': self.quantity_ordered,
        }


# ===========================================================================
# BAR MODELS
# ===========================================================================

class Spirit(db.Model):
    """
    A bottle of spirit (Vodka, Tequila, Rum, Gin, Whiskey, Liqueur, etc.)
    Pricing: cost_price → cost_per_measure → shot_retail_price (editable).
    Stock tracked in measures (1 bottle = bottle_size_ml / measure_ml measures).
    """
    __tablename__ = 'spirits'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)           # e.g. "Smirnoff Red Label"
    brand = db.Column(db.String(120), nullable=True)           # e.g. "Smirnoff"
    category = db.Column(db.String(60), nullable=False, default='vodka')
    # categories: vodka, tequila, rum, gin, whiskey, brandy, liqueur, other
    bottle_size_ml = db.Column(db.Float, nullable=False, default=700.0)   # ml per bottle
    measure_ml = db.Column(db.Float, nullable=False, default=25.0)        # ml per measure/shot
    cost_price = db.Column(db.Float, nullable=False, default=0.0)          # € per bottle
    target_margin_percent = db.Column(db.Float, nullable=False, default=70.0)
    shot_retail_price = db.Column(db.Float, nullable=True)               # € per shot (editable)
    cocktail_price_per_measure = db.Column(db.Float, nullable=True)      # € per measure in cocktail
    minimum_stock_bottles = db.Column(db.Integer, nullable=False, default=1)
    # Current stock in MEASURES (float, deducted per sale)
    current_measures = db.Column(db.Float, nullable=False, default=0.0)
    supplier_name = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sales = db.relationship('SpiritSale', backref='spirit', lazy='dynamic')
    purchases = db.relationship('SpiritPurchase', backref='spirit', lazy='dynamic')
    wastes = db.relationship('BarWaste', backref='spirit', lazy='dynamic')
    cocktail_ingredients = db.relationship('CocktailIngredient', backref='spirit', lazy='dynamic')

    # ---- Computed Properties ----
    @property
    def measures_per_bottle(self):
        """How many measures per full bottle."""
        if self.measure_ml and self.measure_ml > 0:
            return round(self.bottle_size_ml / self.measure_ml, 4)
        return 1.0

    @property
    def cost_per_measure(self):
        """Cost price per single measure."""
        mpb = self.measures_per_bottle
        if mpb > 0:
            return round(self.cost_price / mpb, 4)
        return 0.0

    @property
    def bottles_remaining(self):
        """Current stock expressed in full bottles (float)."""
        mpb = self.measures_per_bottle
        if mpb > 0:
            return round(self.current_measures / mpb, 4)
        return 0.0

    @property
    def stock_value(self):
        """Total value of current stock at cost price."""
        return round(self.bottles_remaining * self.cost_price, 2)

    @property
    def is_below_threshold(self):
        return self.bottles_remaining < self.minimum_stock_bottles

    @property
    def fill_percent(self):
        """0-100 fill percentage of current partial bottle."""
        mpb = self.measures_per_bottle
        if mpb <= 0:
            return 0
        partial = self.current_measures % mpb
        if partial == 0 and self.current_measures > 0:
            partial = mpb
        return round((partial / mpb) * 100, 1)

    def calculate_shot_price(self):
        """Auto-calculate shot retail price from cost and target margin."""
        if self.cost_price and self.target_margin_percent:
            margin_mult = 1 / (1 - self.target_margin_percent / 100)
            self.shot_retail_price = round(self.cost_per_measure * margin_mult * 1.23, 2)
            self.cocktail_price_per_measure = round(self.cost_per_measure * margin_mult, 2)

    def __repr__(self):
        return f'<Spirit {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'category': self.category,
            'bottle_size_ml': self.bottle_size_ml,
            'measure_ml': self.measure_ml,
            'cost_price': self.cost_price,
            'target_margin_percent': self.target_margin_percent,
            'shot_retail_price': self.shot_retail_price,
            'cocktail_price_per_measure': self.cocktail_price_per_measure,
            'minimum_stock_bottles': self.minimum_stock_bottles,
            'current_measures': round(self.current_measures, 4),
            'measures_per_bottle': self.measures_per_bottle,
            'cost_per_measure': self.cost_per_measure,
            'bottles_remaining': self.bottles_remaining,
            'stock_value': self.stock_value,
            'fill_percent': self.fill_percent,
            'is_below_threshold': self.is_below_threshold,
            'supplier_name': self.supplier_name,
            'notes': self.notes,
        }


class SpiritSale(db.Model):
    """Individual shot or spirit-pour sale. Deducts measures from Spirit.current_measures."""
    __tablename__ = 'spirit_sales'

    id = db.Column(db.Integer, primary_key=True)
    spirit_id = db.Column(db.Integer, db.ForeignKey('spirits.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    measures_sold = db.Column(db.Float, nullable=False, default=1.0)  # number of measures
    sale_type = db.Column(db.String(20), nullable=False, default='shot')  # 'shot' or 'cocktail_component'
    unit_price = db.Column(db.Float, nullable=True)   # price charged per measure at time of sale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'spirit_id': self.spirit_id,
            'spirit_name': self.spirit.name if self.spirit else 'N/A',
            'date': self.date.isoformat(),
            'measures_sold': self.measures_sold,
            'sale_type': self.sale_type,
            'unit_price': self.unit_price,
        }


class SpiritPurchase(db.Model):
    """
    Purchase order for spirit bottles.
    Stock NOT added until invoice is cleared (same pattern as WinePurchase).
    """
    __tablename__ = 'spirit_purchases'

    id = db.Column(db.Integer, primary_key=True)
    spirit_id = db.Column(db.Integer, db.ForeignKey('spirits.id'), nullable=False)
    date_ordered = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    bottles_ordered = db.Column(db.Integer, nullable=False, default=1)
    cost_per_bottle = db.Column(db.Float, nullable=True)     # actual invoice cost (may differ)
    is_invoice_cleared = db.Column(db.Boolean, nullable=False, default=False)
    date_cleared = db.Column(db.DateTime, nullable=True)
    invoice_image_path = db.Column(db.Text, nullable=True)
    invoice_image_original = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'spirit_id': self.spirit_id,
            'spirit_name': self.spirit.name if self.spirit else 'N/A',
            'date_ordered': self.date_ordered.isoformat(),
            'bottles_ordered': self.bottles_ordered,
            'cost_per_bottle': self.cost_per_bottle,
            'is_invoice_cleared': self.is_invoice_cleared,
            'date_cleared': self.date_cleared.isoformat() if self.date_cleared else None,
            'invoice_image_path': self.invoice_image_path,
            'invoice_image_original': self.invoice_image_original,
            'notes': self.notes,
        }


class SubIngredient(db.Model):
    """
    Non-spirit bar ingredient: sugar, lime juice, syrups, garnishes, juices, etc.
    Stock tracked in 'units' (can be ml, pieces, kg — user defines).
    """
    __tablename__ = 'sub_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)        # e.g. "Lime Juice"
    category = db.Column(db.String(60), nullable=False, default='mixer')
    # categories: mixer, fruit, syrup, garnish, juice, dairy, other
    unit = db.Column(db.String(30), nullable=False, default='ml')  # ml, pieces, g, cl
    cost_per_unit = db.Column(db.Float, nullable=False, default=0.0)  # € per unit
    current_stock = db.Column(db.Float, nullable=False, default=0.0)
    minimum_stock = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    cocktail_ingredients = db.relationship('CocktailIngredient', backref='sub_ingredient', lazy='dynamic')

    @property
    def stock_value(self):
        return round(self.current_stock * self.cost_per_unit, 2)

    @property
    def is_below_threshold(self):
        return self.current_stock < self.minimum_stock

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'unit': self.unit,
            'cost_per_unit': self.cost_per_unit,
            'current_stock': self.current_stock,
            'minimum_stock': self.minimum_stock,
            'stock_value': self.stock_value,
            'is_below_threshold': self.is_below_threshold,
            'notes': self.notes,
        }


class CocktailRecipe(db.Model):
    """
    A cocktail recipe record: name, description, sell price, and list of ingredients.
    Cost is calculated dynamically from ingredients.
    """
    __tablename__ = 'cocktail_recipes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(400), nullable=True)
    sell_price = db.Column(db.Float, nullable=False, default=0.0)  # € retail price
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    ingredients = db.relationship('CocktailIngredient', backref='recipe',
                                   lazy='selectin', cascade='all, delete-orphan')
    sales = db.relationship('BarSale', backref='cocktail', lazy='dynamic')

    @property
    def cost_price(self):
        """Dynamic cost: sum of all ingredient costs."""
        total = 0.0
        for ing in self.ingredients:
            if ing.spirit_id and ing.spirit:
                total += ing.spirit.cost_per_measure * ing.quantity
            elif ing.sub_ingredient_id and ing.sub_ingredient:
                total += ing.sub_ingredient.cost_per_unit * ing.quantity
        return round(total, 4)

    @property
    def margin_percent(self):
        cost = self.cost_price
        if cost > 0 and self.sell_price > 0:
            return round((1 - cost / self.sell_price) * 100, 1)
        return 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sell_price': self.sell_price,
            'cost_price': self.cost_price,
            'margin_percent': self.margin_percent,
            'is_active': self.is_active,
            'ingredients': [i.to_dict() for i in self.ingredients],
        }


class CocktailIngredient(db.Model):
    """
    A single ingredient line in a CocktailRecipe.
    Either spirit_id OR sub_ingredient_id is set (not both).
    quantity = measures (for spirit) or units (for sub-ingredient).
    """
    __tablename__ = 'cocktail_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('cocktail_recipes.id'), nullable=False)
    # One of these two:
    spirit_id = db.Column(db.Integer, db.ForeignKey('spirits.id'), nullable=True)
    sub_ingredient_id = db.Column(db.Integer, db.ForeignKey('sub_ingredients.id'), nullable=True)
    quantity = db.Column(db.Float, nullable=False, default=1.0)  # measures or units
    notes = db.Column(db.String(100), nullable=True)            # e.g. "freshly squeezed"

    def to_dict(self):
        if self.spirit_id and self.spirit:
            return {
                'id': self.id,
                'type': 'spirit',
                'spirit_id': self.spirit_id,
                'name': self.spirit.name,
                'category': self.spirit.category,
                'quantity': self.quantity,
                'unit': f"{self.spirit.measure_ml}ml measures",
                'cost': round(self.spirit.cost_per_measure * self.quantity, 4),
                'notes': self.notes,
            }
        elif self.sub_ingredient_id and self.sub_ingredient:
            return {
                'id': self.id,
                'type': 'sub_ingredient',
                'sub_ingredient_id': self.sub_ingredient_id,
                'name': self.sub_ingredient.name,
                'category': self.sub_ingredient.category,
                'quantity': self.quantity,
                'unit': self.sub_ingredient.unit,
                'cost': round(self.sub_ingredient.cost_per_unit * self.quantity, 4),
                'notes': self.notes,
            }
        return {'id': self.id, 'type': 'unknown', 'quantity': self.quantity}


class BarSale(db.Model):
    """
    A bar sale event: either a cocktail (by recipe) or a shot (by spirit).
    When recorded, measures are deducted from spirits and sub-ingredient stock is also reduced.
    """
    __tablename__ = 'bar_sales'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    sale_type = db.Column(db.String(20), nullable=False, default='cocktail')  # 'cocktail' or 'shot'
    # For cocktail:
    cocktail_id = db.Column(db.Integer, db.ForeignKey('cocktail_recipes.id'), nullable=True)
    # For shot:
    spirit_id = db.Column(db.Integer, db.ForeignKey('spirits.id'), nullable=True)
    spirit = db.relationship('Spirit', foreign_keys=[spirit_id])
    quantity = db.Column(db.Integer, nullable=False, default=1)    # number of cocktails/shots
    unit_price = db.Column(db.Float, nullable=True)                # price at time of sale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        name = 'N/A'
        if self.sale_type == 'cocktail' and self.cocktail:
            name = self.cocktail.name
        elif self.sale_type == 'shot' and self.spirit:
            name = self.spirit.name
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'sale_type': self.sale_type,
            'cocktail_id': self.cocktail_id,
            'spirit_id': self.spirit_id,
            'name': name,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total': round((self.unit_price or 0) * self.quantity, 2),
        }


class BarWaste(db.Model):
    """
    Waste or spillage record — either for a spirit (measure count) or sub-ingredient (units).
    Does NOT deduct stock (stock was already consumed); only tracks for reporting.
    """
    __tablename__ = 'bar_wastes'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    waste_type = db.Column(db.String(20), nullable=False, default='spirit')  # 'spirit' or 'sub_ingredient'
    spirit_id = db.Column(db.Integer, db.ForeignKey('spirits.id'), nullable=True)
    sub_ingredient_id = db.Column(db.Integer, db.ForeignKey('sub_ingredients.id'), nullable=True)
    sub_ingredient = db.relationship('SubIngredient', foreign_keys=[sub_ingredient_id])
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    reason = db.Column(db.String(200), nullable=True)
    cost_impact = db.Column(db.Float, nullable=True)  # auto-calculated at recording time
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        name = 'N/A'
        unit = ''
        if self.waste_type == 'spirit' and self.spirit:
            name = self.spirit.name
            unit = f"{self.spirit.measure_ml}ml measures"
        elif self.waste_type == 'sub_ingredient' and self.sub_ingredient:
            name = self.sub_ingredient.name
            unit = self.sub_ingredient.unit
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'waste_type': self.waste_type,
            'name': name,
            'quantity': self.quantity,
            'unit': unit,
            'reason': self.reason,
            'cost_impact': self.cost_impact,
        }
