# routeplanner/management/commands/load_fuel_prices.py
import csv
from django.core.management.base import BaseCommand
from optimo_route.models import FuelPrice


class Command(BaseCommand):
    help = 'Load fuel prices from CSV'

    def handle(self, *args, **kwargs):
        with open('fuel-prices-for-be-assessment.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                FuelPrice.objects.create(
                    city=row['City'],
                    state=row['State'],
                    price_per_gallon=float(row['Retail Price'])
                )
