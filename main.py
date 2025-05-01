from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
import resend
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid
import logging
import ipinfo
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
PIXEL_GIF_BYTES = bytes.fromhex('47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b')
PIXEL_MEDIA_TYPE = "image/gif"
TRACKING_DATA_FILE = Path("data/tracking_data.json")
DATA_DIR = Path("data")

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    html: str

class LocationInfo:
    def __init__(self, ipinfo_token: str):
        self.handler = ipinfo.getHandler(ipinfo_token)

    def get_details(self, ip_address: str) -> Dict[str, Any]:
        """Get detailed location information using ipinfo.io"""
        try:
            details = self.handler.getDetails(ip_address)
            return {
                "ip": ip_address,
                "city": details.city,
                "region": details.region,
                "country": details.country,
                "loc": details.loc,
                "org": details.org,
                "timezone": details.timezone
            }
        except Exception as e:
            logger.error(f"Error getting location details for IP {ip_address}: {str(e)}")
            return {"ip": ip_address, "error": str(e)}

class TrackingDataManager:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.data = self._load_data()

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        DATA_DIR.mkdir(exist_ok=True)

    def _load_data(self) -> Dict[str, Any]:
        """Load tracking data from JSON file"""
        try:
            self._ensure_data_dir()
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    return self._deserialize_dates(data)
            return {}
        except Exception as e:
            logger.error(f"Error loading tracking data: {str(e)}")
            return {}

    def _deserialize_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ISO format dates back to datetime objects"""
        for tracking_info in data.values():
            if tracking_info.get('open_time'):
                tracking_info['open_time'] = datetime.fromisoformat(tracking_info['open_time'])
            if tracking_info.get('forwarded_data'):
                for forwarded in tracking_info['forwarded_data']:
                    if forwarded.get('open_time'):
                        forwarded['open_time'] = datetime.fromisoformat(forwarded['open_time'])
        return data

    def _serialize_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime objects to ISO format strings"""
        data_to_save = {}
        for tracking_id, tracking_info in data.items():
            data_to_save[tracking_id] = tracking_info.copy()
            if tracking_info.get('open_time'):
                data_to_save[tracking_id]['open_time'] = tracking_info['open_time'].isoformat()
            if tracking_info.get('forwarded_data'):
                data_to_save[tracking_id]['forwarded_data'] = [
                    {**fwd, 'open_time': fwd['open_time'].isoformat()}
                    if fwd.get('open_time') else fwd
                    for fwd in tracking_info['forwarded_data']
                ]
        return data_to_save

    def save_data(self):
        """Save tracking data to JSON file"""
        try:
            self._ensure_data_dir()
            with open(self.data_file, 'w') as f:
                json.dump(self._serialize_dates(self.data), f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tracking data: {str(e)}")

    def get_tracking_data(self, tracking_id: str) -> Dict[str, Any]:
        """Get tracking data for a specific ID"""
        if tracking_id not in self.data:
            raise HTTPException(status_code=404, detail="Tracking ID not found")
        return self.data[tracking_id]

    def initialize_tracking(self, tracking_id: str, recipient_email: str):
        """Initialize tracking data for a new email"""
        self.data[tracking_id] = {
            "email_id": tracking_id,
            "recipient_email": recipient_email,
            "open_time": None,
            "location": None,
            "forwarded_to": [],
            "forwarded_data": []
        }
        self.save_data()

    def update_tracking(self, tracking_id: str, location: Dict[str, Any], is_forwarded: bool = False):
        """Update tracking data for an email open"""
        if tracking_id not in self.data:
            logger.warning(f"Tracking ID not found: {tracking_id}")
            return

        if is_forwarded:
            forwarded_to = location["ip"]
            self.data[tracking_id]["forwarded_to"].append(forwarded_to)
            self.data[tracking_id]["forwarded_data"].append({
                "open_time": datetime.utcnow(),
                "location": location,
                "email": forwarded_to
            })
        else:
            self.data[tracking_id]["open_time"] = datetime.utcnow()
            self.data[tracking_id]["location"] = location

        self.save_data()

class EmailTracker:
    def __init__(self, resend_api_key: str, live_api: str, ipinfo_token: str):
        resend.api_key = resend_api_key
        self.live_api = live_api
        self.location_info = LocationInfo(ipinfo_token)
        self.tracking_manager = TrackingDataManager(TRACKING_DATA_FILE)

    def create_tracking_pixel(self, tracking_id: str) -> str:
        """Create tracking pixel URL"""
        return f"{self.live_api}/track/{tracking_id}"

    def add_tracking_to_html(self, html: str, tracking_pixel_url: str) -> str:
        """Add tracking pixel to HTML content"""
        tracking_div = f'<div style="background: url({tracking_pixel_url}); width: 1px; height: 1px; position: absolute; top: 0; left: 0;"></div>'
        return f"{html}{tracking_div}"

    def send_email(self, to: str, subject: str, html: str) -> Dict[str, Any]:
        """Send email with tracking"""
        try:
            tracking_id = str(uuid.uuid4())
            tracking_pixel_url = self.create_tracking_pixel(tracking_id)
            html_with_tracking = self.add_tracking_to_html(html, tracking_pixel_url)

            self.tracking_manager.initialize_tracking(tracking_id, to)

            params = {
                "from": "Resend Pixel Test <onboarding@resend.dev>",
                "to": [to],
                "subject": subject,
                "html": html_with_tracking
            }

            email = resend.Emails.send(params)
            logger.info(f"Email sent successfully to {to}")

            return {
                "message": "Email sent successfully",
                "email_id": email.get('id'),
                "tracking_id": tracking_id
            }
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def track_email_open(self, tracking_id: str, request: Request) -> Response:
        """Track email open and return tracking pixel"""
        try:
            client_ip = request.client.host
            location = self.location_info.get_details(client_ip)
            
            # Check if this is a forwarded email
            is_forwarded = bool(request.headers.get("referer") and "mail.google.com" in request.headers.get("referer", ""))
            
            self.tracking_manager.update_tracking(tracking_id, location, is_forwarded)

            headers = {
                "Content-Type": PIXEL_MEDIA_TYPE,
                "Content-Length": str(len(PIXEL_GIF_BYTES)),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            return Response(content=PIXEL_GIF_BYTES, status_code=200, headers=headers)
        except Exception as e:
            logger.error(f"Error processing tracking pixel: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

# Initialize FastAPI app
app = FastAPI(title="Email Tracking Service API")

# Initialize email tracker
email_tracker = EmailTracker(
    resend_api_key=os.getenv("RESEND_API_KEY"),
    live_api=os.getenv("LIVE_API"),
    ipinfo_token=os.getenv("IPINFO_TOKEN")
)

@app.post("/send-email")
async def send_email(email_request: EmailRequest):
    return email_tracker.send_email(
        to=email_request.to,
        subject=email_request.subject,
        html=email_request.html
    )

@app.api_route("/track/{tracking_id}", methods=["GET", "HEAD"])
async def track_email(tracking_id: str, request: Request):
    return email_tracker.track_email_open(tracking_id, request)

@app.get("/tracking-data/{tracking_id}")
async def get_tracking_data(tracking_id: str):
    return email_tracker.tracking_manager.get_tracking_data(tracking_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 