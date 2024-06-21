from flask import Flask, request, jsonify
import numpy as np
from geopy.distance import geodesic
import googlemaps
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.cluster import KMeans

# Replace with your actual API key
API_KEY = 'AIzaSyD7ifW_3VBgfX1baabxSM5dlPtInK9a2bQ'
gmaps = googlemaps.Client(key=API_KEY)

app = Flask(__name__)

def fetch_amenity_coordinates(location, amenity_name):
    try:
        places_result = gmaps.places_nearby(location=location, radius=1000, keyword=amenity_name)
        amenities_info = [
            {
                'name': place['name'],
                'address': place.get('vicinity', 'No address available'),
                'rating': place.get('rating', 0),
                'location': (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
            }
            for place in places_result.get('results', [])
        ]
        return amenities_info
    except googlemaps.exceptions.ApiError as e:
        print(f"API Error: {e}")
        return []

def calculate_distance(point1, point2):
    return geodesic(point1, point2).kilometers

def get_travel_time(origin, destination):
    try:
        directions_result = gmaps.directions(origin, destination, mode="driving")
        if directions_result:
            duration = directions_result[0]['legs'][0]['duration']['value']  # duration in seconds
            return duration / 60  # convert to minutes
        else:
            return float('inf')
    except googlemaps.exceptions.ApiError as e:
        print(f"API Error: {e}")
        return float('inf')

def score_location(location, amenities, weights, current_location, time_preference, rating_preference, max_distance, max_time):
    score = 0
    time_weight = time_preference / (time_preference + rating_preference) if (time_preference + rating_preference) != 0 else 0
    rating_weight = rating_preference / (time_preference + rating_preference) if (time_preference + rating_preference) != 0 else 0
    
    travel_time = get_travel_time(current_location, location) / max_time  # Normalize travel time
    if travel_time == float('inf'):
        return float('inf')

    for amenity, details in amenities.items():
        distances = np.array([calculate_distance(location, detail['location']) for detail in details]) / max_distance  # Normalize distances
        ratings = np.array([detail['rating'] for detail in details])
        
        if distances.size > 0:
            min_distance = distances.min()
            max_rating = ratings.max()
            score += weights[amenity] * (time_weight * (min_distance + travel_time) - rating_weight * max_rating)
    
    return score

def get_address_from_coordinates(coordinates):
    try:
        result = gmaps.reverse_geocode(coordinates)
        if result:
            return result[0]['formatted_address']
        else:
            return "No address found"
    except googlemaps.exceptions.ApiError as e:
        print(f"API Error: {e}")
        return "Error retrieving address"

def find_clusters(amenities):
    locations = []
    for amenity, details in amenities.items():
        for detail in details:
            locations.append(detail['location'])
    
    if not locations:
        return []
    
    kmeans = KMeans(n_clusters=min(len(locations), 5), random_state=0).fit(locations)
    return kmeans.cluster_centers_

@app.route('/recommend_location', methods=['POST'])
def recommend_location():
    try:
        request_data = request.get_json()

        current_location = tuple(map(float, request_data['current_location'].split(',')))
        city = request_data['city']
        country = request_data['country']
        best_location_type = request_data['best_location_type']
        time_preference = float(request_data['time_preference'])
        rating_preference = float(request_data['rating_preference'])
        min_rating = float(request_data['min_rating'])
        amenities_list = [amenity.strip() for amenity in request_data['amenities'].split(',')]

        amenities = {}
        weights = {}
        full_address = f"{city}, {country}"
        city_location = gmaps.geocode(full_address)[0]['geometry']['location']
        city_coordinates = (city_location['lat'], city_location['lng'])

        for amenity_name in amenities_list:
            locations = fetch_amenity_coordinates(city_coordinates, amenity_name)
            if locations:
                amenities[amenity_name] = locations
                weights[amenity_name] = 1.0 / len(amenities_list)
            else:
                print(f"No {amenity_name} locations found.")

        best_location_candidates = fetch_amenity_coordinates(city_coordinates, best_location_type)
        if min_rating > 0:
            best_location_candidates = [loc for loc in best_location_candidates if loc['rating'] != 0 and loc['rating'] >= min_rating]

        if not amenities or not best_location_candidates:
            return jsonify({"error": "No suitable locations found."}), 404

        cluster_centers = find_clusters(amenities)
        if not cluster_centers.any():
            return jsonify({"error": "No suitable clusters found."}), 404

        grid_search_radius = 0.005  # Define a smaller search radius around cluster centers
        num_points = 5  # Define a smaller grid size for local search

        city_grid = []
        for center in cluster_centers:
            lat_range = np.linspace(center[0] - grid_search_radius, center[0] + grid_search_radius, num=num_points)
            lon_range = np.linspace(center[1] - grid_search_radius, center[1] + grid_search_radius, num=num_points)
            city_grid.extend([(lat, lon) for lat in lat_range for lon in lon_range])

        max_distance = max([calculate_distance(current_location, loc) for loc in city_grid])
        max_time = max([get_travel_time(current_location, loc) for loc in city_grid])

        with ThreadPoolExecutor() as executor:
            future_to_location = {executor.submit(score_location, loc, amenities, weights, current_location, time_preference, rating_preference, max_distance, max_time): loc for loc in city_grid}

            best_score = float('inf')
            best_location = None
            for future in as_completed(future_to_location):
                loc = future_to_location[future]
                score = future.result()
                if score < best_score:
                    best_score = score
                    best_location = loc

        best_location_address = get_address_from_coordinates(best_location)
        best_location_detail = min(best_location_candidates, key=lambda detail: calculate_distance(best_location, detail['location']))

        response_data = {
            "best_location_address": best_location_address,
            "best_location_score": best_score,
            "distances_to_amenities": {
                amenity: {
                    "closest_distance": min([calculate_distance(best_location, detail['location']) for detail in details]),
                    "closest_name": min(details, key=lambda detail: calculate_distance(best_location, detail['location']))['name'],
                    "closest_address": min(details, key=lambda detail: calculate_distance(best_location, detail['location']))['address'],
                    "closest_rating": min(details, key=lambda detail: calculate_distance(best_location, detail['location']))['rating']
                }
                for amenity, details in amenities.items()
            },
            "chosen_best_location": {
                "name": best_location_detail['name'],
                "address": best_location_detail['address'],
                "rating": best_location_detail['rating']
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

if __name__ == "__main__":
    app.run(debug=True)
