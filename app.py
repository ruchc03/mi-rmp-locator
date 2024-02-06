from flask import Flask, render_template, request
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import json
import pandas as pd

app = Flask(__name__)

# Load the restaurant data from the provided JSON-like format
with open('restaurants.json') as file:
    restaurants = json.load(file)

# Convert the data into a pandas DataFrame for easy manipulation
df = pd.DataFrame(restaurants)

# Function to calculate distance between two locations
def calculate_distance(user_location, restaurant_location):
    if restaurant_location is None:
        return float('inf')  # Assign a large distance if restaurant location is not available
    return geodesic(user_location, (restaurant_location.latitude, restaurant_location.longitude)).miles

# Function to validate user input as a valid address
def validate_address(address):
    geolocator = Nominatim(user_agent="geoapi")
    location = geolocator.geocode(address)
    return location is not None

# Function to geocode restaurant addresses and store the coordinates with retry mechanism
def geocode_with_retry(address):
    geolocator = Nominatim(user_agent="geoapi")
    max_retries = 3
    for retry in range(1, max_retries + 1):
        try:
            location = geolocator.geocode(address, timeout=10)
            if location and location.latitude is not None and location.longitude is not None:
                return location
        except (GeocoderTimedOut, ValueError):
            print(f"Geocoding attempt {retry} failed for address: {address}. Retrying...")
            continue
    print(f"Geocoding failed after {max_retries} retries for address: {address}.")
    return None

# Function to geocode restaurant addresses and store the coordinates
def geocode_restaurant_addresses():
    for index, row in df.iterrows():
        location = geocode_with_retry(row['Address'])
        if location:
            df.at[index, 'Latitude'] = location.latitude
            df.at[index, 'Longitude'] = location.longitude

# Route for the root URL
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle user input and display sorted table
@app.route('/calculate_distance', methods=['POST'])
def calculate_distance_route():
    user_input = request.form['location_input']

    if validate_address(user_input):
        user_location = geocode_with_retry(user_input)

        if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
            geocode_restaurant_addresses()

        df['Distance'] = df.apply(lambda row: calculate_distance((user_location.latitude, user_location.longitude),
                                                                (row['Latitude'], row['Longitude'])), axis=1)
        df_sorted = df.sort_values(by='Distance')
        return render_template('index.html', restaurants=df_sorted.to_html(classes='table table-striped', index=False))
    else:
        return render_template('index.html', restaurants=df.to_html(classes='table table-striped', index=False),
                               error_message='Invalid address. Please enter a valid address.')

if __name__ == '__main__':
    app.run(debug=True)
