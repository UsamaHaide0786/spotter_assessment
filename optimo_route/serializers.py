import requests
from rest_framework import serializers
from .models import FuelPrice
from decimal import Decimal
from django.db import models

# Constants
VEHICLE_RANGE_MILES = 500
VEHICLE_MPG = 10


class FuelPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelPrice
        fields = ['city', 'state', 'price_per_gallon']


class RouteSerializer(serializers.Serializer):
    """
    Serializer for planning a route based on user input for start and finish locations.
    Validates locations and calculates route details including fuel stops and costs.
    """

    start_location = serializers.CharField()
    finish_location = serializers.CharField()
    
    def validate_start_location(self, value):
        """
        Validate that the start location is within the geographical boundaries of the USA.

        Parameters:
            value (str): The start location provided by the user.

        Returns:
            str: The validated start location.

        Raises:
            serializers.ValidationError: If the start location is not within the USA.
        """
        coords = self.geocode_location(value)
        if not self.is_within_usa(*coords):
            raise serializers.ValidationError(f"Start location '{value}' is not within the USA.")
        return value

    def validate_finish_location(self, value):
        """
        Validate that the finish location is within the geographical boundaries of the USA.

        Parameters:
            value (str): The finish location provided by the user.

        Returns:
            str: The validated finish location.

        Raises:
            serializers.ValidationError: If the finish location is not within the USA.
        """
        coords = self.geocode_location(value)
        if not self.is_within_usa(*coords):
            raise serializers.ValidationError(f"Finish location '{value}' is not within the USA.")
        return value

    def geocode_location(self, location):
        """
        Convert a given address or city name to latitude and longitude coordinates.

        Parameters:
            location (str): The address or city name to geocode.

        Returns:
            tuple: A tuple containing the latitude and longitude.

        Raises:
            ValueError: If the location cannot be geocoded or is invalid.
            requests.exceptions.HTTPError: If there is an issue with the geocoding API request.
        """
        geocode_url = f"https://nominatim.openstreetmap.org/search?format=json&q={location}"
        headers = {
            'User-Agent': 'routeplanner/1.0 (farvakhursheed786@gmail.com)'
        }
        response = requests.get(geocode_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ValueError(f"Location '{location}' could not be geocoded.")

        return float(data[0]['lat']), float(data[0]['lon'])

    def is_within_usa(self, lat, lon):
        """
        Check if the given latitude and longitude are within the geographical boundaries of the USA.

        Parameters:
            lat (float): Latitude coordinate.
            lon (float): Longitude coordinate.

        Returns:
            bool: True if the coordinates are within the USA, False otherwise.
        """
        return (24.396308 <= lat <= 49.384358) and (-125.0 <= lon <= -66.93457)

    def fetch_route_data(self, start_location, end_location):
        """
        Fetch route data from the OSRM API using the coordinates of the start and end locations.

        Parameters:
            start_location (str): The start location.
            end_location (str): The finish location.

        Returns:
            tuple: A tuple containing the route distance in miles and the route geometry.

        Raises:
            requests.exceptions.HTTPError: If there is an issue with the route API request.
        """
        start_coords = self.geocode_location(start_location)
        end_coords = self.geocode_location(end_location)

        api_url = f"https://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        params = {
            'overview': 'full',
            'geometries': 'geojson'
        }
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        route_data = response.json()

        route_distance = route_data['routes'][0]['distance'] / 1609.34
        route_geometry = route_data['routes'][0]['geometry']

        return route_distance, route_geometry

    def find_optimal_fuel_stops(self, route_distance):
        """
        Determine optimal fuel-up locations based on the vehicle's range and fuel prices.

        Parameters:
            route_distance (float): The total distance of the route in miles.

        Returns:
            list: A list of dictionaries containing optimal fuel stop information or raises an error.
        """
        fuel_prices = FuelPrice.objects.order_by('price_per_gallon')
        
        # Check if there are no fuel prices available
        if not fuel_prices.exists():
            raise ValueError("No fuel prices available to calculate the total cost.")

        optimal_stops = []
        stops_required = int(route_distance // VEHICLE_RANGE_MILES)
        current_distance = 0

        for _ in range(stops_required):
            stop = fuel_prices.first()  # Get the cheapest fuel price
            if stop is None:  # Safety check, though it should not happen now
                raise ValueError("No available fuel prices.")
            
            optimal_stops.append({
                'city': stop.city,
                'state': stop.state,
                'price_per_gallon': stop.price_per_gallon,
                'distance_from_start': current_distance + VEHICLE_RANGE_MILES
            })
            current_distance += VEHICLE_RANGE_MILES

        return optimal_stops


    def calculate_total_cost(self, route_distance):
        """
        Calculate the total fuel cost based on the route distance and average fuel price.

        Parameters:
            route_distance (float): The total distance of the route in miles.

        Returns:
            Decimal: The total fuel cost for the trip.

        Raises:
            ValueError: If no fuel prices are available to calculate the total cost.
        """
        total_gallons = Decimal(route_distance) / Decimal(VEHICLE_MPG)
        
        average_fuel_price = FuelPrice.objects.aggregate(models.Avg('price_per_gallon'))['price_per_gallon__avg']
        
        if average_fuel_price is None:
            raise ValueError("No fuel prices available to calculate the total cost.")
        
        total_cost = total_gallons * Decimal(average_fuel_price)
        
        return total_cost

    def create(self, validated_data):
        """
        Create a route plan based on validated data, including route fetching,
        optimal fuel stops, and total cost calculation.

        Parameters:
            validated_data (dict): The validated input data including start and finish locations.

        Returns:
            dict: A dictionary containing route geometry, optimal fuel stops, and total cost.
        """
        start_location = validated_data['start_location']
        end_location = validated_data['finish_location']

        route_distance, route_geometry = self.fetch_route_data(start_location, end_location)

        optimal_stops = self.find_optimal_fuel_stops(route_distance)

        total_cost = self.calculate_total_cost(route_distance)

        return {
            'route': route_geometry,
            'fuel_stops': optimal_stops,
            'total_cost': total_cost
        }