from mcp.server.fastmcp import FastMCP
import httpx
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import uuid
import json
from dataclasses import dataclass, asdict
from enum import Enum
import os
from pathlib import Path
import logging
import sys

# Google Calendar API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
GOOGLE_CALENDAR_AVAILABLE = True

# Initialize FastMCP server
mcp = FastMCP("playo")

# Configure logging to stderr (MCP uses stdout for protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

PLAYO_API_URL = "https://api.playo.io/activity-public/list/location"

# Google Calendar API configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
# Use absolute paths based on script location to ensure files are found
SCRIPT_DIR = Path(__file__).parent.absolute()
CREDENTIALS_FILE = str(SCRIPT_DIR / 'google_calendar_credentials.json')
TOKEN_FILE = str(SCRIPT_DIR / 'google_calendar_token.json')

# Constants for sports
SPORTS = {
    "badminton": "SP5",
    "football": "SP2",
}

# Timing slots
TIMINGS = {
    "morning": 0,    # 12 AM to 9 AM
    "day": 1,        # 9 AM to 4 PM
    "evening": 2,    # 4 PM to 9 PM
    "night": 3,      # 9 PM to 12 PM
}

# Skill levels
SKILLS = {
    "beginner": 0,
    "amateur": 1,
    "intermediate": 2,
    "advanced": 3,
    "professional": 4,
}


# ============================================================================
# Database Models and Enums
# ============================================================================

class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class Payment:
    payment_id: str
    booking_id: str
    amount: float
    currency: str
    status: str
    payment_method: str
    transaction_id: str
    timestamp: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Booking:
    booking_id: str
    user_name: str
    user_email: str
    user_phone: str
    activity_id: str
    activity_name: str
    venue_name: str
    venue_address: str
    sport_type: str
    date: str
    time_slot: str
    duration_hours: float
    price_per_hour: float
    total_price: float
    num_players: int
    status: str
    payment_id: Optional[str]
    google_calendar_event_id: Optional[str]
    created_at: str
    
    def to_dict(self):
        return asdict(self)


# ============================================================================
# In-Memory Database (Simulated)
# ============================================================================

class Database:
    """Simulated database for storing bookings and payments"""
    
    def __init__(self):
        self.bookings: Dict[str, Booking] = {}
        self.payments: Dict[str, Payment] = {}
        self.venues: Dict[str, Dict] = {}  # Cache venue info from API
        
    def add_booking(self, booking: Booking) -> str:
        self.bookings[booking.booking_id] = booking
        return booking.booking_id
    
    def get_booking(self, booking_id: str) -> Optional[Booking]:
        return self.bookings.get(booking_id)
    
    def update_booking_status(self, booking_id: str, status: str) -> bool:
        if booking_id in self.bookings:
            self.bookings[booking_id].status = status
            return True
        return False
    
    def add_payment(self, payment: Payment) -> str:
        self.payments[payment.payment_id] = payment
        return payment.payment_id
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        return self.payments.get(payment_id)
    
    def update_payment_status(self, payment_id: str, status: str) -> bool:
        if payment_id in self.payments:
            self.payments[payment_id].status = status
            return True
        return False
    
    def get_user_bookings(self, user_email: str) -> List[Booking]:
        return [b for b in self.bookings.values() if b.user_email == user_email]
    
    def cache_venue(self, activity_id: str, venue_data: dict):
        self.venues[activity_id] = venue_data
    
    def get_cached_venue(self, activity_id: str) -> Optional[dict]:
        return self.venues.get(activity_id)


# Initialize database
db = Database()


# ============================================================================
# Google Calendar API Helper Functions
# ============================================================================

def get_google_calendar_service():
    """
    Authenticate and return Google Calendar API service
    
    Returns:
        Google Calendar API service object or None if authentication fails
    """
    if not GOOGLE_CALENDAR_AVAILABLE:
        return None
    
    creds = None
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            logger.error(f"Error loading token: {e}")
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Error in OAuth flow: {e}")
                return None
        
        # Save the credentials for the next run
        try:
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            logger.error(f"Error saving token: {e}")
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building service: {e}")
        return None


