import traceback
from datetime import datetime, timedelta

import mysql
from flask import Flask, request, jsonify, render_template, redirect, session, url_for, flash

from db import connection
from db.connection import get_connection
from routes.route_logic import find_all_routes
from services.wallet import update_wallet, get_wallet_balance, update_wallet_balance, save_booking
import smtplib, pymysql
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid
confirmation_code = str(uuid.uuid4())[:8].upper()  # e.g., 'A3F9C7D1'


app = Flask(__name__)
app.secret_key = 'super_secret_key_2025'  # <- add this
# Define this at the top of your app.py
route_cache = {}

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'justsecret4411@gmail.com'
SMTP_PASSWORD = 'tmob lbjy ngnz oway'


@app.route('/logout')
def logout():
    print("User logged out:", session.get('user_id'))  # Debug
    session.clear()
    return redirect('/login')


def send_confirmation_email(to_address, confirmation_code, route_segments):
    # Construct booking details
    booking_details = ""

    for segment in route_segments:
        source = segment.get('source', 'Unknown')
        destination = segment.get('destination', 'Unknown')
        mode = segment.get('mode', 'Unknown')
        departure_datetime = segment.get('departure_datetime', 'N/A')
        arrival_datetime = segment.get('arrival_datetime', 'N/A')
        cost = segment.get('cost', 'N/A')
        duration = segment.get('duration', 'N/A')

        booking_details += f"""
        From: {source}
        To: {destination}
        Mode of Transport: {mode}
        Departure: {departure_datetime}
        Arrival: {arrival_datetime}
        Cost: ₹{cost}
        Duration: {duration} minutes
        ---------------------------
        """

    # Email subject and body
    subject = "Booking Confirmation"
    body = f"""
    Dear Customer,

    Thank you for booking with us. Here are your booking details:

    Confirmation Code: {confirmation_code}

    Booking Details:
    {booking_details}

    We hope you have a safe and pleasant journey!

    Best Regards,
    Multimodal Transport System Team
    """

    # Set up MIME
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = to_address
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to SMTP server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure connection
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, to_address, text)
        server.quit()
        print(f"Booking confirmation sent to {to_address}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def format_route_with_dates(route, travel_date_str):
    base_date = datetime.strptime(travel_date_str, "%Y-%m-%d")
    updated_route = []

    for step in route:
        # Convert if not a string already
        dep_time_raw = step['departure_time']
        arr_time_raw = step['arrival_time']

        if isinstance(dep_time_raw, timedelta):
            dep_time = (datetime.min + dep_time_raw).time()
        elif isinstance(dep_time_raw, datetime):
            dep_time = dep_time_raw.time()
        else:
            dep_time = datetime.strptime(str(dep_time_raw), "%H:%M:%S").time()

        if isinstance(arr_time_raw, timedelta):
            arr_time = (datetime.min + arr_time_raw).time()
        elif isinstance(arr_time_raw, datetime):
            arr_time = arr_time_raw.time()
        else:
            arr_time = datetime.strptime(str(arr_time_raw), "%H:%M:%S").time()

        # Combine date + time
        dep_datetime = datetime.combine(base_date, dep_time)
        arr_datetime = datetime.combine(base_date, arr_time)

        if arr_datetime < dep_datetime:
            arr_datetime += timedelta(days=1)

        # Format with day + full date
        step['departure_datetime'] = dep_datetime.strftime("%a, %Y-%m-%d %H:%M")
        step['arrival_datetime'] = arr_datetime.strftime("%a, %Y-%m-%d %H:%M")

        updated_route.append(step)

    return updated_route


route_cache = {}


@app.route('/find-routes', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        travel_date = request.form['travel_date']
        session['travel_date'] = travel_date  # 🔒 Save travel_date in session

        routes = find_all_routes(source, destination, travel_date)
        for i, route in enumerate(routes):
            route['id'] = i   # or just i, as long as it's unique
            route['route'] = format_route_with_dates(route['route'], travel_date)
            route_cache[i] = route

        fastest = min(routes, key=lambda r: r['total_time'], default=None)
        cheapest = min(routes, key=lambda r: r['total_cost'], default=None)

        return render_template('results.html',
                               travel_date=travel_date,
                               routes=routes,
                               fastest=fastest,
                               cheapest=cheapest)

    return render_template('index.html')


def get_route_by_id(route_id):
    with get_connection().cursor() as cursor:
        sql = "SELECT * FROM routes WHERE id = %s"
        cursor.execute(sql, (route_id,))
        return cursor.fetchone()


@app.route('/confirmation/<int:route_id>')
def confirmation(route_id):
    route = route_cache.get(route_id)
    if not route:
        return "Route not found", 404
    return render_template('confirmation.html', route=route)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Safely get and trim email/password
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        # Connect to the DB
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        try:
            # Check if user exists with given email and password
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()

            if user:
                # Store user data in session
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_name'] = user['name']

                print(f"[LOGIN SUCCESS] User ID: {user['id']}, Email: {user['email']}")

                return redirect('/')  # Or redirect to home/dashboard
            else:
                print("[LOGIN FAILED] Invalid credentials")
                return render_template('login.html', error="Invalid email or password")

        except Exception as e:
            print(f"[LOGIN ERROR] {e}")
            return "An error occurred during login", 500

        finally:
            conn.close()

    # GET method — render login form
    return render_template('login.html')

@app.route('/confirm-route/<int:route_index>', methods=['GET', 'POST'])
def confirm_route(route_index):
    all_routes = session.get('search_results')
    if not all_routes or route_index >= len(all_routes):
        flash("Invalid route selection.", "error")
        return redirect('/find-routes')

    selected_route = all_routes[route_index]
    session['selected_route'] = selected_route  # ✅ Save in session
    return render_template('confirm.html', route=selected_route)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (name, email, password, phone)
            VALUES (%s, %s, %s, %s)
        """, (name, email, password, phone))
        conn.commit()

        # Get the newly created user's ID
        cursor.execute("SELECT LAST_INSERT_ID() AS id")
        user_id = cursor.fetchone()['id']

        # 💰 Insert wallet with ₹100 initial balance
        cursor.execute("INSERT INTO wallet (user_id, balance) VALUES (%s, 100.00)", (user_id,))
        conn.commit()

        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/add-to-wallet', methods=['POST'])
def add_to_wallet():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    # Get the amount to add
    amount_to_add = request.form.get('amount')  # Ensure this is a valid numeric value
    try:
        amount_to_add = float(amount_to_add)  # Convert to float to handle decimals
        if amount_to_add <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect('/wallet')

        # Update the wallet balance
        update_wallet(user_id, amount_to_add)

        # After updating, get the new balance
        balance = get_wallet_balance(user_id)

        # Redirect to wallet page to show the updated balance
        return render_template('wallet.html', balance=balance)

    except ValueError:
        flash("Invalid amount", "error")
        return redirect('/wallet')


@app.route('/add-funds', methods=['POST'])
def add_funds():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')  # Redirect if not logged in

    try:
        amount = float(request.form.get('amount'))
        if amount <= 0:
            flash("Amount must be greater than 0", "error")
            return redirect('/wallet')
        update_wallet(user_id, amount)
    except (TypeError, ValueError):
        flash("Invalid amount.", "error")
        return redirect('/wallet')

    return redirect('/wallet')


@app.route('/wallet', methods=['GET'])
def wallet_balance():
    user_id = session.get('user_id')
    print(f"User ID from session: {user_id}")

    if not user_id:
        return redirect('/login')

    balance = get_wallet_balance(user_id)
    print(f"Balance from DB: {balance}")

    if balance is None:
        balance = 0.00  # Ensure a default value if None

    return render_template('wallet.html', balance=balance)


@app.route('/book', methods=['POST'])
def book_route():
    data = request.json
    user_id = data['user_id']
    total_cost = data['cost']
    route_steps = data['steps']

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Wallet balance and seat deduction logic...
        confirmation_code = str(uuid.uuid4())[:8].upper()

        for step in route_steps:
            route_id = step['route_id']
            cursor.execute("UPDATE routes SET seats_available = seats_available - 1 WHERE id = %s", (route_id,))
            cursor.execute(
                "INSERT INTO bookings (user_id, route_id, cost, confirmation_code) VALUES (%s, %s, %s, %s)",
                (user_id, route_id, step['cost'], confirmation_code)
            )

        # ✅ Now fetch user's email
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user_email = cursor.fetchone()[0]

        # ✅ Generate HTML email body
        html_details_string = f"""
        <h3>Your Booking Confirmation</h3>
        <p><strong>Confirmation Code:</strong> {confirmation_code}</p>
        <ul>
            {''.join([f"<li>{step['source']} → {step['destination']} via {step['mode']} - ₹{step['cost']}</li>" for step in route_steps])}
        </ul>
        <p><strong>Total:</strong> ₹{total_cost}</p>
        """

        # ✅ Send the email
        send_confirmation_email(user_email, html_details_string)

        conn.commit()
        return jsonify({"message": "Booking successful", "confirmation": confirmation_code}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/bookings/<int:user_id>')
def user_bookings(user_id):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT b.id, b.confirmation_code, b.booking_time, b.cost,
               r.source, r.destination, tm.mode
        FROM bookings b
        JOIN routes r ON b.route_id = r.id
        JOIN transport_modes tm ON r.mode_id = tm.id
        WHERE b.user_id = %s
        ORDER BY b.booking_time DESC
    """, (user_id,))
    bookings = cursor.fetchall()
    conn.close()

    return render_template('bookings.html', bookings=bookings)


@app.route('/booking-confirmation/<int:route_id>', methods=['POST'])
def booking_confirmation(route_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Booking session expired or not logged in", "error")
        return redirect('/login')

    selected_route = route_cache.get(route_id)
    if not selected_route:
        flash("Session expired. Please search again.", "error")
        return redirect('/find-routes')

    total_cost = selected_route['total_cost']
    route_segments = selected_route['route']

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        print("Wallet query result:", result)

        if not result:
            flash("Wallet not found for this user.", "error")
            return redirect('/wallet')

        wallet_balance = result['balance']
        if wallet_balance < total_cost:
            flash("Insufficient wallet balance.", "error")
            return redirect('/wallet')

        cursor.execute("UPDATE wallet SET balance = balance - %s WHERE user_id = %s", (total_cost, user_id))

        confirmation_code = str(uuid.uuid4())[:8].upper()  # Generate unique code

        first_segment_route_id = route_segments[0]['id']
        cursor.execute("""
            INSERT INTO bookings (user_id, route_id, cost, confirmation_code)
            VALUES (%s, %s, %s, %s)
        """, (user_id, first_segment_route_id, total_cost, confirmation_code))

        booking_id = cursor.lastrowid
        for segment in route_segments:
            cursor.execute("INSERT INTO booking_routes (booking_id, route_id) VALUES (%s, %s)", (booking_id, segment['id']))

        conn.commit()
        print("Route segments:", route_segments)

        # Step 1: Retrieve user email
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user_email = cursor.fetchone()['email']

        # Step 2: Create the booking details string
        # Assuming 'name' key might be different in some segments
        booking_details = "\n".join(
            [f"Route Segment: {segment.get('name', 'Unknown')} (ID: {segment['id']})" for segment in route_segments])

        # Step 3: Send the confirmation email
        send_confirmation_email(user_email, confirmation_code, route_segments)

        # Step 4: Flash success message and redirect to bookings page
        flash("Booking confirmed successfully! A confirmation email has been sent.", "success")
        return redirect('/bookings')

    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        flash("Booking failed due to an error.", "error")
        return redirect('/find-routes')

    finally:
        conn.close()


@app.route('/bookings')
def view_bookings():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view bookings.", "error")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get all bookings and their route segments
        cursor.execute("""
            SELECT b.id AS booking_id, b.cost, b.booking_time, b.confirmation_code,
                   r.source, r.destination, r.departure_time, r.arrival_time
            FROM bookings b
            JOIN booking_routes br ON b.id = br.booking_id
            JOIN routes r ON br.route_id = r.id
            WHERE b.user_id = %s
            ORDER BY b.booking_time DESC
        """, (user_id,))

        rows = cursor.fetchall()
        print("Fetched rows:", rows)  # Debugging line to check if results are returned

        # Group segments by booking_id
        bookings = {}
        for row in rows:
            bid = row['booking_id']
            if bid not in bookings:
                bookings[bid] = {
                    'confirmation_code': row['confirmation_code'],
                    'cost': row['cost'],
                    'booking_time': row['booking_time'],
                    'segments': []
                }
            bookings[bid]['segments'].append({
                'source': row['source'],
                'destination': row['destination'],
                'departure_time': row['departure_time'],
                'arrival_time': row['arrival_time']
            })

        return render_template('bookings.html', bookings=bookings)

    except Exception as e:
        traceback.print_exc()
        flash("Could not retrieve your bookings.", "error")
        return redirect('/')

    finally:
        conn.close()


def confirm_booking(selected_route):
    user_id = session.get('user_id')
    total_cost = selected_route['total_cost']
    route_segments = selected_route['route']

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Deduct from wallet
        cursor.execute("UPDATE wallet SET balance = balance - %s WHERE user_id = %s", (total_cost, user_id))

        # Create a new booking
        confirmation_code = str(uuid.uuid4())[:8].upper()
        cursor.execute("""
            INSERT INTO bookings (user_id, route_id, cost, confirmation_code)
            VALUES (%s, %s, %s, %s)
        """, (user_id, route_segments[0]['id'], total_cost, confirmation_code))
        booking_id = cursor.lastrowid

        # Insert each segment into booking_routes
        for segment in route_segments:
            cursor.execute("INSERT INTO booking_routes (booking_id, route_id) VALUES (%s, %s)", (booking_id, segment['id']))

        conn.commit()
        flash("Booking successful!", "success")

        # (Optional) Send confirmation email here

    except Exception as e:
        conn.rollback()
        flash("Booking failed. Error: " + str(e), "error")
    finally:
        conn.close()


def deduct_wallet_balance(user_id, total_cost):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch the current balance
    cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result:
        current_balance = result[0]

        if current_balance >= total_cost:
            # Deduct the amount if sufficient balance is available
            new_balance = current_balance - total_cost
            cursor.execute("UPDATE wallet SET balance = %s WHERE user_id = %s", (new_balance, user_id))
            conn.commit()
            conn.close()
            return True  # Sufficient funds, deduction successful
        else:
            conn.close()
            return False  # Not enough funds
    else:
        conn.close()
        return False  # No user found


if __name__ == '__main__':
    app.run(debug=True)
