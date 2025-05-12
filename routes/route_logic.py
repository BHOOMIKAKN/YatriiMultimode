from calendar import weekday
from datetime import datetime, timedelta
from db.connection import get_connection
import pymysql
from collections import defaultdict
from copy import deepcopy

def find_all_routes(source, destination, travel_date, max_hops=4):
    weekday = datetime.strptime(travel_date, "%Y-%m-%d").strftime('%a')
    print(f"Travel Date: {travel_date}, Weekday: {weekday}")

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    query = """
    SELECT r.id, r.source, r.destination, r.duration, r.cost, r.operating_days,
           r.seats_available, r.departure_time, r.arrival_time, tm.mode
    FROM routes r
    JOIN transport_modes tm ON r.mode_id = tm.id
    WHERE (r.operating_days = 'Daily' OR FIND_IN_SET(%s, r.operating_days) > 0)
      AND r.seats_available > 0
    ORDER BY r.departure_time
    """

    cursor.execute(query, (weekday,))
    all_routes = cursor.fetchall()
    conn.close()

    print(f"Fetched Routes: {len(all_routes)}")

    def normalize_time_field(time_value):
        """Convert timedelta, datetime, or str to 'HH:MM' string."""
        if isinstance(time_value, str):
            return time_value  # assume already in HH:MM format
        elif isinstance(time_value, timedelta):
            total_minutes = int(time_value.total_seconds() // 60)
            hours, minutes = divmod(total_minutes, 60)
            return f"{hours:02d}:{minutes:02d}"
        elif isinstance(time_value, datetime):
            return time_value.strftime("%H:%M")
        else:
            raise TypeError(f"Unexpected time format: {type(time_value)}")

    # Build graph
    graph = defaultdict(list)
    for route in all_routes:
        route['departure_time'] = normalize_time_field(route['departure_time'])
        route['arrival_time'] = normalize_time_field(route['arrival_time'])
        graph[route['source']].append(route)

    all_paths = []
    route_id_counter = 1  # Unique route ID for each full path

    def dfs(current_city, path, visited, total_time, total_cost):
        nonlocal route_id_counter
        if len(path) > max_hops:
            return
        if current_city == destination and path:
            all_paths.append({
                "id": route_id_counter,
                "route": deepcopy(path),
                "total_time": total_time,
                "total_cost": total_cost
            })
            route_id_counter += 1
            return
        for route in graph.get(current_city, []):
            next_city = route['destination']
            if next_city not in visited:
                visited.add(next_city)
                dfs(
                    next_city,
                    path + [route.copy()],
                    visited,
                    total_time + route['duration'],
                    total_cost + float(route['cost'])
                )
                visited.remove(next_city)

    dfs(source, [], set([source]), 0, 0.0)

    return all_paths
