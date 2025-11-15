# Reddit, Playo, and IP Geolocation MCP Servers

A collection of three MCP (Model Context Protocol) servers providing Reddit integration, Playo sports venue finder with booking system, and IP geolocation services.

## 📹 Demo Video

Watch the demo video to see all three MCP servers in action:

**[Demo Video](https://youtu.be/IJUluYlRUhg)**

##  Features

### 1. Reddit MCP Server (`main.py`)

Comprehensive Reddit integration for searching, browsing, and reading Reddit content.

- **Search Subreddits**: Search for posts within specific subreddits
- **Get Hot Posts**: Retrieve trending posts from any subreddit
- **Get New Posts**: Fetch the latest posts from subreddits
- **Get Top Posts**: Access top posts filtered by time period (hour, day, week, month, year, all)
- **Get Post Content**: Retrieve full content of specific posts
- **Get Post Comments**: Read comments from Reddit posts
- **User Posts**: Get recent posts from any Reddit user
- **User Comments**: Retrieve recent comments from any Reddit user

### 2. Playo MCP Server (`playo_mcp.py`)

Complete sports venue finder and booking system with Google Calendar integration.

- **Search Activities**: Find sports venues (Badminton, Football) near you
- **Booking System**: Create, manage, and cancel bookings
- **Payment Processing**: Simulated payment processing (UPI, Card, Net Banking, Wallet)
- **Google Calendar Integration**: Automatically add bookings to Google Calendar
- **Booking Management**: View booking details and user booking history
- **Filter Options**: Search by sport type, timing slots, skill levels, and location

### 3. IP Geolocation MCP Server (`ip_mcp.py`)

IP address geolocation and network information lookup.

- **IP Lookup**: Get geolocation information for any IP address (IPv4 or IPv6)
- **Current Location**: Get location information for the current request IP
- **Detailed Information**: Country, city, coordinates, ISP, timezone, and more
- **Multi-language Support**: Support for multiple languages (en, de, es, pt-BR, fr, ja, zh-CN, ru)
- **Custom Fields**: Request specific fields to reduce response size


##  Available Tools

### Reddit MCP Server Tools

#### `search_subreddit`
Search for posts in a specific subreddit.

**Parameters:**
- `subreddit` (str): Name of the subreddit (e.g., 'python', 'machinelearning')
- `query` (str): Search query
- `limit` (int, optional): Number of results to return (default: 10, max: 100)

#### `get_subreddit_hot`
Get hot/trending posts from a subreddit.

**Parameters:**
- `subreddit` (str): Name of the subreddit
- `limit` (int, optional): Number of posts to return (default: 10, max: 100)

#### `get_subreddit_new`
Get newest posts from a subreddit.

**Parameters:**
- `subreddit` (str): Name of the subreddit
- `limit` (int, optional): Number of posts to return (default: 10, max: 100)

#### `get_subreddit_top`
Get top posts from a subreddit filtered by time period.

**Parameters:**
- `subreddit` (str): Name of the subreddit
- `time_filter` (str, optional): Time period - 'hour', 'day', 'week', 'month', 'year', 'all' (default: 'day')
- `limit` (int, optional): Number of posts to return (default: 10, max: 100)

#### `get_post_content`
Get full content of a specific post.

**Parameters:**
- `subreddit` (str): Name of the subreddit
- `post_id` (str): The post ID (from search results)

#### `get_post_comments`
Get comments from a specific post.

**Parameters:**
- `subreddit` (str): Name of the subreddit
- `post_id` (str): The post ID
- `limit` (int, optional): Number of top-level comments to return (default: 20)

#### `get_user_posts`
Get recent posts from a Reddit user.

**Parameters:**
- `username` (str): Reddit username (without u/)
- `limit` (int, optional): Number of posts to return (default: 10, max: 100)

#### `get_user_comments`
Get recent comments from a Reddit user.

**Parameters:**
- `username` (str): Reddit username (without u/)
- `limit` (int, optional): Number of comments to return (default: 10, max: 100)

### Playo MCP Server Tools

#### `search_activities`
Search for sports activities on Playo.

**Parameters:**
- `lat` (float): Latitude of the search location
- `lng` (float): Longitude of the search location
- `date` (str, optional): Date to search for activities (ISO format, e.g., "2025-11-24")
- `sports` (list[str], optional): List of sport IDs (e.g., ["SP5", "SP2"])
- `timings` (list[int], optional): List of timing slot IDs (0=morning, 1=day, 2=evening, 3=night)
- `skills` (list[int], optional): List of skill level IDs (0=beginner, 1=amateur, 2=intermediate, 3=advanced, 4=professional)
- `city_radius` (int, optional): Search radius in kilometers (default: 50)
- `sort_by` (str, optional): Sort results by "distance" or "time_date" (default: "distance")
- `page` (int, optional): Page number for pagination (default: 0)

#### `get_available_sports`
Get list of available sports that can be searched.

**Returns:** Dictionary with available sports and their IDs

#### `get_timing_slots`
Get list of available timing slots for activities.

**Returns:** Dictionary with timing slots and their descriptions

#### `get_skill_levels`
Get list of available skill levels.

**Returns:** Dictionary with skill levels and their IDs

#### `create_booking`
Create a new booking for a sports activity.

**Parameters:**
- `user_name` (str): Name of the person booking
- `user_email` (str): Email address for confirmation
- `user_phone` (str): Contact phone number
- `activity_id` (str): ID of the activity from search results
- `activity_name` (str): Name of the activity
- `venue_name` (str): Name of the venue
- `venue_address` (str): Full address of the venue
- `sport_type` (str): Type of sport (e.g., "Badminton", "Football")
- `date` (str): Date of booking (YYYY-MM-DD)
- `time_slot` (str): Time slot (e.g., "6:00 PM - 7:00 PM")
- `duration_hours` (float, optional): Duration in hours (default: 1.0)
- `price_per_hour` (float, optional): Price per hour in INR (default: 500)
- `num_players` (int, optional): Number of players (default: 1)

#### `process_payment`
Process payment for a booking (Simulated).

**Parameters:**
- `booking_id` (str): Booking ID to pay for
- `payment_method` (str, optional): Payment method - 'upi', 'card', 'netbanking', 'wallet' (default: 'upi')
- `upi_id` (str, optional): UPI ID if payment_method is 'upi'
- `card_number` (str, optional): Last 4 digits of card if payment_method is 'card'

#### `add_to_google_calendar`
Add confirmed booking to Google Calendar.

**Parameters:**
- `booking_id` (str): ID of the confirmed booking
- `timezone` (str, optional): Timezone for the event (default: "Asia/Kolkata")
- `send_notifications` (bool, optional): Send email notifications (default: True)
- `add_reminder_minutes` (int, optional): Add reminder X minutes before event (default: 30)

#### `get_booking_details`
Get details of a specific booking.

**Parameters:**
- `booking_id` (str): ID of the booking

#### `get_user_bookings`
Get all bookings for a user.

**Parameters:**
- `user_email` (str): Email address of the user

#### `list_calendar_events`
List upcoming events from Google Calendar.

**Parameters:**
- `max_results` (int, optional): Maximum number of events to return (default: 10)
- `days_ahead` (int, optional): Number of days ahead to fetch events (default: 7)

#### `cancel_booking`
Cancel a booking and process refund.

**Parameters:**
- `booking_id` (str): ID of the booking to cancel
- `reason` (str, optional): Reason for cancellation (default: "User cancelled")

### IP Geolocation MCP Server Tools

#### `get_ip_location`
Get geolocation information for an IP address.

**Parameters:**
- `ip` (str, optional): IP address to lookup (IPv4 or IPv6). Leave empty for current IP.
- `fields` (str, optional): Comma-separated list of fields (e.g., 'country,city,lat,lon'). Leave empty for all fields.
- `lang` (str, optional): Language code for city/region names (en, de, es, pt-BR, fr, ja, zh-CN, ru) (default: "en")

#### `get_current_location`
Get geolocation information for the current request IP.

**Returns:** Dictionary with location details for the current IP