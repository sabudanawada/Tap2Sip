from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
import sqlite3, os, random, string
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import qrcode
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tap2sip.db")

app = Flask(__name__)
app.secret_key = "tap2sip-demo-secret-change-in-production"

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin'
    );
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        emoji TEXT DEFAULT '☕',
        available INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        total REAL NOT NULL,
        discount REAL DEFAULT 0,
        tax REAL DEFAULT 0,
        payment_method TEXT,
        transaction_id TEXT,
        status TEXT DEFAULT 'Confirmed',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        customization TEXT,
        price REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );
    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient TEXT UNIQUE NOT NULL,
        quantity REAL NOT NULL,
        minimum_quantity REAL NOT NULL,
        unit TEXT DEFAULT 'units'
    );
    CREATE TABLE IF NOT EXISTS coupons(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        discount_type TEXT NOT NULL,
        discount_value REAL NOT NULL,
        active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT,
        rating INTEGER,
        drink_rating INTEGER,
        comment TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS loyalty(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_key TEXT UNIQUE NOT NULL,
        points INTEGER DEFAULT 0
    );
    """)
    admin = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not admin:
        db.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                   ("admin", generate_password_hash("admin123"), "admin"))
    if db.execute("SELECT COUNT(*) c FROM products").fetchone()["c"] == 0:
        products = [
            ("Espresso","coffee","Strong and rich espresso shot",50,"☕"),
            ("Cappuccino","coffee","Rich, creamy and balanced",80,"☕"),
            ("Latte","coffee","Smooth coffee with steamed milk",90,"☕"),
            ("Americano","coffee","Espresso with hot water",70,"☕"),
            ("Mocha","coffee","Coffee with chocolate",100,"☕"),
            ("Masala Tea","tea","Classic Indian spiced tea",30,"🍵"),
            ("Ginger Tea","tea","Warm tea with ginger",35,"🍵"),
            ("Green Tea","tea","Light and refreshing",40,"🍵"),
            ("Lemon Tea","tea","Refreshing lemon-infused tea",35,"🍋"),
            ("Elaichi Tea","tea","Aromatic cardamom tea",40,"🍵"),
            ("Classic Cold Coffee","cold","Chilled creamy coffee",90,"🧊"),
            ("Chocolate Cold Coffee","cold","Cold coffee with chocolate",110,"🍫"),
            ("Iced Mocha","cold","Chilled mocha blend",120,"🧊"),
            ("Vanilla Cold Coffee","cold","Smooth vanilla cold coffee",110,"🍦"),
            ("Chocolate Chip Cookie","snacks","Soft and crunchy chocolate chip cookie",30,"🍪"),
            ("Butter Cookie","snacks","Classic buttery and crisp cookie",25,"🍪"),
            ("Oatmeal Cookie","snacks","Wholesome oatmeal cookie",30,"🍪"),
            ("Chocolate Biscuit","snacks","Rich and crunchy chocolate biscuit",20,"🍫"),
            ("Cream Biscuit","snacks","Sweet biscuit with creamy filling",20,"🍪"),
        ]
        db.executemany("INSERT INTO products(name,category,description,price,emoji) VALUES(?,?,?,?,?)", products)
    # Keep an existing local database in sync with the current Tap2Sip menu.
    db.execute("DELETE FROM products WHERE name=?", ("Cold Coffee with Ice Cream",))
    snack_products = [
        ("Chocolate Chip Cookie","snacks","Soft and crunchy chocolate chip cookie",30,"🍪"),
        ("Butter Cookie","snacks","Classic buttery and crisp cookie",25,"🍪"),
        ("Oatmeal Cookie","snacks","Wholesome oatmeal cookie",30,"🍪"),
        ("Chocolate Biscuit","snacks","Rich and crunchy chocolate biscuit",20,"🍫"),
        ("Cream Biscuit","snacks","Sweet biscuit with creamy filling",20,"🍪"),
    ]
    for snack in snack_products:
        exists = db.execute("SELECT id FROM products WHERE name=?", (snack[0],)).fetchone()
        if not exists:
            db.execute("INSERT INTO products(name,category,description,price,emoji) VALUES(?,?,?,?,?)", snack)
    if db.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"] == 0:
        inv = [
            ("Coffee Beans",80,20,"%"),
            ("Tea Powder",60,15,"%"),
            ("Milk",40,10,"%"),
            ("Sugar",70,15,"%"),
            ("Chocolate",30,10,"%"),
            ("Ice Cream",45,10,"%"),
            ("Whipped Cream",50,10,"%"),
            ("Cups",90,20,"%"),
            ("Lids",85,20,"%")
        ]
        db.executemany("INSERT INTO inventory(ingredient,quantity,minimum_quantity,unit) VALUES(?,?,?,?)", inv)
    if db.execute("SELECT COUNT(*) c FROM coupons").fetchone()["c"] == 0:
        db.executemany("INSERT INTO coupons(code,discount_type,discount_value) VALUES(?,?,?)",
                       [("COFFEE10","percent",10),("SIP20","flat",20)])
    db.commit()
    db.close()

PRODUCT_IMAGES = {
    "Espresso": "espresso.jpg",
    "Cappuccino": "cappuccino.jpg",
    "Latte": "latte.jpg",
    "Americano": "americano.jpg",
    "Mocha": "mocha.jpg",
    "Masala Tea": "masala_tea.jpg",
    "Ginger Tea": "ginger_tea.jpg",
    "Green Tea": "green_tea.jpg",
    "Lemon Tea": "lemon_tea.jpg",
    "Elaichi Tea": "elaichi_tea.jpg",
    "Classic Cold Coffee": "classic_cold_coffee.jpg",
    "Chocolate Cold Coffee": "chocolate_cold_coffee.jpg",
    "Iced Mocha": "iced_mocha.jpg",
    "Vanilla Cold Coffee": "vanilla_cold_coffee.jpg",
    "Chocolate Chip Cookie": "chocolate_chip_cookie.jpg",
    "Butter Cookie": "butter_cookie.jpg",
    "Oatmeal Cookie": "oatmeal_cookie.jpg",
    "Chocolate Biscuit": "chocolate_biscuit.jpg",
    "Cream Biscuit": "cream_biscuit.jpg",
}

def product_image(name):
    return PRODUCT_IMAGES.get(name, "placeholder.jpg")

@app.template_global("product_image")
def product_image_url(name):
    return url_for("static", filename="img/products/" + product_image(name))

def get_products():
    return get_db().execute("SELECT * FROM products ORDER BY CASE category WHEN 'coffee' THEN 1 WHEN 'tea' THEN 2 WHEN 'cold' THEN 3 WHEN 'snacks' THEN 4 ELSE 5 END, id").fetchall()

def make_order_number():
    db = get_db()
    last = db.execute("SELECT order_number FROM orders ORDER BY id DESC LIMIT 1").fetchone()
    if not last:
        n = 1001
    else:
        try: n = int(last["order_number"].replace("#","")) + 1
        except: n = random.randint(1000,9999)
    db.close()
    return f"#{n}"

def transaction_id():
    return "TXN" + ''.join(random.choices(string.digits, k=8))

@app.context_processor
def inject_globals():
    return {"cart_count": sum(i.get("quantity",1) for i in session.get("cart", []))}

@app.route("/")
def index():
    db=get_db()
    popular=db.execute("""
      SELECT oi.name, SUM(oi.quantity) qty FROM order_items oi
      GROUP BY oi.name ORDER BY qty DESC LIMIT 3
    """).fetchall()
    db.close()
    return render_template("index.html", popular=popular)

@app.route("/menu")
def menu():
    return render_template("menu.html", products=get_products())

@app.route("/customize/<int:product_id>", methods=["GET","POST"])
def customize(product_id):
    db=get_db()
    product=db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    db.close()
    if not product or not product["available"]:
        flash("That beverage is currently unavailable.", "error")
        return redirect(url_for("menu"))
    if request.method == "POST":
        size=request.form.get("size","Medium")
        sugar=request.form.get("sugar","Normal")
        milk=request.form.get("milk","Regular")
        temperature=request.form.get("temperature","Hot")
        ice=request.form.get("ice","Normal Ice")
        addons=request.form.getlist("addons")
        addon_prices={"Extra Shot":20,"Chocolate":10,"Whipped Cream":15,"Ice Cream":20,"Extra Milk":10}
        extra=sum(addon_prices.get(a,0) for a in addons)
        size_extra={"Small":0,"Medium":10,"Large":20}.get(size,0)
        item={
            "product_id":product["id"], "name":product["name"], "emoji":product["emoji"],
            "image":product_image(product["name"]),
            "quantity":1, "size":size, "sugar":sugar, "milk":milk,
            "temperature":temperature, "ice":ice, "addons":addons,
            "price":round(product["price"]+size_extra+extra,2)
        }
        cart=session.get("cart",[])
        cart.append(item); session["cart"]=cart
        return redirect(url_for("cart"))
    return render_template("customize.html", product=product)

@app.route("/cart")
def cart():
    cart=session.get("cart",[])
    subtotal=sum(i["price"]*i["quantity"] for i in cart)
    discount=session.get("discount",0)
    tax=round(max(subtotal-discount,0)*0.05,2)
    total=round(subtotal-discount+tax,2)
    return render_template("cart.html", cart=cart, subtotal=subtotal, discount=discount, tax=tax, total=total)

@app.post("/cart/update")
def cart_update():
    idx=int(request.form["index"])
    action=request.form["action"]
    cart=session.get("cart",[])
    if 0 <= idx < len(cart):
        if action=="plus": cart[idx]["quantity"]+=1
        elif action=="minus":
            cart[idx]["quantity"]-=1
            if cart[idx]["quantity"]<=0: cart.pop(idx)
        elif action=="remove": cart.pop(idx)
    session["cart"]=cart
    return redirect(url_for("cart"))

@app.post("/coupon")
def coupon():
    code=request.form.get("code","").strip().upper()
    db=get_db(); c=db.execute("SELECT * FROM coupons WHERE code=? AND active=1",(code,)).fetchone(); db.close()
    if not c:
        flash("Invalid or inactive coupon.", "error")
        session.pop("discount",None)
    else:
        cart=session.get("cart",[])
        subtotal=sum(i["price"]*i["quantity"] for i in cart)
        discount=round(subtotal*c["discount_value"]/100,2) if c["discount_type"]=="percent" else min(c["discount_value"],subtotal)
        session["discount"]=discount
        flash(f"Coupon applied. You saved ₹{discount:.2f}.","success")
    return redirect(url_for("cart"))

@app.route("/payment", methods=["GET","POST"])
def payment():
    cart=session.get("cart",[])
    if not cart:
        return redirect(url_for("menu"))
    subtotal=sum(i["price"]*i["quantity"] for i in cart)
    discount=session.get("discount",0)
    tax=round(max(subtotal-discount,0)*0.05,2)
    total=round(subtotal-discount+tax,2)
    if request.method=="POST":
        method=request.form.get("payment_method")
        if method=="cash":
            return redirect(url_for("cash_payment"))
        if method=="upi":
            # UPI flow: show a scannable QR, then confirm payment.
            return render_template("payment.html", total=total, show_upi_qr=True, show_card_pin=False, upi_id="tap2sip@upi")
        if method=="card":
            pin=request.form.get("card_pin", "").strip()
            # Validate PIN format without storing it.
            if not pin.isdigit() or len(pin) not in (4,5,6):
                flash("Enter a valid 4–6 digit PIN.", "error")
                return render_template("payment.html", total=total, show_upi_qr=False, show_card_pin=True, upi_id="tap2sip@upi")
            return complete_order("card",total)
        if method=="netbanking":
            return complete_order(method,total)
        if method=="upi_confirm":
            return complete_order("upi",total)
    return render_template("payment.html", total=total, show_upi_qr=False, show_card_pin=False, upi_id="tap2sip@upi")

@app.get("/upi-qr")
def upi_qr():
    # Generate the UPI payment QR code.
    amount=request.args.get("amount", "0")
    upi_id="tap2sip@upi"
    payload=f"upi://pay?pa={upi_id}&pn=Tap2Sip&am={amount}&cu=INR"
    img=qrcode.make(payload)
    buf=BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/cash-payment", methods=["GET","POST"])
def cash_payment():
    cart=session.get("cart",[])
    if not cart: return redirect(url_for("menu"))
    subtotal=sum(i["price"]*i["quantity"] for i in cart)
    discount=session.get("discount",0)
    tax=round(max(subtotal-discount,0)*0.05,2)
    total=round(subtotal-discount+tax,2)
    if request.method=="POST":
        amount=float(request.form.get("amount",0))
        if amount + 1e-9 < total:
            return render_template("cash_payment.html",total=total,amount=amount,error=f"Please add ₹{total-amount:.2f} more.")
        return complete_order("cash",total,amount)
    return render_template("cash_payment.html", total=total, amount=0, error=None)

def complete_order(method,total,amount_received=None):
    cart=session.get("cart",[])
    subtotal=sum(i["price"]*i["quantity"] for i in cart)
    discount=session.get("discount",0)
    tax=round(max(subtotal-discount,0)*0.05,2)
    order_no=make_order_number()
    txn=transaction_id()
    db=get_db()
    cur=db.execute("""INSERT INTO orders(order_number,total,discount,tax,payment_method,transaction_id,status,created_at)
                      VALUES(?,?,?,?,?,?,?,?)""",
                   (order_no,total,discount,tax,method,txn,"Confirmed",datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    oid=cur.lastrowid
    for i in cart:
        custom=f"Size: {i['size']}; Sugar: {i['sugar']}; Milk: {i['milk']}; Temp: {i['temperature']}; Ice: {i['ice']}; Add-ons: {', '.join(i['addons']) or 'None'}"
        db.execute("""INSERT INTO order_items(order_id,product_id,name,quantity,customization,price)
                      VALUES(?,?,?,?,?,?)""",(oid,i["product_id"],i["name"],i["quantity"],custom,i["price"]))
    db.commit(); db.close()
    session["last_order"]=order_no
    session["last_amount_received"]=amount_received
    session.pop("cart",None); session.pop("discount",None)
    return redirect(url_for("receipt",order_number=order_no))

@app.route("/receipt/<order_number>")
def receipt(order_number):
    db=get_db()
    order=db.execute("SELECT * FROM orders WHERE order_number=?",(order_number,)).fetchone()
    items=db.execute("SELECT * FROM order_items WHERE order_id=?",(order["id"],)).fetchall() if order else []
    db.close()
    if not order: return "Order not found",404
    change=None
    if order["payment_method"]=="cash" and session.get("last_amount_received") is not None:
        change=round(session["last_amount_received"]-order["total"],2)
    subtotal=sum(i["price"]*i["quantity"] for i in items)
    return render_template("receipt.html",order=order,items=items,change=change,subtotal=subtotal)

@app.route("/receipt/<order_number>/pdf")
def receipt_pdf(order_number):
    db=get_db()
    order=db.execute("SELECT * FROM orders WHERE order_number=?",(order_number,)).fetchone()
    items=db.execute("SELECT * FROM order_items WHERE order_id=?",(order["id"],)).fetchall() if order else []
    db.close()
    if not order:return "Order not found",404
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=A4); y=800
    c.setFont("Helvetica-Bold",20); c.drawCentredString(300,y,"TAP2SIP"); y-=25
    c.setFont("Helvetica",11); c.drawCentredString(300,y,"Smart Self-Service Beverage Kiosk"); y-=40
    c.drawString(60,y,f"Order: {order['order_number']}"); y-=18
    c.drawString(60,y,f"Date: {order['created_at']}"); y-=30
    for item in items:
        c.drawString(60,y,f"{item['name']} x{item['quantity']}"); c.drawRightString(530,y,f"Rs. {item['price']*item['quantity']:.2f}"); y-=18
    y-=10
    c.line(60,y,530,y); y-=22
    c.drawString(60,y,f"Subtotal: Rs. {sum(i['price']*i['quantity'] for i in items):.2f}"); y-=18
    c.drawString(60,y,f"Discount: Rs. {order['discount']:.2f}"); y-=18
    c.drawString(60,y,f"Tax: Rs. {order['tax']:.2f}"); y-=18
    c.setFont("Helvetica-Bold",12); c.drawString(60,y,f"TOTAL: Rs. {order['total']:.2f}"); y-=22
    c.setFont("Helvetica",11); c.drawString(60,y,f"Payment: {order['payment_method'].upper()}"); y-=18
    c.drawString(60,y,f"Transaction: {order['transaction_id']}"); y-=45
    c.drawCentredString(300,y,"Thank you! Enjoy your drink.")
    c.save(); buf.seek(0)
    return send_file(buf,as_attachment=True,download_name=f"Tap2Sip_{order_number.replace('#','')}.pdf",mimetype="application/pdf")

@app.route("/order/<order_number>")
def order_status(order_number):
    db=get_db(); order=db.execute("SELECT * FROM orders WHERE order_number=?",(order_number,)).fetchone(); db.close()
    if not order:return "Order not found",404
    return render_template("order_status.html",order=order)

@app.post("/feedback")
def feedback():
    db=get_db()
    db.execute("INSERT INTO feedback(order_number,rating,drink_rating,comment,created_at) VALUES(?,?,?,?,?)",
               (request.form.get("order_number"),request.form.get("rating"),request.form.get("drink_rating"),request.form.get("comment"),datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit(); db.close()
    flash("Thanks for your feedback!","success")
    return redirect(url_for("index"))

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        db=get_db(); u=db.execute("SELECT * FROM users WHERE username=?",(request.form.get("username"),)).fetchone(); db.close()
        if u and check_password_hash(u["password"],request.form.get("password","")):
            session["admin"]=True; return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.","error")
    return render_template("admin/login.html")

def admin_required():
    return session.get("admin") is True

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin",None); return redirect(url_for("admin_login"))

@app.route("/admin")
def admin_dashboard():
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db()
    stats=db.execute("""SELECT COUNT(*) orders, COALESCE(SUM(total),0) revenue,
                       COALESCE(SUM(CASE WHEN payment_method!='cash' THEN 1 ELSE 0 END),0) online,
                       COALESCE(SUM(CASE WHEN payment_method='cash' THEN 1 ELSE 0 END),0) cash FROM orders""").fetchone()
    popular=db.execute("SELECT name,SUM(quantity) qty FROM order_items GROUP BY name ORDER BY qty DESC LIMIT 5").fetchall()
    low=db.execute("SELECT * FROM inventory WHERE quantity<=minimum_quantity ORDER BY quantity").fetchall()
    recent=db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 8").fetchall()
    db.close()
    return render_template("admin/dashboard.html",stats=stats,popular=popular,low=low,recent=recent)

@app.route("/admin/orders")
def admin_orders():
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db(); orders=db.execute("SELECT * FROM orders ORDER BY id DESC").fetchall(); db.close()
    return render_template("admin/orders.html",orders=orders)

@app.post("/admin/order-status/<int:order_id>")
def admin_order_status(order_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db(); db.execute("UPDATE orders SET status=? WHERE id=?",(request.form["status"],order_id)); db.commit(); db.close()
    return redirect(url_for("admin_orders"))

@app.route("/admin/products")
def admin_products():
    if not admin_required(): return redirect(url_for("admin_login"))
    return render_template("admin/products.html",products=get_products())

@app.post("/admin/products/save")
def admin_product_save():
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db(); pid=request.form.get("id")
    data=(request.form["name"],request.form["category"],request.form["description"],float(request.form["price"]),request.form.get("emoji","☕"),int(request.form.get("available",1)))
    if pid:
        db.execute("UPDATE products SET name=?,category=?,description=?,price=?,emoji=?,available=? WHERE id=?",(*data,int(pid)))
    else:
        db.execute("INSERT INTO products(name,category,description,price,emoji,available) VALUES(?,?,?,?,?,?)",data)
    db.commit(); db.close(); return redirect(url_for("admin_products"))

@app.post("/admin/products/delete/<int:pid>")
def admin_product_delete(pid):
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db(); db.execute("DELETE FROM products WHERE id=?",(pid,)); db.commit(); db.close(); return redirect(url_for("admin_products"))

@app.route("/admin/inventory")
def admin_inventory():
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db(); inv=db.execute("SELECT * FROM inventory ORDER BY id").fetchall(); db.close()
    return render_template("admin/inventory.html",inventory=inv)

@app.post("/admin/inventory/<int:item_id>")
def admin_inventory_update(item_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db(); db.execute("UPDATE inventory SET quantity=?,minimum_quantity=? WHERE id=?",
                             (float(request.form["quantity"]),float(request.form["minimum_quantity"]),item_id)); db.commit(); db.close()
    return redirect(url_for("admin_inventory"))

@app.route("/admin/reports")
def admin_reports():
    if not admin_required(): return redirect(url_for("admin_login"))
    db=get_db()
    daily=db.execute("""SELECT substr(created_at,1,10) day,COUNT(*) orders,ROUND(SUM(total),2) revenue
                        FROM orders GROUP BY day ORDER BY day DESC LIMIT 14""").fetchall()
    payments=db.execute("SELECT payment_method,COUNT(*) count,ROUND(SUM(total),2) total FROM orders GROUP BY payment_method").fetchall()
    feedback=db.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT 10").fetchall()
    db.close()
    return render_template("admin/reports.html",daily=daily,payments=payments,feedback=feedback)

@app.route("/api/products")
def api_products():
    return jsonify([dict(p) for p in get_products()])

@app.route("/api/order/<order_number>")
def api_order(order_number):
    db=get_db(); o=db.execute("SELECT * FROM orders WHERE order_number=?",(order_number,)).fetchone(); db.close()
    return jsonify(dict(o)) if o else (jsonify({"error":"not found"}),404)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
