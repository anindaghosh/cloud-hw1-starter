# import json

# def lambda_handler(event, context):
#     # TODO implement

#     messages = {
#         "messages": [
#             {
#                 "type": "unstructured",
#                 "unstructured": {
#                     "text": "I'm still under construction. Please come back later."
#                 },
#             }
#         ]
#     }

#     return messages



import json
import boto3

# Initialize Lex client
lex_client = boto3.client('lexv2-runtime', region_name='us-east-1')  # Change to your region

def lambda_handler(event, context):
    try:

        print(event)
        # Extract request body
        body = event
        
        # Extract user message from "messages" array
        messages = body.get('messages', [])
        if not messages or messages[0].get('type') != 'unstructured':
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid request format"})
            }

        user_message = messages[0]['unstructured'].get('text', '')

        if not user_message:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No text provided"})
            }

        print(f"User said: {user_message}")

        session_id = body.get('sessionId', context.aws_request_id)

        if not session_id:
            session_id = context.aws_request_id

        print(f"Session ID: {session_id}")

        session_attributes = body.get('sessionAttributes', {})

        # Send request to Lex
        lex_response = lex_client.recognize_text(
            botId='KNXCF8ZMU2',  # Replace with your Lex bot ID
            botAliasId='TSTALIASID',  # Replace with Lex bot alias ID
            localeId='en_US',
            sessionId=session_id,  # Unique session ID
            text=user_message,
            sessionState={
                'sessionAttributes': session_attributes
            }
        )

        # Extract Lex response message
        lex_messages = lex_response.get('messages', [])
        lex_message = lex_messages[0]['content'] if lex_messages else "I didn't understand that."

        print(lex_response)
        print(lex_messages)

        lex_session_attributes = lex_response.get('sessionState', {}).get('sessionAttributes', {})

        # Format API response
        api_response = {
            "session_id": session_id,
            "messages": [
                {
                    "type": "unstructured",
                    "unstructured": {
                        "text": lex_message,
                        "session_attributes": lex_session_attributes,
                    }
                }
            ]
        }

        return api_response

    except Exception as e:
        print(f"Error calling Lex: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to process request"})
        }
