# --- Helper Functions for Lex Responses ---
import datetime

# --- Lex Response Helper Functions ---
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    """Elicit the next slot value."""
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': {'contentType': 'PlainText', 'content': message}
        }
    }

def confirm_intent(session_attributes, intent_name, slots, message):
    """Confirm the user's intent."""
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': {'contentType': 'PlainText', 'content': message}
        }
    }

def close(session_attributes, fulfillment_state, message):
    """Close the conversation with a completion message."""
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': {'contentType': 'PlainText', 'content': message}
        }
    }

def delegate(session_attributes, slots):
    """Delegate control to Lex for the next step in the conversation."""
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }
        
def build_validation_result(is_valid, violated_slot, message_content):
    """Build the result structure for validation."""
    if not is_valid:
        return {
            'isValid': False,
            'violatedSlot': violated_slot,
            'message': {'contentType': 'PlainText', 'content': message_content}
        }
    return {'isValid': True}

# --- Slot Validation Functions ---
def is_valid_city(city):
    """Check if the city is valid for this bot."""
    valid_cities = ['new york', 'seattle', 'san francisco', 'chicago', 'boston', 'los angeles', 'houston', 'miami']
    return city.lower() in valid_cities

def is_valid_date(date):
    """Check if the date is a valid future date and not too far in the future."""
    try:
        check_in_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        if check_in_date < datetime.date.today():
            return False, "The check-in date cannot be in the past. Can you provide a future date?"
        if check_in_date > datetime.date.today() + datetime.timedelta(days=365):
            return False, "You cannot book more than a year in advance. Please choose a closer date."
        return True, None
    except ValueError:
        return False, "The date format is invalid. Please use YYYY-MM-DD format."

def is_valid_nights(nights):
    """Check if the number of nights is a positive integer and not too large."""
    try:
        nights = int(nights)
        if nights <= 0:
            return False, "The number of nights should be a positive integer. Please provide a valid number."
        if nights > 30:
            return False, "We do not allow bookings for more than 30 nights. Please enter a shorter stay."
        return True, None
    except ValueError:
        return False, "The number of nights should be a valid integer."

def is_valid_room_type(room_type):
    """Check if the room type is valid and suggest alternatives if not."""
    valid_room_types = ['single', 'double', 'suite', 'deluxe']
    if room_type.lower() not in valid_room_types:
        return False, f"We only have Single, Double, Suite, or Deluxe rooms. Please specify one of these room types."
    return True, None

# --- Main Validation Function ---
def validate_hotel_booking(location, check_in_date, nights, room_type):
    """Perform validation for all slots with advanced checks."""
    if location and not is_valid_city(location):
        return build_validation_result(False, 'Location', f"We do not support {location} yet. Please choose from: New York, Seattle, San Francisco, Chicago, Boston, Los Angeles, Houston, or Miami.")
    
    if check_in_date:
        date_valid, date_message = is_valid_date(check_in_date)
        if not date_valid:
            return build_validation_result(False, 'CheckInDate', date_message)

    if nights:
        nights_valid, nights_message = is_valid_nights(nights)
        if not nights_valid:
            return build_validation_result(False, 'Nights', nights_message)

    if room_type:
        room_type_valid, room_type_message = is_valid_room_type(room_type)
        if not room_type_valid:
            return build_validation_result(False, 'RoomType', room_type_message)

    return {'isValid': True, 'violatedSlot': None, 'message': None}