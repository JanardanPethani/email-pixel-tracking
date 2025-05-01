from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
import resend
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Email Tracking Service API")

# Set Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

# Base URL for tracking pixel
LIVE_API = os.getenv("LIVE_API")

# In-memory storage for tracking data
tracking_data = {}

# Constants for tracking pixel
PIXEL_GIF_BYTES = bytes.fromhex('47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b')
PIXEL_MEDIA_TYPE = "image/gif"

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    html: str

@app.post("/send-email")
async def send_email(email_request: EmailRequest):
    try:
        logger.info(f"Sending email to {email_request.to}")
        
        # Generate unique tracking ID
        tracking_id = str(uuid.uuid4())
        
        # Create tracking pixel URL
        tracking_pixel_url = f"{LIVE_API}/track/{tracking_id}"
        
        # Add tracking pixel as background image
        tracking_div = f'<div style="background: url({tracking_pixel_url}); width: 1px; height: 1px; position: absolute; top: 0; left: 0;"></div>'
        html_with_tracking = f"{email_request.html}{tracking_div}"
        
        # Initialize tracking data
        tracking_data[tracking_id] = {
            "email_id": tracking_id,
            "recipient_email": email_request.to,
            "open_time": None,
            "location": None
        }
        
        # Send email using Resend
        params = {
            "from": "Acme <onboarding@resend.dev>",
            "to": [email_request.to],
            "subject": email_request.subject,
            "html": html_with_tracking
        }
        
        email = resend.Emails.send(params)
        logger.info(f"Email sent successfully to {email_request.to}")
        
        return {
            "message": "Email sent successfully",
            "email_id": email.get('id'),
            "tracking_id": tracking_id
        }
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.api_route("/track/{tracking_id}", responses={200: {"content": {"image/gif": {}}}}, methods=["GET", 'HEAD'])
async def track_email(tracking_id: str, request: Request):  
    try:
        logger.info(f"Tracking pixel accessed for tracking_id: {tracking_id}")
        
        # Get client IP
        client_ip = request.client.host
        
        # Update tracking data
        if tracking_id in tracking_data:
            tracking_data[tracking_id]["open_time"] = datetime.utcnow()
            tracking_data[tracking_id]["location"] = {
                "ip": client_ip,
                "user_agent": request.headers.get("user-agent")
            }
        else:
            logger.warning(f"Tracking ID not found: {tracking_id}")
        
        # Return tracking pixel
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

@app.get("/tracking-data/{tracking_id}")
async def get_tracking_data(tracking_id: str):
    if tracking_id not in tracking_data:
        raise HTTPException(status_code=404, detail="Tracking ID not found")
    return tracking_data[tracking_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 