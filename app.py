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

@app.route('/update_route')
def update_route():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, source, destination, service_name, service_number FROM routes")
    routes = cursor.fetchall()
    conn.close()
    return render_template('update_route_list.html', routes=routes)

@app.route('/update_route/<int:route_id>', methods=['GET', 'POST'])
def update_route_form(route_id):
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        duration = request.form['duration']
        cost = request.form['cost']
        departure_time = request.form['departure_time']
        arrival_time = request.form['arrival_time']
        operating_days = ','.join(request.form.getlist('operating_days'))

        cursor.execute("""
            UPDATE routes SET duration=%s, cost=%s, departure_time=%s, arrival_time=%s, operating_days=%s WHERE id=%s
        """, (duration, cost, departure_time, arrival_time, operating_days, route_id))
        conn.commit()
        conn.close()
        return redirect(url_for('transport_route'))  # Redirect to routes list

    # For GET request, fetch existing data to pre-fill form
    cursor.execute("SELECT * FROM routes WHERE id=%s", (route_id,))
    route = cursor.fetchone()
    conn.close()
    return render_template('update_route_form.html', route=route)


@app.route('/add_route', methods=['GET', 'POST'])
def add_route():
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        mode_id = request.form['mode_id']
        duration = request.form['duration']
        cost = request.form['cost']
        departure_time = request.form['departure_time']
        arrival_time = request.form['arrival_time']
        operating_days = request.form['operating_days']
        service_name = request.form['service_name']
        service_number = request.form['service_number']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO routes (source, destination, mode_id, duration, cost, departure_time, arrival_time, operating_days, service_name, service_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (source, destination, mode_id, duration, cost, departure_time, arrival_time, operating_days, service_name, service_number))
        conn.commit()
        conn.close()
        return redirect(url_for('transport_route'))  # Redirect to view all routes after adding

    return render_template('add_route.html')


@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Access Denied. Admins Only.', 'error')
        return redirect('/')

    conn = get_connection()   # ✅ Correct way to get DB connection
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        # Fetch users
        cursor.execute("SELECT id, email, name FROM users")
        users = cursor.fetchall()

        # Fetch detailed bookings
        cursor.execute("""
            SELECT 
                b.id AS booking_id,
                b.user_id,
                u.name AS user_name,
                tm.mode AS mode,
                b.cost,
                b.booking_time,
                b.confirmation_code,
                r.source,
                r.destination,
                r.departure_time,
                r.arrival_time
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN booking_routes br ON b.id = br.booking_id
            JOIN routes r ON br.route_id = r.id
            JOIN transport_modes tm ON r.mode_id = tm.id
        """)
        bookings = cursor.fetchall()

        # Fetch wallets
        cursor.execute("SELECT user_id, balance FROM wallet")
        wallets = cursor.fetchall()

        return render_template('admin.html', users=users, bookings=bookings, wallets=wallets)

    except Exception as e:
        print(f"[ADMIN ERROR] {e}")
        return "Error loading admin dashboard", 500

    finally:
        cursor.close()
        conn.close()

def parse_time_flexibly(time_str):
    """Parses time in 'HH:MM' or 'HH:MM:SS' formats."""
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return datetime.strptime(time_str, "%H:%M:%S").time()

def format_route_with_dates(segments, start_date):
    current_datetime = datetime.strptime(start_date + " 00:00", "%Y-%m-%d %H:%M")
    formatted_segments = []

    for segment in segments:
        dep_time_raw = segment['departure_time']
        arr_time_raw = segment['arrival_time']

        # Convert all to strings first
        dep_str = str(dep_time_raw)
        arr_str = str(arr_time_raw)

        dep_time = parse_time_flexibly(dep_str)
        arr_time = parse_time_flexibly(arr_str)

        # Departure datetime
        dep_dt = current_datetime.replace(hour=dep_time.hour, minute=dep_time.minute)
        if dep_dt < current_datetime:
            dep_dt += timedelta(days=1)

        # Arrival datetime
        arr_dt = dep_dt.replace(hour=arr_time.hour, minute=arr_time.minute)
        if arr_time <= dep_time:
            arr_dt += timedelta(days=1)

        segment['departure_datetime'] = dep_dt
        segment['arrival_datetime'] = arr_dt
        segment['formatted_departure'] = dep_dt.strftime('%a, %Y-%m-%d %H:%M')
        segment['formatted_arrival'] = arr_dt.strftime('%a, %Y-%m-%d %H:%M')

        current_datetime = arr_dt
        formatted_segments.append(segment)

    return formatted_segments

route_cache = {}


@app.route('/find-routes', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        travel_date = request.form['travel_date']

        if not source or not destination or not travel_date:
            flash("Please fill in all fields.", "error")
            return redirect('/')

        session['travel_date'] = travel_date  # 🔒 Save travel_date in session

        routes = find_all_routes(source, destination, travel_date)

        if not routes:
            flash("No routes found for the given source, destination, or date.", "warning")
            return render_template('results.html', routes=[], travel_date=travel_date)

        route_cache.clear()  # 🔁 Clear old cache

        # Make sure to add 'id' to each route
        for i, route in enumerate(routes):
            route['cache_id'] = i  # For selection from UI
            route['id'] = route.get('id', i)  # Ensure 'id' exists for each route, use index as fallback
            route['route'] = format_route_with_dates(route['route'], travel_date)

            print(f"[ROUTE {i}] Total Time: {route['total_time']} mins, Total Cost: ₹{route['total_cost']}")
            for segment in route['route']:
                print(
                    f"  SEGMENT - ID: {segment.get('id')} | {segment['source']} → {segment['destination']} via {segment['mode']}")

            route_cache[i] = route

        # Get the fastest and cheapest routes
        fastest = min(routes, key=lambda r: r['total_time'], default=None)
        cheapest = min(routes, key=lambda r: r['total_cost'], default=None)

        # Ensure that 'id' exists before passing to the template
        if fastest and 'id' not in fastest:
            fastest['id'] = fastest.get('id', None)
        if cheapest and 'id' not in cheapest:
            cheapest['id'] = cheapest.get('id', None)

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


@app.route('/transport_route')
def transport_route():
    # Connect to your MySQL database
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='admin@123',
        db='yatrii',
        cursorclass=pymysql.cursors.DictCursor  # Optional: makes row results as dictionaries
    )

    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM routes")
        routes = cursor.fetchall()  # This will be a list of dictionaries if DictCursor is used

    conn.close()
    return render_template('transport_route.html', routes=routes)


