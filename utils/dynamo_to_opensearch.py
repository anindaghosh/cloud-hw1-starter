import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from requests_aws4auth import AWS4Auth
import json

# Set up AWS credentials and region
region = "us-east-1"  # Your region
service = "es"

# Get credentials
credentials = boto3.Session(profile_name="default").get_credentials()

print(credentials.access_key)
print(credentials.secret_key)

# awsauth = AWS4Auth(
#     credentials.access_key,
#     credentials.secret_key,
#     region,
#     service,
#     session_token=credentials.token,
# )

awsauth = AWSV4SignerAuth(credentials, region, service)

# OpenSearch endpoint - replace with your endpoint
host = "search-restaurants-qybycszp3udr7u2iioq7aekp3e.us-east-1.es.amazonaws.com"  # Your domain endpoint

# Create OpenSearch client
opensearch_client = OpenSearch(
    hosts=[{"host": host, "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

opensearch_client.info()


# Create index if it doesn't exist
if not opensearch_client.indices.exists(index="restaurants"):
    # Create index with mapping
    index_body = {
        "mappings": {
            "properties": {"id": {"type": "keyword"}, "cuisine": {"type": "keyword"}}
        }
    }

    response = opensearch_client.indices.create(index="restaurants", body=index_body)

    print(f"Index created: {response}")


# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("yelp-restaurants")


# Scan DynamoDB Table (Fetch all records)
response = table.scan()
restaurants = response.get("Items", [])

for restaurant in restaurants:
    try:
        # Extract only required fields

        print(restaurant)

        restaurant_id = restaurant.get("business_id")
        cuisine = restaurant.get("cuisine")

        print(restaurant_id, cuisine)

        if not restaurant_id or not cuisine:
            continue  # Skip if data is incomplete

        # Prepare document for OpenSearch
        document = {"RestaurantID": restaurant_id, "Cuisine": cuisine}

        # Index the document in OpenSearch
        opensearch_client.index(index="restaurants", id=restaurant_id, body=document)

    except Exception as e:
        print(f"Error processing {restaurant}: {str(e)}")


print("Done!")