def parse_time_slot(time_slot_str: str, date_str: str) -> tuple:
    """
    Parse time slot string and convert to datetime objects
    
    Args:
        time_slot_str: Time slot string like "6:00 PM - 7:00 PM"
        date_str: Date string in YYYY-MM-DD format
    
    Returns:
        Tuple of (start_datetime, end_datetime) as ISO format strings
    """
    # Parse the date
    date_obj = datetime.strptime(date_str, "%Y-%m-%d") if 'T' not in date_str else datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    
    # Parse time slot
    times = time_slot_str.split('-')
    start_time_str = times[0].strip()
    end_time_str = times[1].strip() if len(times) > 1 else None
    
    # Parse start time
    try:
        # Handle formats like "6:00 PM", "18:00", "6 PM"
        if 'AM' in start_time_str or 'PM' in start_time_str:
            start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
        else:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
        
        start_datetime = datetime.combine(date_obj.date(), start_time)
        
        # Parse end time if provided
        if end_time_str:
            if 'AM' in end_time_str or 'PM' in end_time_str:
                end_time = datetime.strptime(end_time_str, "%I:%M %p").time()
            else:
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
            end_datetime = datetime.combine(date_obj.date(), end_time)
        else:
            # Default to 1 hour duration
            end_datetime = start_datetime + timedelta(hours=1)
        
        # Convert to ISO format with timezone
        # Using local timezone (IST for India)
        return (
            start_datetime.isoformat(),
            end_datetime.isoformat()
        )
    
    except Exception as e:
        # Fallback to simple parsing
        return (
            date_obj.isoformat(),
            (date_obj + timedelta(hours=1)).isoformat()
        )


# Initialize Google Calendar on startup
def initialize_google_calendar():
    """Initialize and check Google Calendar setup on startup"""
    if GOOGLE_CALENDAR_AVAILABLE:
        logger.info("="*70)
        logger.info("🗓️  Google Calendar API Status")
        logger.info("="*70)
        
        if os.path.exists(CREDENTIALS_FILE):
            logger.info(f"✅ Credentials file found: {CREDENTIALS_FILE}")
            
            # Try to authenticate
            service = get_google_calendar_service()
            if service:
                logger.info("✅ Google Calendar authenticated successfully!")
                try:
                    # Test API access
                    service.calendarList().list(maxResults=1).execute()
                    logger.info("✅ Calendar API access confirmed")
                except Exception as e:
                    logger.warning(f"⚠️  Calendar API test failed: {e}")
            else:
                logger.warning("⚠️  Authentication pending. Run setup when ready.")
                logger.info(f"   Browser will open for OAuth when you create first event.")
        else:
            logger.warning(f"⚠️  Credentials file not found: {CREDENTIALS_FILE}")
            logger.info("   Download from: https://console.cloud.google.com/apis/credentials")
            logger.info("   See setup instructions in the code comments")
        
        logger.info("="*70)
    else:
        logger.warning("⚠️  Google Calendar libraries not installed")
        logger.info("   Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")


# Don't initialize at module level - this would interfere with MCP stdio protocol
# Initialization will happen lazily when Google Calendar functions are first called


# ============================================================================
# MCP Tools - Activity Search
# ============================================================================

