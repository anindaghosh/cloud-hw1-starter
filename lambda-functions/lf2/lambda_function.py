import json
import boto3
import random
import os
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Initialize AWS services
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
ses = boto3.client('ses')

# Get environment variables
QUEUE_URL = os.environ['QUEUE_URL']
REGION = os.environ['AWS_REGION']
OPENSEARCH_HOST = os.environ['OPENSEARCH_HOST']
FROM_EMAIL = os.environ['FROM_EMAIL']

# Set up OpenSearch client
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    'es',
    session_token=credentials.token
)

opensearch_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

def lambda_handler(event, context):
    try:
        # Pull message from SQS queue

        print("Connecting to queue")
        print(f"Queue URL: {QUEUE_URL}")
        print(f"Region: {REGION}")

        response = sqs.receive_message(
            QueueUrl=QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=5
        )

        print(response)

        if "Messages" not in response:
            print("No messages in queue")
            return {"statusCode": 200, "body": json.dumps("No messages to process")}

        message = response["Messages"][0]
        receipt_handle = message["ReceiptHandle"]
        message_body = json.loads(message["Body"])

        # Extract required information from the message
        cuisine = message_body.get("cuisine")
        user_email = message_body.get("email")
        location = message_body.get("location", "Manhattan")
        dining_time = message_body.get("dining_time", "today")
        num_people = message_body.get("num_people", "2")

        print(message_body)

        if not cuisine or not user_email:
            print("Missing required fields in message")
            # Delete the message from the queue
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
            return {
                "statusCode": 400,
                "body": json.dumps("Missing required fields in message"),
            }

        # Get restaurant recommendation from OpenSearch
        restaurants = get_restaurants_from_opensearch(cuisine)

        if not restaurants:
            print(f"No restaurants found for cuisine: {cuisine}")
            # Delete the message from the queue
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
            return {
                "statusCode": 404,
                "body": json.dumps(f"No restaurants found for cuisine: {cuisine}"),
            }

        # Select a random restaurant
        restaurant_id = random.choice(restaurants)

        # Get detailed restaurant information from DynamoDB
        restaurant_details = get_restaurant_from_dynamodb(restaurant_id)

        if not restaurant_details:
            print(f"Restaurant details not found for ID: {restaurant_id}")
            # Delete the message from the queue
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
            return {
                "statusCode": 404,
                "body": json.dumps(f"Restaurant details not found for ID: {restaurant_id}"),
            }

        print(restaurant_details)

        # Format and send email
        send_email(
            user_email, restaurant_details, location, dining_time, num_people, cuisine
        )

        # Delete the message from the queue
        sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)

        return {
            "statusCode": 200,
            "body": json.dumps("Restaurant recommendation sent successfully"),
        }
        
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing message: {str(e)}')
        }

def get_restaurants_from_opensearch(cuisine):
    try:
        # Search for restaurants with the given cuisine
        query = {
            "query": {"match": {"Cuisine": cuisine}},
            "size": 25,  # Get up to 25 restaurants to randomly choose from
        }

        response = opensearch_client.search(body=query, index="restaurants")

        print(response)

        # Extract restaurant IDs from the response
        restaurant_ids = [
            hit["_source"]["RestaurantID"] for hit in response["hits"]["hits"]
        ]

        print(restaurant_ids)

        return restaurant_ids

    except Exception as e:
        print(f"Error searching OpenSearch: {str(e)}")
        return []


def get_restaurant_from_dynamodb(restaurant_id):
    try:
        table = dynamodb.Table("yelp-restaurants")
        response = table.get_item(Key={"business_id": restaurant_id})

        if "Item" in response:
            return response["Item"]
        else:
            return None

    except Exception as e:
        print(f"Error fetching from DynamoDB: {str(e)}")
        return None


def send_email(user_email, restaurant, location, dining_time, num_people, cuisine):
    # Format the restaurant address
    address = restaurant.get("address", {})

    # Create email subject and body
    subject = f"Your {cuisine} Restaurant Recommendation"

    body_html = f"""
    <html>
    <head></head>
    <body>
        <h1>Your Restaurant Recommendation</h1>
        <p>Hello!</p>
        <p>Based on your request for {cuisine} cuisine in {location} for {num_people} people on {dining_time}, we recommend:</p>
        <h2>{restaurant.get('name', 'Restaurant')}</h2>
        <p><strong>Address:</strong> {address}</p>
        <p><strong>Phone:</strong> {restaurant.get('phone', 'N/A')}</p>
        <p><strong>Rating:</strong> {restaurant.get('rating', 'N/A')} stars</p>
        <p><strong>Review Count:</strong> {restaurant.get('review_count', 'N/A')}</p>
        <p><strong>Price:</strong> {restaurant.get('price', 'N/A')}</p>
        <p>Enjoy your meal!</p>
    </body>
    </html>
    """

    body_text = f"""
    Your Restaurant Recommendation
    
    Hello!
    
    Based on your request for {cuisine} cuisine in {location} for {num_people} people on {dining_time}, we recommend:
    
    {restaurant.get('name', 'Restaurant')}
    Address: {address}
    Phone: {restaurant.get('phone', 'N/A')}
    Rating: {restaurant.get('rating', 'N/A')} stars
    Review Count: {restaurant.get('review_count', 'N/A')}
    Price: {restaurant.get('price', 'N/A')}
    
    Enjoy your meal!
    """

    try:
        response = ses.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [user_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body_text}, "Html": {"Data": body_html}},
            },
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
        return True

    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        return False