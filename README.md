# geotag
This project is a Flask-based web application that recommends the best location within a city based on user preferences for amenities and travel time. The application leverages the Google Maps API to fetch amenity data and calculate travel times, as well as the KMeans clustering algorithm to find optimal clusters of amenities.

Features:
Amenity Search: Fetches nearby amenities within a specified radius using the Google Maps API, including details like name, address, and rating.
Distance & Travel Time Calculation: Calculates the distance between locations using the Geopy library and estimates travel time using the Google Maps Directions API.
Location Scoring: Scores potential locations based on user-defined weights for time and rating preferences, normalized distances, and travel times.
KMeans Clustering: Clusters amenities to identify optimal areas within the city and conducts a grid search around cluster centers to fine-tune location recommendations.
Multi-threaded Execution: Utilizes ThreadPoolExecutor for concurrent processing, speeding up the location scoring process.
Location Recommendation: Returns the best location with the highest score, including the address and details of the chosen best location.
Endpoints:
/recommend_location (POST): Accepts JSON input with details like current location, city, country, preferences for time and rating, and a list of desired amenities. Returns a recommendation for the best location based on the input criteria.
Setup:
Install Dependencies: Use pip install -r requirements.txt to install the necessary Python packages.
API Key: Replace the placeholder API key in the code with your actual Google Maps API key.
Run the Application: Use python app.py to start the Flask server.
Dependencies:
Flask: For creating the web application.
numpy: For numerical operations, including grid creation and normalization.
geopy: For calculating distances between geographical points.
googlemaps: For interacting with the Google Maps API to fetch location data and travel times.
scikit-learn: For the KMeans clustering algorithm.
Example Usage:
bash
Copy code
curl -X POST http://127.0.0.1:5000/recommend_location \
-H "Content-Type: application/json" \
-d '{
    "current_location": "28.7041,77.1025",
    "city": "Delhi",
    "country": "India",
    "best_location_type": "restaurant",
    "time_preference": 0.6,
    "rating_preference": 0.4,
    "min_rating": 4.0,
    "amenities": "supermarket, school, park"
}'