@mcp.tool()
async def search_activities(
    lat: float,
    lng: float,
    date: str = None,
    sports: list[str] = None,
    timings: list[int] = None,
    skills: list[int] = None,
    city_radius: int = 50,
    sort_by: str = "distance",
    page: int = 0
) -> dict:
    """
    Search for sports activities on Playo
    
    Args:
        lat: Latitude of the search location (e.g., 12.9715987 for Bangalore)
        lng: Longitude of the search location (e.g., 77.59456269999998 for Bangalore)
        date: Date to search for activities (ISO format, e.g., "2025-11-24")
        sports: List of sport IDs. Call get_available_sports() first to get valid sport IDs (e.g., ["SP5", "SP2"])
        timings: List of timing slot IDs. Call get_timing_slots() first to get valid IDs (e.g., [0, 1, 2, 3])
        skills: List of skill level IDs. Call get_skill_levels() first to get valid IDs (e.g., [0, 1, 2, 3, 4])
        city_radius: Search radius in kilometers (default: 50)
        sort_by: Sort results by "distance" or "time_date" (default: "distance")
        page: Page number for pagination (default: 0)
    
    Returns:
        Dictionary containing search results with activities. If the price is 0, then the activity payment is to be done on-site.
    """
    # Prepare date - handle both YYYY-MM-DD and full ISO format
    if date:
        if 'T' not in date:
            date_str = f"{date}T00:00:00.000Z"
        else:
            date_str = date
    else:
        date_str = datetime.now().strftime("%Y-%m-%dT00:00:00.000Z")
    
    # Use sport IDs directly (no conversion needed)
    sport_ids = sports if sports else []
    
    # Use timing IDs directly (no conversion needed)
    timing_ids = timings if timings else [0, 1, 2]  # Default: morning, day, evening
    
    # Use skill IDs directly (no conversion needed)
    skill_ids = skills if skills else [1]  # Default: amateur
    
    # Prepare request payload
    payload = {
        "booking": False,
        "cityRadius": city_radius,
        "date": [date_str],
        "gameTimeActivities": False,
        "lastId": "",
        "lat": lat,
        "lng": lng,
        "page": page,
        "skill": skill_ids,
        "sportId": sport_ids,
        "timing": timing_ids
    }
    
    # Add sort_by filter if specified
    if sort_by in ["distance", "time_date"]:
        payload["appliedFilters"] = {
            "sortandfilter": {
                "sort_by": sort_by
            }
        }
    
    # Make API request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            PLAYO_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_available_sports() -> dict:
    """
    Get list of available sports that can be searched
    
    Returns:
        Dictionary with available sports and their IDs
    """
    return {
        "sports": [
            {"name": "Badminton", "id": "SP5", "key": "badminton"},
            {"name": "Football", "id": "SP2", "key": "football"}
        ]
    }


@mcp.tool()
async def get_timing_slots() -> dict:
    """
    Get list of available timing slots for activities
    
    Returns:
        Dictionary with timing slots and their descriptions
    """
    return {
        "timings": [
            {"name": "Morning", "id": 0, "key": "morning", "time": "12 AM to 9 AM"},
            {"name": "Day", "id": 1, "key": "day", "time": "9 AM to 4 PM"},
            {"name": "Evening", "id": 2, "key": "evening", "time": "4 PM to 9 PM"},
            {"name": "Night", "id": 3, "key": "night", "time": "9 PM to 12 PM"}
        ]
    }


@mcp.tool()
async def get_skill_levels() -> dict:
    """
    Get list of available skill levels
    
    Returns:
        Dictionary with skill levels and their IDs
    """
    return {
        "skills": [
            {"name": "Beginner", "id": 0, "key": "beginner"},
            {"name": "Amateur", "id": 1, "key": "amateur"},
            {"name": "Intermediate", "id": 2, "key": "intermediate"},
            {"name": "Advanced", "id": 3, "key": "advanced"},
            {"name": "Professional", "id": 4, "key": "professional"}
        ]
    }


# ============================================================================
# Booking Functions
# ============================================================================

