# Email Tracking Service

A FastAPI-based email tracking service that uses Resend for sending emails and includes tracking capabilities. The service tracks email opens, recipient locations, and forwarding information.

## Features

- 📧 Send emails with tracking capabilities
- 📍 Track recipient location (city, region, country, coordinates)
- ⏱️ Record exact time of email opens
- 🔄 Track email forwarding
- 📊 Store tracking data in JSON format
- 🔒 Secure tracking with unique tracking IDs

## Prerequisites

- Python 3.8+
- Resend API key
- IPInfo API key (for location tracking)
- ngrok or similar service for exposing the tracking endpoint

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd email-tracking-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```env
RESEND_API_KEY=your_resend_key
LIVE_API=your_ngrok_url
IPINFO_TOKEN=your_ipinfo_token
```

## Usage

### Starting the Server

Run the FastAPI server:
```bash
python main.py
```

The server will start on `http://localhost:8000`.

### API Endpoints

1. **Send Email with Tracking**
```bash
curl -X POST "http://localhost:8000/send-email" \
-H "Content-Type: application/json" \
-d '{
    "to": "recipient@example.com",
    "subject": "Test Email with Tracking",
    "html": "<h1>Test Email</h1><p>This email contains a tracking pixel.</p>"
}'
```

Response:
```json
{
    "message": "Email sent successfully",
    "email_id": "email_id_from_resend",
    "tracking_id": "unique_tracking_id"
}
```

2. **Get Tracking Data**
```bash
curl "http://localhost:8000/tracking-data/{tracking_id}"
```

Response:
```json
{
    "email_id": "unique_tracking_id",
    "recipient_email": "recipient@example.com",
    "open_time": "2024-03-21T10:00:00",
    "location": {
        "ip": "1.2.3.4",
        "city": "New York",
        "region": "New York",
        "country": "US",
        "loc": "40.7128,-74.0060",
        "org": "ISP Name",
        "timezone": "America/New_York"
    },
    "forwarded_to": ["forwarded@example.com"],
    "forwarded_data": [
        {
            "open_time": "2024-03-21T11:00:00",
            "location": {
                "ip": "5.6.7.8",
                "city": "London",
                "region": "England",
                "country": "GB",
                "loc": "51.5074,-0.1278",
                "org": "ISP Name",
                "timezone": "Europe/London"
            },
            "email": "forwarded@example.com"
        }
    ]
}
```

### Tracking Data Storage

Tracking data is stored in `data/tracking_data.json`. The file is automatically created and updated when:
- A new email is sent
- An email is opened
- An email is forwarded

## How It Works

1. **Email Sending**:
   - Generates a unique tracking ID
   - Creates a tracking pixel URL
   - Embeds the tracking pixel in the email HTML
   - Sends the email using Resend

2. **Email Tracking**:
   - When the email is opened, the tracking pixel is loaded
   - The service records:
     - Time of opening
     - Recipient's location
     - Forwarding information (if applicable)

3. **Location Tracking**:
   - Uses IPInfo to get detailed location data
   - Tracks city, region, country, coordinates
   - Includes ISP and timezone information

## Security Considerations

- Tracking IDs are unique UUIDs
- No personal data is stored beyond email addresses
- Location data is based on IP addresses only
- Tracking data is stored locally in JSON format

## Troubleshooting

1. **Email Not Sending**:
   - Verify your Resend API key
   - Check your email quota
   - Ensure the recipient email is valid

2. **Tracking Not Working**:
   - Verify your ngrok URL is correct
   - Check if the tracking endpoint is accessible
   - Ensure the IPInfo token is valid

3. **Location Data Missing**:
   - Verify your IPInfo token
   - Check if the IP address is valid
   - Ensure the service has internet access

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 