@app.route('/confirmation/<int:route_id>', methods=['GET', 'POST'])
def confirmation(route_id):
    route = route_cache.get(route_id)
    if not route:
        flash("Invalid route selection.", "error")
        return redirect('/')

    return render_template("confirmation.html", route=route)


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

                # 🛡️ Admin check:
                if user['email'] == 'justsecret4411@gmail.com':  # <-- put your admin email here
                    session['is_admin'] = True
                else:
                    session['is_admin'] = False

                print(f"[LOGIN SUCCESS] User ID: {user['id']}, Email: {user['email']}")

                return redirect('/admin')  # Or redirect to home/dashboard
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

def deduct_seats_for_route(route_segments, cursor):
    for segment in route_segments:
        segment_id = segment['id']
        cursor.execute("""
            UPDATE routes
            SET seats_available = seats_available - 1
            WHERE id = %s AND seats_available > 0
        """, (segment_id,))


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
        # Step 1: Wallet check
        cursor.execute("SELECT balance FROM wallet WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            flash("Wallet not found for this user.", "error")
            return redirect('/wallet')

        wallet_balance = result['balance']
        if wallet_balance < total_cost:
            flash("Insufficient wallet balance.", "error")
            return redirect('/wallet')

        # Step 2: Check all segment seat availability
        for segment in route_segments:
            segment_id = segment['id']
            cursor.execute("SELECT seats_available FROM routes WHERE id = %s", (segment_id,))
            seat_data = cursor.fetchone()
            if not seat_data or seat_data['seats_available'] <= 0:
                flash(f"Segment {segment_id} is full. Please choose another route.", "error")
                conn.rollback()
                return redirect('/find-routes')

        # Step 3: Deduct wallet balance
        cursor.execute("UPDATE wallet SET balance = balance - %s WHERE user_id = %s", (total_cost, user_id))

        # Step 4: Create booking record
        confirmation_code = str(uuid.uuid4())[:8].upper()
        first_segment_route_id = route_segments[0]['id']
        cursor.execute("""
            INSERT INTO bookings (user_id, route_id, cost, confirmation_code)
            VALUES (%s, %s, %s, %s)
        """, (user_id, first_segment_route_id, total_cost, confirmation_code))
        booking_id = cursor.lastrowid

        # Step 5: Insert into booking_routes and reduce seats
        for segment in route_segments:
            segment_id = segment['id']
            cursor.execute("""
                INSERT INTO booking_routes (booking_id, route_id)
                VALUES (%s, %s)
            """, (booking_id, segment_id))

        # Deduct seats for all segments in one place
        deduct_seats_for_route(route_segments, cursor)

        # Step 6: Final commit
        conn.commit()

        # Step 7: Send confirmation email
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user_email = cursor.fetchone()['email']
        send_confirmation_email(user_email, confirmation_code, route_segments)

        flash("Booking confirmed successfully! A confirmation email has been sent.", "success")
        return redirect('/bookings')

    except Exception as e:
        traceback.print_exc()
        conn.rollback()
        flash("Booking failed due to an internal error.", "error")
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
        # Set the transaction isolation level to handle concurrent transactions
        cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")

        # Deduct from wallet
        cursor.execute("UPDATE wallet SET balance = balance - %s WHERE user_id = %s", (total_cost, user_id))

        # Create a new booking
        confirmation_code = str(uuid.uuid4())[:8].upper()
        cursor.execute("""
            INSERT INTO bookings (user_id, route_id, cost, confirmation_code)
            VALUES (%s, %s, %s, %s)
        """, (user_id, route_segments[0]['id'], total_cost, confirmation_code))
        booking_id = cursor.lastrowid

        # Insert each segment into booking_routes and reduce available seats
        for segment in route_segments:
            route_id = segment['id']  # Route ID for this segment

            # Insert booking route
            cursor.execute("INSERT INTO booking_routes (booking_id, route_id) VALUES (%s, %s)", (booking_id, route_id))

            # Fetch current seats_available with row lock to avoid concurrency issues
            cursor.execute("SELECT seats_available FROM routes WHERE id = %s FOR UPDATE", (route_id,))
            seats_available = cursor.fetchone()[0]

            # Debugging log
            print(f"Route ID: {route_id}, Seats Available: {seats_available}")

            if seats_available > 0:
                # Reduce the seats by 1
                cursor.execute("UPDATE routes SET seats_available = seats_available - 1 WHERE id = %s", (route_id,))

                # Check if update was successful
                if cursor.rowcount == 1:
                    print(f"Reduced seat availability for route {route_id}. New seats_available: {seats_available - 1}")
                else:
                    raise Exception(f"Failed to update seat availability for route ID: {route_id}")
            else:
                raise Exception(f"No available seats for route ID: {route_id}")

        # Commit transaction
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
