import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file
from pyexpat.errors import messages
from werkzeug.utils import secure_filename
from models import get_all_products, add_product, update_product, delete_product, get_product_by_id
import sqlite3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from datetime import datetime

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect('data/inventory.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/report')
def report():
    conn = get_db_connection()

    #purchases = conn.execute("SELECT * FROM purchases ORDER BY date DESC").fetchall()
    sales = conn.execute("SELECT * FROM sales ORDER BY timestamp DESC").fetchall()

    conn.close()
    return render_template('report.html', sales=sales)



@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    message = ""
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])

        conn = get_db_connection()
        cursor = conn.cursor()
        product = cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

        if product:
            new_quantity = product['quantity'] + quantity
            cursor.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_quantity, product_id))
            conn.commit()
            message = f"Successfully purchased {quantity} units of product ID {product_id}. New quantity: {new_quantity}."
            flash(message, 'success')
        else:
            message = f"Product with ID {product_id} not found."
            flash(message, 'error')
        conn.close()
    return render_template('purchase.html')




@app.route('/sales', methods=['GET', 'POST'])
def sales():
    with get_db_connection() as conn:
        products = conn.execute('SELECT * FROM products').fetchall()

    if 'cart' not in session:
        session['cart'] = []

    if request.method == 'POST':
        try:
            quantity = int(request.form['quantity'])
            product_id = int(request.form['product_id'])
        except (ValueError, KeyError):
            flash('Invalid input.', 'error')
            return redirect(url_for('sales'))

        with get_db_connection() as conn:
            product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

        if product:
            item = {
                'id': product['id'],
                'name': product['name'],
                'quantity': quantity,
                'price': product['price'],
                'total': round(product['price'] * quantity, 2)
            }
            session['cart'].append(item)
            session.modified = True
            flash(f'Added {quantity} of {product["name"]} to cart.', 'success')
        return redirect(url_for('sales'))

    cart = session.get('cart', [])
    cart_total = sum(item['total'] for item in cart)
    return render_template('sales.html', products=products, cart=cart, cart_total=cart_total)


@app.route("/generate-receipt")
def generate_receipt_pdf():
    cart = session.get("cart", [])
    if not cart:
        flash("Cart is empty. Cannot generate receipt.", "warning")
        return redirect(url_for("sales"))

    total = sum(item["quantity"] * item["price"] for item in cart)
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Generate PDF in memory
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "SALES RECEIPT")
    y -= 30

    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Date: {date}")
    y -= 20
    p.drawString(50, y, "Item")
    p.drawString(200, y, "Qty")
    p.drawString(250, y, "Price")
    p.drawString(320, y, "Total")
    y -= 15
    p.line(50, y, 500, y)
    y -= 20

    for item in cart:
        if y < 50:  # handle page break
            p.showPage()
            y = height - 50
        p.drawString(50, y, item["name"])
        p.drawString(200, y, str(item["quantity"]))
        p.drawString(250, y, f"{item['price']:.2f}")
        p.drawString(320, y, f"{item['quantity'] * item['price']:.2f}")
        y -= 20

    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Total: ₦{total:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mimetype="application/pdf"
    )


@app.route("/receipt")
def receipt():
    return render_template("receipt.html")


@app.route("/checkout", methods=["POST"])
def checkout():
    cart = session.get("cart", [])
    if not cart:
        return redirect(url_for("sales"))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        for item in cart:
            product = cursor.execute(
                "SELECT quantity, price FROM products WHERE id = ?", (item["id"],)
            ).fetchone()
            if product and product["quantity"] >= item["quantity"]:
                new_qty = product["quantity"] - item["quantity"]
                cursor.execute(
                    "UPDATE products SET quantity = ? WHERE id = ?", (new_qty, item["id"])
                )
                total = item["quantity"] * item["price"]
                cursor.execute(
                    "INSERT INTO sales (product_id, product_name, quantity, price, total) VALUES (?, ?, ?, ?, ?)",
                    (item["id"], item["name"], item["quantity"], item["price"], total),
                )
            else:
                session["cart"] = []
                conn.commit()
                flash(f'Insufficient stock for product: {item["name"]}', 'error')
                return redirect(url_for('sales'))
        conn.commit()

    session["cart"] = []
    session.modified = True
    return redirect(url_for("receipt"))


@app.route("/sales-history")
def sales_history():
    with get_db_connection() as conn:
        sales = conn.execute("SELECT * FROM sales ORDER BY date DESC").fetchall()
    return render_template("sales_history.html", sales=sales)





@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit(product_id):
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        quantity = request.form['quantity']
        price = request.form['price']

        if not name or not category or not quantity or not price:
            flash('All fields are required!', 'error')
            return redirect(url_for('edit', product_id=product_id))

        try:
            quantity = int(quantity)
            price = float(price)
            update_product(product_id, name, category, quantity, price)
            flash('Product updated successfully!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Invalid input for quantity or price.', 'error')
            return redirect(url_for('edit', product_id=product_id))

    product = get_product_by_id(product_id)
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('index'))
    return render_template('edit.html', product=product)


@app.route('/delete/<int:product_id>', methods=['POST'])
def delete(product_id):
    delete_product(product_id)
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/')
def index():
    query = request.args.get('q', '').strip()
    with get_db_connection() as conn:
        c = conn.cursor()
        if query:
            c.execute("SELECT * FROM products WHERE name LIKE ? OR category LIKE ?",
                      ('%' + query + '%', '%' + query + '%'))
            products = c.fetchall()
            if not products:
                flash('No products found for your search.', 'info')
        else:
            c.execute("SELECT * FROM products")
            products = c.fetchall()
    return render_template('index.html', products=products)


@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        quantity = request.form['quantity']
        price = request.form['price']
        file = request.files.get('image')

        if not name or not category or not quantity or not price:
            flash('All fields are required!', 'error')
            return redirect(url_for('add'))

        image_filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_filename)

        try:
            quantity = int(quantity)
            price = float(price)
            add_product(name, category, quantity, price,)
            flash('Product added successfully!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Invalid input for quantity or price.', 'error')

    return render_template('add.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




# Example: Basic login/logout (for demonstration)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Replace with real authentication
        if username == 'admin' and password == 'password':
            session['user'] = username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
