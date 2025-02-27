import json
import boto3
import time

# Initialize client
sqs = boto3.client('sqs')
dynamodb = boto3.client('dynamodb')
user_pref_table = 'user-search-history'

# Replace with your actual SQS queue URL
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/699475932675/DiningRequestsQueue"

def get_last_search(user_email):
    response = dynamodb.get_item(
        TableName=user_pref_table,
        Key={"email": {"S": user_email}}
    )
    
    if 'Item' in response:
        return {
            "location": response['Item'].get("location", {}).get("S"),
            "cuisine": response['Item'].get("cuisine", {}).get("S"),
            "dining_time": response['Item'].get("dining_time", {}).get("S"),
            "num_people": response['Item'].get("num_people", {}).get("S"),
            "email": response['Item'].get("email", {}).get("S")
        }

    return None

def store_last_search(session_id, body):

    user_email = body['email']
    location = body['location']
    cuisine = body['cuisine']
    dining_time = body['dining_time']
    num_people = body['num_people']

    dynamodb.put_item(
        TableName=user_pref_table,
        Item={
            "session_id": {"S": session_id},
            "email": {"S": user_email},
            "location": {"S": location},
            "cuisine": {"S": cuisine},
            "dining_time": {"S": dining_time},
            "num_people": {"S": num_people},
            "timestamp": {"N": str(int(time.time()))}
        }
    )

    return

def lambda_handler(event, context):

    print("EVENT")
    print(event)

    print("CONTEXT")
    print(context)


    intent_name = event['sessionState']['intent']['name']

    if intent_name == "GreetingIntent":
        return generate_response("Hi there, how can I help?")

    elif intent_name == "DiningSuggestionsIntent":
        return handle_dining_suggestions(event)

    elif intent_name == "ThankYouIntent":
        return generate_response("You're welcome! Have a great day!")

    else:
        return generate_response("I'm not sure how to handle that request.")

def handle_dining_suggestions(event):
    slots = event['sessionState']['intent']['slots']
    
    # Extract slot values

    def get_slot_value(slot_name):
        """Retrieve interpreted slot value safely, handling None values."""
        slot = slots.get(slot_name)
        if slot and slot.get('value'):
            return slot['value'].get('interpretedValue')
        return None  # Return None if the slot or value is missing

    email = get_slot_value('Email')

    if email:
        last_search = get_last_search(email)
        if last_search:
            print(last_search)
            
            # Create message payload
            message = {
                "location": last_search['location'],
                "cuisine": last_search['cuisine'],
                "dining_time": last_search['dining_time'],
                "num_people": last_search['num_people'],
                "email": last_search['email'],
                "insertedAtTimestamp": int(time.time())
            }

            # Push to SQS queue
            sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message))

            return {
                "sessionState": {
                    "dialogAction": {
                        "type": "Close"
                    },
                    "intent": event['sessionState']['intent']
                },
                "messages": [
                    {
                        "contentType": "PlainText",
                        "content": f"Thanks! I've sent your last search to your email inbox for location {last_search['location']} and cuisine {last_search['cuisine']}."
                    }
                ]
            }


    location = get_slot_value('Location')

    # Validate the data, ensure location is only Manhattan and request location again
    
    if location and location.lower() != 'manhattan':
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "ElicitSlot",
                    "slotToElicit": "Location"
                },
                "intent": event['sessionState']['intent']
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": "Please enter a valid location."
                }
            ]
        }


    cuisine = get_slot_value('Cuisine')
    dining_time = get_slot_value('DiningTime')
    num_people = get_slot_value('NumberOfPeople')
    

    missing_slots = []

    if not email:
        missing_slots.append({'slot' : 'Email', 'message': "Please provide your email address" })
    if not location:
        missing_slots.append({'slot' : 'Location', 'message': "What city or city area are you looking to dine in?" })
    if not cuisine:
        missing_slots.append({'slot' : 'Cuisine', 'message': "What cuisine are you looking for? (Ex. Indian, Italian, Chinese, etc.)" })
    if not dining_time:
        missing_slots.append({'slot' : 'DiningTime', 'message': "What time?" })
    if not num_people:
        missing_slots.append({'slot' : 'NumberOfPeople', 'message': "How many people in your party?" })

    if missing_slots:
        return {
            "sessionState": {
                "dialogAction": {
                    "type": "ElicitSlot",
                    "slotToElicit": missing_slots[0]['slot']  # Ask for the first missing slot
                },
                "intent": event['sessionState']['intent']
            },
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": missing_slots[0]['message']
                }
            ]
        }


    # Create message payload
    message = {
        "location": location,
        "cuisine": cuisine,
        "dining_time": dining_time,
        "num_people": num_people,
        "email": email,
        "insertedAtTimestamp": int(time.time())
    }

    # Push to SQS queue
    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message))

    store_last_search(event['sessionId'], message)

    # Confirmation message
    return generate_response(f"Thanks! We received your request for {cuisine} food in {location} for {num_people} people at {dining_time}. We'll email suggestions to {email} soon!")

def generate_response(message):
    return {
        "sessionState": {
            "dialogAction": {
                "type": "Close"
            },
            "intent": {
                "name": "DiningSuggestionsIntent",
                "state": "Fulfilled"
            }
        },
        "messages": [
            {
                "contentType": "PlainText",
                "content": message
            }
        ]
    }
