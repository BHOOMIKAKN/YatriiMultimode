from calendar import weekday
from datetime import datetime

from db.connection import get_connection
import pymysql
from collections import defaultdict


def find_all_routes(source, destination, travel_date, max_hops=4):
    weekday = datetime.strptime(travel_date, "%Y-%m-%d").strftime('%a')  # 'Mon', 'Tue', etc.
    print(f"Travel Date: {travel_date}, Weekday: {weekday}")  # Debug the values

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Debugging: Check the raw query and parameters
    print(f"Executing query with parameters: ('%s', '%s')")

    # Get all valid routes for that day, using FIND_IN_SET for exact day match
    query = """
    SELECT r.id, r.*, tm.mode
    FROM routes r
    JOIN transport_modes tm ON r.mode_id = tm.id
    WHERE (r.operating_days = 'Daily' OR FIND_IN_SET(%s, r.operating_days) > 0)
    AND r.seats_available > 0
    ORDER BY r.departure_time
    """
    cursor.execute(query, (weekday,))

    all_routes = cursor.fetchall()

    conn.close()

    print(f"Fetched Routes: {len(all_routes)}")  # Debug number of fetched routes

    # Build graph
    graph = defaultdict(list)
    for route in all_routes:
        graph[route['source']].append(route)

    all_paths = []

    def dfs(current_city, path, visited, total_time, total_cost):
        if len(path) > max_hops:
            return
        if current_city == destination and path:
            all_paths.append({
                "route": path[:],
                "total_time": total_time,
                "total_cost": total_cost
            })
            return
        for route in graph.get(current_city, []):
            next_city = route['destination']
            if next_city not in visited:
                visited.add(next_city)
                dfs(
                    next_city,
                    path + [route],
                    visited,
                    total_time + route['duration'],
                    total_cost + float(route['cost'])
                )
                visited.remove(next_city)

    dfs(source, [], set([source]), 0, 0.0)

    return all_paths
