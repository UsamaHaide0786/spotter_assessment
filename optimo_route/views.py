from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RouteSerializer
from rest_framework.generics import GenericAPIView
import requests


class RouteView(GenericAPIView):
    """
    API view for planning a route from a start location to a finish location,
    including fuel stop suggestions and total fuel cost calculation.
    """

    serializer_class = RouteSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests to plan a route.

        Validates input data and calculates route distance, optimal fuel stops,
        and total fuel cost based on user input.

        Parameters:
            request: The HTTP request object containing the start and finish locations.

        Returns:
            Response: A Response object containing the route data, fuel stops, and total cost.

        Raises:
            HTTPError: If there is an error fetching route data from external APIs.
            ValueError: If geocoding fails or no fuel prices are available.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = serializer.create(serializer.validated_data)

            return Response(result, status=status.HTTP_200_OK)
        except requests.exceptions.HTTPError as e:
            return Response(
                {"error": f"Failed to fetch route data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