@mcp.tool()
async def create_booking(
    user_name: str,
    user_email: str,
    user_phone: str,
    activity_id: str,
    activity_name: str,
    venue_name: str,
    venue_address: str,
    sport_type: str,
    date: str,
    time_slot: str,
    duration_hours: float = 1.0,
    price_per_hour: float = 500.0,
    num_players: int = 1
) -> dict:
    """
    Create a new booking for a sports activity
    
    Args:
        user_name: Name of the person booking
        user_email: Email address for confirmation
        user_phone: Contact phone number
        activity_id: ID of the activity from search results
        activity_name: Name of the activity
        venue_name: Name of the venue
        venue_address: Full address of the venue
        sport_type: Type of sport (e.g., "Badminton", "Football")
        date: Date of booking (YYYY-MM-DD)
        time_slot: Time slot (e.g., "6:00 PM - 7:00 PM")
        duration_hours: Duration in hours (default: 1.0)
        price_per_hour: Price per hour in INR (default: 500)
        num_players: Number of players (default: 1)
    
    Returns:
        Dictionary with booking details and payment information
    """
    # Generate unique IDs
    booking_id = f"BK{uuid.uuid4().hex[:8].upper()}"
    
    # Calculate total price
    total_price = price_per_hour * duration_hours
    
    # Create booking object
    booking = Booking(
        booking_id=booking_id,
        user_name=user_name,
        user_email=user_email,
        user_phone=user_phone,
        activity_id=activity_id,
        activity_name=activity_name,
        venue_name=venue_name,
        venue_address=venue_address,
        sport_type=sport_type,
        date=date,
        time_slot=time_slot,
        duration_hours=duration_hours,
        price_per_hour=price_per_hour,
        total_price=total_price,
        num_players=num_players,
        status=BookingStatus.PENDING.value,
        payment_id=None,
        google_calendar_event_id=None,
        created_at=datetime.now().isoformat()
    )
    
    # Save to database
    db.add_booking(booking)
    
    return {
        "success": True,
        "booking_id": booking_id,
        "message": "Booking created successfully. Please proceed with payment.",
        "booking_details": booking.to_dict(),
        "next_step": f"Use process_payment(booking_id='{booking_id}', payment_method='...') to complete the booking"
    }


@mcp.tool()
async def process_payment(
    booking_id: str,
    payment_method: str = "upi",
    upi_id: Optional[str] = None,
    card_number: Optional[str] = None
) -> dict:
    """
    Process payment for a booking (Simulated)
    
    Args:
        booking_id: Booking ID to pay for
        payment_method: Payment method - 'upi', 'card', 'netbanking', 'wallet'
        upi_id: UPI ID if payment_method is 'upi'
        card_number: Last 4 digits of card if payment_method is 'card'
    
    Returns:
        Dictionary with payment status and details
    """
    # Get booking
    booking = db.get_booking(booking_id)
    if not booking:
        return {
            "success": False,
            "error": "Booking not found"
        }
    
    if booking.status != BookingStatus.PENDING.value:
        return {
            "success": False,
            "error": f"Booking is already {booking.status}. Cannot process payment."
        }
    
    # Generate payment ID and transaction ID
    payment_id = f"PAY{uuid.uuid4().hex[:8].upper()}"
    transaction_id = f"TXN{uuid.uuid4().hex[:12].upper()}"
    
    # Create payment object
    payment = Payment(
        payment_id=payment_id,
        booking_id=booking_id,
        amount=booking.total_price,
        currency="INR",
        status=PaymentStatus.PROCESSING.value,
        payment_method=payment_method,
        transaction_id=transaction_id,
        timestamp=datetime.now().isoformat()
    )
    
    # Save payment
    db.add_payment(payment)
    
    # Simulate payment processing (100% success rate)
    import random
    success = random.random() < 1.0 # 100% success rate
    
    if success:
        # Update payment status
        db.update_payment_status(payment_id, PaymentStatus.SUCCESS.value)
        
        # Update booking status and link payment
        booking.status = BookingStatus.CONFIRMED.value
        booking.payment_id = payment_id
        db.bookings[booking_id] = booking
        
        payment_details = {
            "upi_id": upi_id,
            "card_last4": card_number[-4:] if card_number else None
        }
        
        return {
            "success": True,
            "payment_id": payment_id,
            "transaction_id": transaction_id,
            "status": "success",
            "amount": booking.total_price,
            "currency": "INR",
            "payment_method": payment_method,
            "payment_details": payment_details,
            "booking_status": "confirmed",
            "message": "Payment successful! Booking confirmed.",
            "next_step": f"Use add_to_google_calendar(booking_id='{booking_id}') to add this to your calendar"
        }
    else:
        # Payment failed
        db.update_payment_status(payment_id, PaymentStatus.FAILED.value)
        
        return {
            "success": False,
            "payment_id": payment_id,
            "transaction_id": transaction_id,
            "status": "failed",
            "error": "Payment failed. Please try again.",
            "message": "Payment processing failed. Please check your payment details and try again."
        }


