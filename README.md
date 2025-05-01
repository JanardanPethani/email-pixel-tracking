# Email Tracking System

This is a FastAPI application that implements email tracking using a tracking pixel. The system tracks when emails are opened, the location of the recipient, and if the email has been forwarded.

## Features

- Track when emails are opened
- Track recipient location using ipinfo.io (city, region, country, coordinates, ISP)
- Track forwarded emails
- Track forwarded email opens and locations
- Simple API endpoints for sending and tracking emails

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your API keys:
```
RESEND_API_KEY=your_resend_api_key
IPINFO_TOKEN=your_ipinfo_token
```

3. Run the application:
```bash
uvicorn main:app --reload
```

## API Endpoints

### Send Email
```
POST /send-email
```
Request body:
```json
{
    "to": "recipient@example.com",
    "subject": "Test Email",
    "html": "<h1>Hello</h1><p>This is a test email</p>",
    "from_email": "your-email@gmail.com"
}
```

### Get Tracking Data
```
GET /tracking-data/{tracking_id}
```

## How it Works

1. When you send an email, a unique tracking ID is generated
2. A transparent 1x1 pixel image is embedded in the email
3. When the email is opened, the pixel is loaded, triggering the tracking endpoint
4. The system records:
   - Time and date of opening
   - Detailed location information (city, region, country, coordinates, ISP)
   - Forwarding information (if applicable)

## Location Tracking

The system uses ipinfo.io to provide detailed location information:
- City
- Region/State
- Country
- Latitude and Longitude
- ISP/Organization
- Timezone

## Notes

- This implementation uses in-memory storage. For production use, you should implement a proper database.
- The tracking pixel works best with HTML emails.
- Make sure to replace "your-email@gmail.com" with your actual Gmail address in the code.
- You need to sign up for an ipinfo.io account to get an API token for location tracking. 