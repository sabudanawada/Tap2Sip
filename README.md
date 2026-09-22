# Tap2Sip

Tap2Sip is a Flask + SQLite smart self-service beverage kiosk prototype.

## Current menu

### Hot Coffee
- Espresso
- Cappuccino
- Latte
- Americano
- Mocha

### Tea
- Masala Tea
- Ginger Tea
- Green Tea
- Lemon Tea
- Elaichi Tea

### Cold Coffee
- Classic Cold Coffee
- Chocolate Cold Coffee
- Iced Mocha
- Vanilla Cold Coffee

### Snacks
- Chocolate Chip Cookie
- Butter Cookie
- Oatmeal Cookie
- Chocolate Biscuit
- Cream Biscuit

The old **Cold Coffee with Ice Cream** item has been removed.

## Product images

Local product photography is included in `static/img/products/` and is shown on the menu, customization page, cart, receipt, popular-items section, and admin product page.

## Run

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

Admin: http://127.0.0.1:5000/admin/login

Demo admin credentials:
- Username: `admin`
- Password: `admin123`

The SQLite database is created automatically on first run.