@mcp.tool()
async def add_to_google_calendar(
    booking_id: str, 
    timezone: str = "Asia/Kolkata",
    send_notifications: bool = True,
    add_reminder_minutes: int = 30
) -> dict:
    """
    Add confirmed booking to Google Calendar using actual Google Calendar API
    
    Args:
        booking_id: ID of the confirmed booking
        timezone: Timezone for the event (default: Asia/Kolkata for India)
        send_notifications: Send email notifications to attendees
        add_reminder_minutes: Add reminder X minutes before event (default: 30)
    
    Returns:
        Dictionary with Google Calendar event details
    """
    # Get booking
    booking = db.get_booking(booking_id)
    if not booking:
        return {
            "success": False,
            "error": "Booking not found"
        }
    
    if booking.status != BookingStatus.CONFIRMED.value:
        return {
            "success": False,
            "error": f"Booking must be confirmed before adding to calendar. Current status: {booking.status}"
        }
    
    # Check if Google Calendar is available
    if not GOOGLE_CALENDAR_AVAILABLE:
        return {
            "success": False,
            "error": "Google Calendar libraries not installed",
            "install_command": "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        }
    
    # Get Google Calendar service
    service = get_google_calendar_service()
    if not service:
        return {
            "success": False,
            "error": "Failed to authenticate with Google Calendar",
            "help": f"Please ensure {CREDENTIALS_FILE} exists. Download it from Google Cloud Console.",
            "setup_url": "https://console.cloud.google.com/apis/credentials"
        }
    
    # Parse date and time
    try:
        start_time, end_time = parse_time_slot(booking.time_slot, booking.date)
    except Exception as e:
        return {
            "success": False,
            "error": f"Error parsing date/time: {str(e)}"
        }
    
    # Create event details
    event = {
        'summary': f"{booking.sport_type} at {booking.venue_name}",
        'location': booking.venue_address,
        'description': f"""🏸 Sports Booking Details

📝 Booking ID: {booking.booking_id}
🎮 Activity: {booking.activity_name}
🏟️ Venue: {booking.venue_name}
📍 Address: {booking.venue_address}
👥 Players: {booking.num_players}
⏱️ Duration: {booking.duration_hours} hour(s)
💰 Amount Paid: ₹{booking.total_price}

📞 Contact: {booking.user_phone}
📧 Email: {booking.user_email}

Booked via Playo MCP Server""",
        'start': {
            'dateTime': start_time,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': timezone,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': add_reminder_minutes},
                {'method': 'popup', 'minutes': add_reminder_minutes},
            ],
        },
        'attendees': [
            {'email': booking.user_email}
        ],
        'sendNotifications': send_notifications,
        'colorId': '4'  # Flamingo color for sports events
    }
    
    try:
        # Create the event
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            sendNotifications=send_notifications
        ).execute()
        
        # Update booking with calendar event ID
        booking.google_calendar_event_id = created_event['id']
        db.bookings[booking_id] = booking
        
        # Get event link
        event_link = created_event.get('htmlLink', '')
        
        return {
            "success": True,
            "event_id": created_event['id'],
            "message": "Booking successfully added to Google Calendar",
            "event_details": {
                "summary": created_event['summary'],
                "location": created_event.get('location', ''),
                "start_time": created_event['start'].get('dateTime', ''),
                "end_time": created_event['end'].get('dateTime', ''),
                "timezone": timezone,
                "calendar_link": event_link,
                "ical_uid": created_event.get('iCalUID', ''),
                "reminder_minutes": add_reminder_minutes
            },
            "booking_id": booking_id
        }
    
    except HttpError as error:
        return {
            "success": False,
            "error": f"Google Calendar API error: {error}",
            "error_details": str(error)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create calendar event: {str(e)}"
        }


@mcp.tool()
async def get_booking_details(booking_id: str) -> dict:
    """
    Get details of a specific booking
    
    Args:
        booking_id: ID of the booking
    
    Returns:
        Dictionary with complete booking information
    """
    booking = db.get_booking(booking_id)
    if not booking:
        return {
            "success": False,
            "error": "Booking not found"
        }
    
    result = {
        "success": True,
        "booking": booking.to_dict()
    }
    
    # Add payment details if available
    if booking.payment_id:
        payment = db.get_payment(booking.payment_id)
        if payment:
            result["payment"] = payment.to_dict()
    
    return result


