# app_fastapi.py

from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, timedelta
import sqlite3
import csv
import re

app = FastAPI()

DATABASE_NAME = "restaurants.db"
CSV_FILE_NAME = "restaurants.csv"

# Initialize the SQLite database


def initialize_database():
    """Create the SQLite database and populate it with data from the CSV file."""

    restaurant_data = process_data()

    # SQLite database connection
    conn = sqlite3.connect('restaurant_data.db')
    cursor = conn.cursor()

    # Create a table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurant_hours (
            restaurant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_name TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            open_time TEXT NOT NULL,
            close_time TEXT NOT NULL
        )
    ''')

    # Insert data into the table
    for restaurant_name, opening_hours in restaurant_data.items():
        for day, times in opening_hours.items():
            open_time = times['open']
            close_time = times['close']
            cursor.execute('''
                INSERT INTO restaurant_hours (restaurant_name, day_of_week, open_time, close_time)
                VALUES (?, ?, ?, ?)
            ''', (restaurant_name, day, open_time, close_time))

    # Commit changes and close the connection
    conn.commit()
    conn.close()

# Helper function to parse opening hours


def convert_to_24_hour_format(original_time):

    am_pm_mapping = {'am': 'AM', 'pm': 'PM'}

    if ":" in original_time:

        updated_time = datetime.strptime(original_time, '%I:%M %p')
    else:
        updated_time = datetime.strptime(original_time, '%I %p')

    updated_time_24h = updated_time.strftime('%H:%M:%S')

    return updated_time_24h


def get_missing_days(start_day, end_day):
    all_days = ['Sun', 'Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat']
    start_index = all_days.index(start_day)
    end_index = all_days.index(end_day)
    day_range = all_days[start_index:end_index + 1]
    return day_range


def process_data():
    all_restaurant_record = {}

    with open(CSV_FILE_NAME, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            hours = row['Hours'].split("/")
            rest_name = row['Restaurant Name']
            days_pattern = re.compile(r'(Mon|Tues|Wed|Thu|Fri|Sat|Sun)')
            curr_record = {}
            for h in hours:
                ranged_days = re.search(r'([a-zA-Z]+)-([a-zA-Z]+)', h)
                if ranged_days:
                    start_day, end_day = ranged_days.groups()
                    filled_in_days = get_missing_days(
                        start_day, end_day)

                    for d in days_pattern.findall(h):
                        if d not in filled_in_days:
                            filled_in_days.append(d)

                    curr_all_days = filled_in_days

                else:
                    curr_all_days = days_pattern.findall(h)

                time_begins_at = re.search(r'\d', h).start()
                time_string = h[time_begins_at:]

                start_time = convert_to_24_hour_format(
                    time_string.split("-")[0].strip())
                end_time = convert_to_24_hour_format(
                    time_string.split("-")[1].strip())

                curr_record.update(
                    {day: {"open": start_time, "close": end_time} for day in curr_all_days})
            all_restaurant_record.update({rest_name: curr_record})

    return all_restaurant_record


# Get open restaurants for a given datetime


def get_open_restaurants(dt):
    """Query the database for open restaurants based on the provided datetime."""
    day_of_week = dt.strftime('%a').lower()

    current_time = dt.strftime('%H:%M:%S').lstrip('0').lower()
    day_before = (dt - timedelta(days=1)).strftime('%a').lower()

    if current_time.startswith(":"):
        current_time = '00:' + current_time[1:]

    normal_ = ''' select distinct(restaurant_name) from restaurant_hours where 
            LOWER(SUBSTR(day_of_week, 1, 3)) 
            = "{}" and time("{}") BETWEEN TIME(open_time) AND TIME(close_time);'''.format(day_of_week, current_time)

    conn = sqlite3.connect("restaurant_data.db")

    c = conn.cursor()
    c.execute(normal_)

    res_1 = c.fetchall()

    if len(res_1) > 0:
        return [row[0] for row in res_1]

    later_midnight = ''' SELECT  distinct(restaurant_name) from restaurant_hours where LOWER(SUBSTR(day_of_week, 1, 3))  = "{}" and TIME(close_time) < TIME(open_time) and TIME(close_time) <> "00:00:00" and TIME(close_time) > TIME("{}") '''.format(
        day_before, current_time)

    conn = sqlite3.connect("restaurant_data.db")
    c = conn.cursor()
    c.execute(later_midnight)

    res_2 = c.fetchall()

    return [row[0] for row in res_2]


# API endpoint


@app.get("/open-restaurants/")
async def open_restaurants(datetime_param: str = Query(..., description="Datetime in the format %Y-%m-%d %H:%M:%S")):
    """FastAPI endpoint to get a list of open restaurants based on the provided datetime.

    Args:
        datetime (str): Datetime string in the format %Y-%m-%d %H:%M:%S.

    Returns:
        dict: A dictionary containing the list of open restaurants.

    Examples:
        To get open restaurants for January 1, 2023, at 12:00 PM:
        ```
        curl -X 'GET' \
          'http://127.0.0.1:5000/open-restaurants/?datetime=2023-01-01%2012:00:00' \
          -H 'accept: application/json'
        ```

        Response:
        ```
        {"open_restaurants":["The Cowfish Sushi Burger Bar","Morgan St Food Hall","Beasley's Chicken + Honey"]}
        ```

        Note: Replace the URL with the appropriate server address and datetime values.
    """
    try:
        dt = datetime.strptime(datetime_param, '%Y-%m-%d %H:%M:%S')
        open_restaurants = get_open_restaurants(dt)
        return {"open_restaurants": open_restaurants}

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="CSV file not found.")

    except csv.Error:
        raise HTTPException(
            status_code=500, detail="Error parsing CSV file. Ensure it is properly formatted.")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == '__main__':
    initialize_database()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
