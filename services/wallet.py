# services/wallet.py
from db.connection import get_connection

def update_wallet(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE wallet SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
    conn.commit()
    print(f"Balance updated for user {user_id}")  # Add log here to confirm execution
    conn.close()

def save_booking(user_id, route_data, total_cost):
    conn = get_connection()
    cursor = conn.cursor()

    # Insert into bookings table
    booking_query = """
        INSERT INTO bookings (user_id, total_cost, booking_time)
        VALUES (%s, %s, NOW())
    """
    cursor.execute(booking_query, (user_id, total_cost))
    booking_id = cursor.lastrowid

    # Insert each route segment
    segment_query = """
        INSERT INTO booking_segments (booking_id, source, destination, mode, cost, departure_datetime, arrival_datetime)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    for step in route_data['route']:
        cursor.execute(segment_query, (
            booking_id,
            step['source'],
            step['destination'],
            step['mode'],
            step['cost'],
            step['departure_datetime'],
            step['arrival_datetime']
        ))

    conn.commit()
    conn.close()


def update_wallet_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE wallet SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
    conn.commit()
    conn.close()


def get_wallet_balance(user_id):
    # Assuming you're fetching result from a database query
    query = "SELECT balance FROM wallet WHERE user_id = %s"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()  # This should return a tuple or None if no result

    # Check if result is valid
    if result:
        # If the result is a dictionary, fetch the balance using the key
        if isinstance(result, dict):
            return result.get('balance', 0.00)  # Return balance from dict, default to 0.00 if not found
        # If it's a tuple, assuming balance is in the first element
        elif isinstance(result, tuple):
            return result[0]  # Assuming balance is in the first column of the tuple
        else:
            return 0.00  # Default value if format is unexpected
    else:
        return 0.00  # Return default value if no result is found