@mcp.tool()
async def get_user_bookings(user_email: str) -> dict:
    """
    Get all bookings for a user
    
    Args:
        user_email: Email address of the user
    
    Returns:
        Dictionary with list of user's bookings
    """
    bookings = db.get_user_bookings(user_email)
    
    return {
        "success": True,
        "user_email": user_email,
        "total_bookings": len(bookings),
        "bookings": [b.to_dict() for b in bookings]
    }


def setup_google_calendar() -> dict:
    """
    Setup instructions and status check for Google Calendar integration
    
    Returns:
        Dictionary with setup status and instructions
    """
    status = {
        "google_calendar_libraries": GOOGLE_CALENDAR_AVAILABLE,
        "credentials_file_exists": os.path.exists(CREDENTIALS_FILE),
        "token_file_exists": os.path.exists(TOKEN_FILE),
        "authenticated": False
    }
    
    # Test if we can get the service
    if GOOGLE_CALENDAR_AVAILABLE:
        service = get_google_calendar_service()
        status["authenticated"] = service is not None
    
    instructions = """
╔══════════════════════════════════════════════════════════════════════╗
║              Google Calendar API Setup Instructions                  ║
╚══════════════════════════════════════════════════════════════════════╝

📦 STEP 1: Install Required Libraries
────────────────────────────────────────────────────────────────────
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client

🌐 STEP 2: Create Google Cloud Project & Enable API
────────────────────────────────────────────────────────────────────
1. Open: https://console.cloud.google.com/projectcreate
2. Project name: "Playo MCP Server" (or any name)
3. Click "CREATE"

4. Enable Google Calendar API:
   - Open: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
   - Click "ENABLE"
   - Wait for activation (few seconds)

🔐 STEP 3: Configure OAuth Consent Screen
────────────────────────────────────────────────────────────────────
1. Open: https://console.cloud.google.com/apis/credentials/consent
2. Choose "External" user type → Click "CREATE"
3. Fill required fields:
   ✓ App name: Playo MCP Server
   ✓ User support email: <your email>
   ✓ Developer contact: <your email>
4. Click "SAVE AND CONTINUE"
5. Scopes page: Click "ADD OR REMOVE SCOPES"
   - Search: "Google Calendar API"
   - Select: ".../auth/calendar" (Read/write access)
   - Click "UPDATE" → "SAVE AND CONTINUE"
6. Test users: Add your email → "SAVE AND CONTINUE"
7. Summary: Click "BACK TO DASHBOARD"

🔑 STEP 4: Create OAuth 2.0 Credentials
────────────────────────────────────────────────────────────────────
1. Open: https://console.cloud.google.com/apis/credentials
2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Playo Calendar Desktop"
5. Click "CREATE"
6. On success popup:
   - Click "DOWNLOAD JSON" button
   - Save the downloaded file
7. Rename the downloaded file to: google_calendar_credentials.json
8. Move it to: """ + os.path.abspath('.') + """

✅ STEP 5: Verify & Authenticate
────────────────────────────────────────────────────────────────────
Run this command again: setup_google_calendar()
- Browser will open automatically
- Sign in with your Google account
- Click "Allow" to grant calendar access
- Token will be saved as: """ + TOKEN_FILE + """

🎯 STEP 6: Test Integration
────────────────────────────────────────────────────────────────────
Test with: list_calendar_events()
This should show your upcoming calendar events!

📝 Quick Links:
- Project Dashboard: https://console.cloud.google.com/home/dashboard
- API Credentials: https://console.cloud.google.com/apis/credentials
- OAuth Consent: https://console.cloud.google.com/apis/credentials/consent
"""
    
    return {
        "status": status,
        "setup_complete": all([
            status["google_calendar_libraries"],
            status["credentials_file_exists"],
            status["authenticated"]
        ]),
        "instructions": instructions,
        "next_steps": _get_next_steps(status),
        "current_directory": os.path.abspath('.'),
        "credentials_file_path": os.path.abspath(CREDENTIALS_FILE),
        "quick_links": {
            "create_project": "https://console.cloud.google.com/projectcreate",
            "enable_calendar_api": "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com",
            "configure_oauth": "https://console.cloud.google.com/apis/credentials/consent",
            "create_credentials": "https://console.cloud.google.com/apis/credentials"
        }
    }


