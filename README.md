# Wine Stock Management System (Stock-Tech)

A comprehensive, tablet-optimized web application for managing wine supplies, tracking inventory, running analytics, and generating sales metrics. Built with a deeply integrated, modern glassmorphism aesthetic.

## 🌟 Key Features

* **Visual Stock Management**: 
    A quick-glance CSS grid indicating wine availabilities color-coded by scarcity levels (Red for critical, Amber for low, Green for well-stocked).
* **Weekly Sales Tracking**:
    An interactive, horizontal scrollable board tracking day-by-day wine sales and orders that expand upon interaction.
* **Wine Analytics KPIs**:
    Real-time computations of business metric KPIs including Monthly Profit, Total Stock Value, Monthly Revenue, Top Performing Wine, Highest Margin Wine, and Low Stock Alerts.
* **Smart Alerting & Invoicing**:
    A robust system that identifies threshold-dropping inventory, alerts the supplier on cutoffs, and delays immediate stock aggregation on order entry until standard invoices clear safely.
* **Detailed Supplier Management**:
    A centralized directory equipped to organize primary contacts, delivery cutoffs, typical transit days, automated minimum order constraints, and one-click contact capabilities (Email, Phone, WhatsApp).
* **Responsive Layouts**:
    A fluid UI with a modern, dark-mode glassmorphism theme and 44px tap targets suited for smooth navigation and fast action recording on mobile & tablet environments.

---

## 💻 Technology Stack

* **Backend Foundation**:
  * [Python](https://www.python.org/) 3.12+
  * [Flask](https://flask.palletsprojects.com/en/3.0.x/) 3.1.0 
  * [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/) for database operations via ORM.
  * [Flask-Login](https://flask-login.readthedocs.io/en/latest/) for straightforward admin authentication.
  * [SQLite](https://sqlite.org/) for local, file-based database structure.
* **Frontend & Aesthetic Design**:
  * Vanilla JavaScript (`ES6`) designed for asynchronous interaction with API routes.
  * Custom Vanilla CSS incorporating a **Dark Glassmorphism** visual hierarchy.
  * Integration of Bootstrap 5 grid principles supplemented by Google Fonts (`Inter`, `Outfit`) and FontAwesome 6 icon kits.

---

## 🚀 Setup & Installation

### 1. Clone & Enter the Working Directory

```bash
cd "/home/roma/Antigravity Projects/Stock-Tech"
```

*(Assuming local placement for user workspace, or `git clone` alternative source path)*

### 2. Install the Required Dependencies

As outlined in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Initialize & Pre-Populate the Database

A script is provided to automatically create your local SQLite database structure (`wine_stock.db`) and seed it with dummy/baseline data (15 Suppliers, 50 Wines, 30 days of mock sales activity).

```bash
python3 seed_data.py
```

### 4. Start the Development Server

```bash
python3 app.py
```
The Flask server bounds by default to `http://127.0.0.1:5000`.

---

## 🔒 Authentication

This system utilizes single-user backend security configured in the database seed step.

* **URL Path**: `http://127.0.0.1:5000` (Defaults redirection to the login endpoint).
* **Username**: `Admin`
* **Password**: `123`

---

## 📂 Project Structure

```text
Stock-Tech/
├── app.py                     # Main Flask routing, application config, REST APIs
├── models.py                  # SQLAlchemy entities (User, Supplier, Wine, WineSale, WinePurchase)
├── seed_data.py               # Test-data generator logic & mock values
├── requirements.txt           # Library dependencies module versions
├── wine_stock.db              # SQLite Database payload (created via seed_data.py)
├── static/
│   ├── css/
│   │   └── wine_stock.css     # App aesthetic, structural glassmorphism behaviors
│   └── js/
│       └── wine_stock.js      # Front-end API actions, element states, and logic flow
└── templates/
    ├── base.html              # Shell layout frame & structural skeleton nav inclusion
    ├── login.html             # Administrative initial entrance mechanism
    └── wine_stock.html        # Centralized dashboard view templates containing all 6 modules
```

---

## 📱 Navigation Components

1. **Record Items**: Action paths designated into `Record Sale`, `Record Purchase`, `Add Wine`, or `Add Supplier` forms instantiated via custom animated modals.
2. **Weekly Performance Module**: Expandable tracking summaries.
3. **Database Grid**: Injections of all local warehouse variants with sorting arrays.
4. **Analysis Row**: Macro level calculations (Revenue flow, Low-quantity dependencies).
5. **Directory Roster**: Supplier index references.