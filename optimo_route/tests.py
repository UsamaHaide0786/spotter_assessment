import pytest
from rest_framework import status
from rest_framework.test import APIClient
from .models import FuelPrice
from .views import RoutePlannerView


@pytest.mark.django_db
class TestRoutePlannerView:
    """
    Test suite for the RoutePlannerView API endpoint.
    This class contains various test cases to ensure the route planning functionality works as expected.
    """

    def setup_method(self):
        """ 
        Create an instance of the API client for testing and set up initial data.
        """
        self.client = APIClient()

    def test_invalid_start_location(self):
        """
        Test case for an invalid start location.
        
        This test sends a POST request with an invalid start location (outside the USA).
        It verifies that the response status is 400 BAD REQUEST and checks that
        the appropriate error message is returned.
        """
        data = {
            'start_location': 'London, UK',
            'finish_location': 'New York, NY'
        }
        response = self.client.post('/api/route/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'start_location' in response.data

        assert response.data['start_location'][0].code == 'invalid'
        assert response.data['start_location'][0] == "Start location 'London, UK' is not within the USA."

    def test_invalid_finish_location(self):
        """
        Test case for an invalid finish location.

        This test sends a POST request with a valid start location and an invalid finish location.
        It verifies that the response status is 400 BAD REQUEST and checks that 
        the appropriate error message is returned.
        """
        data = {
            'start_location': 'Seattle, WA',
            'finish_location': 'Tokyo, Japan'
        }
        response = self.client.post('/api/route/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'finish_location' in response.data

        assert response.data['finish_location'][0].code == 'invalid'
        assert response.data['finish_location'][0] == "Finish location 'Tokyo, Japan' is not within the USA."

    def test_no_fuel_prices(self):
        """
        Test case for handling scenarios where no fuel prices are available.

        This test clears any existing FuelPrice objects, then sends a POST request
        with valid locations. It verifies that the response status is 400 BAD REQUEST
        and checks that the appropriate error message is returned.
        """
        FuelPrice.objects.all().delete()  # Clear existing fuel prices

        data = {
            'start_location': 'Chicago, IL',
            'finish_location': 'Miami, FL'
        }
        response = self.client.post('/api/route/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert response.data['error'] == "No fuel prices available to calculate the total cost."

    def test_multiple_fuel_stops(self):
        """ 
        Test case to ensure the API returns multiple fuel stops when needed.

        This test checks that with valid locations and multiple fuel prices, 
        the response status is 200 OK and contains more than one fuel stop.
        """
        FuelPrice.objects.create(city='Las Vegas', state='NV', price_per_gallon=3.00)
        FuelPrice.objects.create(city='Phoenix', state='AZ', price_per_gallon=2.50)

        data = {
            'start_location': 'Los Angeles, CA',
            'finish_location': 'New York, NY'
        }
        response = self.client.post('/api/route/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['fuel_stops']) > 1

    def test_exact_vehicle_range(self):
        """ 
        Test case to verify behavior when the route distance equals the vehicle's range.

        This test checks that with a route distance matching the vehicle's 
        maximum range, the response status is 200 OK and includes fuel stops.
        """
        FuelPrice.objects.create(city='Las Vegas', state='NV', price_per_gallon=3.00)

        data = {
            'start_location': 'Las Vegas, NV',
            'finish_location': 'Denver, CO'
        }
        response = self.client.post('/api/route/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'fuel_stops' in response.data