def _get_next_steps(status: dict) -> list:
    """Helper to provide next steps based on status"""
    steps = []
    
    if not status["google_calendar_libraries"]:
        steps.append("Install Google Calendar libraries: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    
    if not status["credentials_file_exists"]:
        steps.append(f"Download OAuth credentials from Google Cloud Console and save as '{CREDENTIALS_FILE}'")
    
    if status["google_calendar_libraries"] and status["credentials_file_exists"] and not status["authenticated"]:
        steps.append("Run this function again to trigger OAuth authentication flow")
    
    if status["authenticated"]:
        steps.append("✅ Setup complete! You can now use add_to_google_calendar() to create events")
    
    return steps


@mcp.tool()
async def list_calendar_events(
    max_results: int = 10,
    days_ahead: int = 7
) -> dict:
    """
    List upcoming events from Google Calendar
    
    Args:
        max_results: Maximum number of events to return (default: 10)
        days_ahead: Number of days ahead to fetch events (default: 7)
    
    Returns:
        Dictionary with list of upcoming calendar events
    """
    if not GOOGLE_CALENDAR_AVAILABLE:
        return {
            "success": False,
            "error": "Google Calendar libraries not installed"
        }
    
    service = get_google_calendar_service()
    if not service:
        return {
            "success": False,
            "error": "Not authenticated with Google Calendar",
            "help": "Run setup_google_calendar() first"
        }
    
    try:
        # Get current time and time ahead
        now = datetime.utcnow().isoformat() + 'Z'
        time_max = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            formatted_events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'location': event.get('location', ''),
                'description': event.get('description', '')[:100] + '...' if event.get('description', '') else '',
                'link': event.get('htmlLink', '')
            })
        
        return {
            "success": True,
            "total_events": len(formatted_events),
            "days_ahead": days_ahead,
            "events": formatted_events
        }
    
    except HttpError as error:
        return {
            "success": False,
            "error": f"Google Calendar API error: {error}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list events: {str(e)}"
        }


@mcp.tool()
async def cancel_booking(booking_id: str, reason: str = "User cancelled") -> dict:
    """
    Cancel a booking and process refund
    
    Args:
        booking_id: ID of the booking to cancel
        reason: Reason for cancellation
    
    Returns:
        Dictionary with cancellation status
    """
    booking = db.get_booking(booking_id)
    if not booking:
        return {
            "success": False,
            "error": "Booking not found"
        }
    
    if booking.status == BookingStatus.CANCELLED.value:
        return {
            "success": False,
            "error": "Booking is already cancelled"
        }
    
    if booking.status == BookingStatus.COMPLETED.value:
        return {
            "success": False,
            "error": "Cannot cancel completed booking"
        }
    
    # Update booking status
    db.update_booking_status(booking_id, BookingStatus.CANCELLED.value)
    
    # Process refund if payment was made
    refund_details = None
    if booking.payment_id:
        payment = db.get_payment(booking.payment_id)
        if payment and payment.status == PaymentStatus.SUCCESS.value:
            db.update_payment_status(booking.payment_id, PaymentStatus.REFUNDED.value)
            refund_details = {
                "refund_amount": booking.total_price,
                "refund_status": "processed",
                "refund_id": f"REF{uuid.uuid4().hex[:8].upper()}",
                "estimated_days": "5-7 business days"
            }
    
    return {
        "success": True,
        "booking_id": booking_id,
        "status": "cancelled",
        "reason": reason,
        "refund": refund_details,
        "message": "Booking cancelled successfully" + (" and refund initiated" if refund_details else "")
    }


if __name__ == "__main__":
    # Initialize Google Calendar before running server
    initialize_google_calendar()
    # Run the server
    mcp.run()