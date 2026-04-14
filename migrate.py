import os
from sqlalchemy import create_engine, text
from app import app, db
from models import Wine, WinePurchase

def run_migration():
    print("Starting migration...")
    with app.app_context():
        # Step 1: Process pending purchases
        pending_purchases = WinePurchase.query.filter_by(is_invoice_cleared=False).all()
        processed_count = 0
        for purchase in pending_purchases:
            if purchase.wine:
                print(f"Adding {purchase.quantity_ordered} bottles to {purchase.wine.name} from pending invoice #{purchase.id}")
                purchase.wine.current_stock_qty += purchase.quantity_ordered
                processed_count += 1
        
        db.session.commit()
        print(f"Processed {processed_count} pending invoices into stock.")
        
        # Step 2: Add wines_per_box to wines table
        engine = db.engine
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE wines ADD COLUMN wines_per_box INTEGER NOT NULL DEFAULT 6"))
                conn.commit()
                print("Added wines_per_box column to wines table.")
            except Exception as e:
                print(f"wines_per_box column might already exist or error: {e}")

            # Step 3: Remove invoice columns from wine_purchases
            # SQLite >= 3.35 supports DROP COLUMN
            columns_to_drop = [
                'is_invoice_cleared',
                'date_cleared',
                'invoice_image_path',
                'invoice_image_original'
            ]
            for col in columns_to_drop:
                try:
                    conn.execute(text(f"ALTER TABLE wine_purchases DROP COLUMN {col}"))
                    conn.commit()
                    print(f"Dropped column {col} from wine_purchases.")
                except Exception as e:
                    print(f"Could not drop column {col} (might not exist or unsupported in this sqlite ver): {e}")

    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
