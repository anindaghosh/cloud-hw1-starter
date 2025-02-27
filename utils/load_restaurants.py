import boto3
from decimal import Decimal
from utils import get_restaurants


dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("yelp-restaurants")


def convert_floats_to_decimals(data):
    if isinstance(data, dict):
        return {k: convert_floats_to_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats_to_decimals(v) for v in data]
    elif isinstance(data, float):
        return Decimal(str(data))
    return data


def store_in_dynamodb(restaurants):
    with table.batch_writer() as batch:
        for restaurant in restaurants:
            restaurant_data = convert_floats_to_decimals(restaurant)
            batch.put_item(Item=restaurant_data)


# Example usage
cuisines = [
    "Italian",
    "Mexican",
    "Japanese",
    "Indian",
    "Chinese",
    "Thai",
    "Mediterranean",
    "Continental",
    "Korean",
    "French",
    "Continental",
    "American",
]


for cuisine in cuisines:
    data = get_restaurants(cuisine=cuisine, location="Manhattan")

    # print(data)

    store_in_dynamodb(data)
    print(f"Stored {len(data)} {cuisine} restaurants in DynamoDB.")

    # break
