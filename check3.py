import streamlit as st
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
import io
import base64
import hashlib
import json
from groq import Groq
import re
import webbrowser
import threading
import schedule
import os
# Check for required packages and install if missing
import sys
import subprocess
import os

def install_packages():
    try:
        import firebase_admin
        import groq
        import qrcode
    except ImportError:
        print("Installing missing packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                              "firebase-admin==6.2.0", 
                              "groq==0.4.0", 
                              "qrcode==7.4.2"])
        print("Packages installed successfully!")

# Try to install packages if they're missing
try:
    install_packages()
except Exception as e:
    st.error(f"Failed to install required packages: {e}")
    st.info("Please contact support if this error persists.")
# Set page config first to avoid warnings
st.set_page_config(
    page_title="Athena Museum Booking Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Firebase
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            # Try to use Firebase credentials from Streamlit secrets first
            if "firebase" in st.secrets:
                firebase_config = {
                    "type": st.secrets["firebase"]["type"],
                    "project_id": st.secrets["firebase"]["project_id"],
                    "private_key_id": st.secrets["firebase"]["private_key_id"],
                    "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
                    "client_email": st.secrets["firebase"]["client_email"],
                    "client_id": st.secrets["firebase"]["client_id"],
                    "auth_uri": st.secrets["firebase"]["auth_uri"],
                    "token_uri": st.secrets["firebase"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
                    "universe_domain": st.secrets["firebase"]["universe_domain"]
                }
                cred = credentials.Certificate(firebase_config)
            else:
                # Fallback to local file for development
                cred = credentials.Certificate('firebase_auth.json')
            
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")
        return None

# Initialize Groq client
@st.cache_resource
def init_groq():
    # Try to get API key from secrets first, then fallback to hardcoded
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "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")
        return Groq(api_key=api_key)
    except:
        return Groq(api_key="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")

# Initialize clients
db = init_firebase()
client = init_groq()
MODEL = 'llama3-8b-8192'

# SMTP Configuration - Use secrets if available
try:
    SMTP_SERVER = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(st.secrets.get("SMTP_PORT", 587))
    SMTP_USERNAME = st.secrets.get("SMTP_USERNAME", "chsantosh2004@gmail.com")
    SMTP_PASSWORD = st.secrets.get("SMTP_PASSWORD", "kzka uohw hbxg gwgi")
except:
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "chsantosh2004@gmail.com"
    SMTP_PASSWORD = "kzka uohw hbxg gwgi"

# Updated Flask app URL - Your deployed Vercel app
FLASK_APP_URL = "https://my-ticket-tau.vercel.app"

# Museum information
MUSEUM_INFO = {
    "name": "Athena Museum of Science and Technology",
    "address": "123 Science Avenue, Mumbai, Maharashtra 400001, India",
    "hours": {
        "monday_to_saturday": "9:00 AM - 5:00 PM",
        "sunday": "10:00 AM - 4:00 PM",
        "holidays": "Closed on major holidays"
    },
    "ticket_prices": {
        "adult": 500,
        "child": 250,
        "student": 350,
        "senior": 350,
        "family_pack": 1200
    },
    "exhibitions": [
        {
            "name": "AI Revolution",
            "description": "Explore the future of artificial intelligence and its impact on society.",
            "duration": "Until December 31, 2024"
        },
        {
            "name": "Space Odyssey", 
            "description": "Journey through the cosmos and discover the wonders of our universe.",
            "duration": "Until November 15, 2024"
        },
        {
            "name": "Quantum Realm",
            "description": "Dive into the mysteries of quantum physics and understand the building blocks of reality.",
            "duration": "Until January 30, 2025"
        }
    ]
}

# Initialize session state
def init_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.messages = [{
            "role": "assistant",
            "content": "👋 Welcome to the Athena Museum Booking Assistant! I can help you with booking tickets, provide information about exhibitions, or answer any questions about the museum. How may I assist you today?"
        }]
        st.session_state.show_booking_form = False
        st.session_state.show_ticket_info = False
        st.session_state.booking_data = {}
        st.session_state.last_booking_id = ""
        st.session_state.processing = False
        st.session_state.booking_created = False
        st.session_state.current_booking = None
        st.session_state.displayed_booking = None
        st.session_state.cleanup_running = False

# Optimized CSS with stable animations
def load_optimized_css():
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap');
    
    .stApp {
        opacity: 1 !important;
        transition: none !important;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%) !important;
        min-height: 100vh;
    }
    
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --accent-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --card-bg: rgba(255, 255, 255, 0.05);
        --border-color: rgba(103, 126, 234, 0.3);
        --text-primary: #ffffff;
        --text-secondary: #b8c6db;
        --success-color: #00d4aa;
        --error-color: #ff6b6b;
        --warning-color: #feca57;
    }
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
        color: var(--text-primary) !important;
        background: transparent !important;
    }
    
    .main-title {
        font-size: clamp(2rem, 5vw, 4rem);
        font-weight: 700;
        text-align: center;
        margin: 2rem 0;
        background: linear-gradient(45deg, #667eea, #764ba2, #4facfe, #00f2fe);
        background-size: 400% 400%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 8s ease infinite;
        text-shadow: 0 0 30px rgba(102, 126, 234, 0.5);
    }
    
    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .subtitle {
        font-size: clamp(1rem, 3vw, 1.5rem);
        text-align: center;
        margin-bottom: 3rem;
        color: var(--text-secondary);
        font-weight: 300;
        letter-spacing: 2px;
    }
    
    .chat-container {
        max-height: 600px;
        overflow-y: auto;
        padding: 1rem;
        background: var(--card-bg);
        border-radius: 20px;
        border: 1px solid var(--border-color);
        backdrop-filter: blur(20px);
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .chat-message {
        padding: 1.5rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .chat-message.user {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
        border-left: 4px solid #667eea;
        margin-left: 2rem;
    }
    
    .chat-message.assistant {
        background: linear-gradient(135deg, rgba(79, 172, 254, 0.15), rgba(0, 242, 254, 0.15));
        border-left: 4px solid #4facfe;
        margin-right: 2rem;
    }
    
    .avatar {
        width: 45px;
        height: 45px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.2rem;
        flex-shrink: 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    .avatar.user {
        background: var(--primary-gradient);
        color: white;
    }
    
    .avatar.assistant {
        background: var(--accent-gradient);
        color: white;
    }
    
    .message-content {
        flex-grow: 1;
        line-height: 1.6;
        font-size: 1rem;
    }
    
    .booking-form {
        background: var(--card-bg);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid var(--border-color);
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin: 2rem 0;
    }
    
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 15px !important;
        color: var(--text-primary) !important;
        padding: 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.3) !important;
        background: rgba(255, 255, 255, 0.15) !important;
    }
    
    .stButton > button {
        background: var(--primary-gradient) !important;
        color: white !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 1rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6) !important;
    }
    
    .success-message {
        background: linear-gradient(135deg, rgba(0, 212, 170, 0.2), rgba(0, 212, 170, 0.1));
        border: 2px solid var(--success-color);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: var(--success-color);
        backdrop-filter: blur(10px);
    }
    
    .error-message {
        background: linear-gradient(135deg, rgba(255, 107, 107, 0.2), rgba(255, 107, 107, 0.1));
        border: 2px solid var(--error-color);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: var(--error-color);
        backdrop-filter: blur(10px);
    }
    
    .ticket-display {
        background: var(--card-bg);
        border-radius: 20px;
        padding: 2rem;
        border: 2px solid var(--border-color);
        backdrop-filter: blur(20px);
        margin: 2rem 0;
        position: relative;
        overflow: hidden;
        opacity: 1;
        transform: none;
    }
    
    .ticket-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .ticket-header h2 {
        color: #667eea;
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .ticket-detail {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .ticket-label {
        font-weight: 600;
        color: var(--text-secondary);
    }
    
    .ticket-value {
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .qr-container {
        text-align: center;
        background: var(--card-bg);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid var(--border-color);
        backdrop-filter: blur(20px);
    }
    
    .qr-code-img {
        max-width: 200px;
        border-radius: 10px;
        background: white;
        padding: 10px;
        margin: 1rem auto;
        display: block;
    }
    
    .payment-link {
        display: inline-block;
        background: var(--secondary-gradient);
        color: white !important;
        text-decoration: none;
        padding: 1rem 2rem;
        border-radius: 15px;
        font-weight: 600;
        margin: 1rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(240, 147, 251, 0.4);
        text-align: center;
        width: 100%;
        display: block;
    }
    
    .payment-link:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.6);
        text-decoration: none;
        color: white !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    @media (max-width: 768px) {
        .main-title {
            font-size: 2.5rem;
        }
        
        .chat-message {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .chat-message.user {
            margin-left: 0;
        }
        
        .chat-message.assistant {
            margin-right: 0;
        }
        
        .booking-form {
            padding: 1.5rem;
        }
    }
    </style>
    """

# Automatic cleanup function for expired bookings
def cleanup_expired_bookings():
    """Clean up expired bookings from Firebase"""
    try:
        if not db:
            return
        
        current_time = datetime.now()
        
        # Get all bookings
        bookings_ref = db.collection('bookings')
        bookings = bookings_ref.get()
        
        deleted_count = 0
        for booking_doc in bookings:
            booking_data = booking_doc.to_dict()
            validity_date = booking_data.get('validity')
            
            if validity_date:
                # Handle Firestore timestamp
                if hasattr(validity_date, 'replace'):
                    validity_datetime = validity_date.replace(tzinfo=None)
                else:
                    validity_datetime = validity_date
                
                # Check if booking is expired
                if validity_datetime <= current_time:
                    # Delete expired booking
                    booking_doc.reference.delete()
                    
                    # Also delete phone index if exists
                    email = booking_data.get('email', '')
                    if email:
                        phone_clean = re.sub(r'[^\d+]', '', booking_data.get('phone', ''))
                        if phone_clean:
                            phone_doc_id = f"phone_{phone_clean}"
                            try:
                                db.collection('phone_index').document(phone_doc_id).delete()
                            except:
                                pass
                    
                    deleted_count += 1
        
        if deleted_count > 0:
            st.success(f"🧹 Cleaned up {deleted_count} expired booking(s)")
            
    except Exception as e:
        st.error(f"Cleanup error: {str(e)}")

# Run cleanup on app start
@st.cache_resource
def run_initial_cleanup():
    cleanup_expired_bookings()
    return True

# Helper function to detect identifier type
def detect_identifier_type(text):
    """Detect if text contains booking ID, email, or phone number"""
    text = text.strip()
    
    # Check for email
    if '@' in text and '.' in text:
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            return "email", email_match.group()
    
    # Check for booking ID (starts with ATH)
    booking_id_match = re.search(r'\bATH\d+\b', text, re.IGNORECASE)
    if booking_id_match:
        return "booking_id", booking_id_match.group().upper()
    
    # Check for phone number (various formats)
    phone_patterns = [
        r'\+91[\s-]?\d{10}',  # +91 followed by 10 digits
        r'\b91\d{10}\b',      # 91 followed by 10 digits
        r'\b\d{10}\b',        # 10 digits
        r'\+\d{1,3}[\s-]?\d{8,12}',  # International format
    ]
    
    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)
        if phone_match:
            return "phone", phone_match.group()
    
    return None, None

# Email sending function
def send_email_confirmation(email, booking_details):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        msg['Subject'] = "Athena Museum Booking Confirmation"
        
        payment_url = f"{FLASK_APP_URL}?email={email}"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Montserrat', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; background: #f8f9fa; }}
                .footer {{ background: #e9ecef; padding: 20px; text-align: center; font-size: 14px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; margin: 20px 0; }}
                .details {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #667eea; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Athena Museum</h1>
                    <h2>Booking Confirmation</h2>
                </div>
                <div class="content">
                    <p>Dear Visitor,</p>
                    <p>Thank you for choosing the Athena Museum of Science and Technology! Your booking has been created successfully.</p>
                    
                    <div class="details">
                        <h3>📋 Booking Details</h3>
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Phone:</strong> {booking_details['phone_number']}</p>
                        <p><strong>Number of Tickets:</strong> {booking_details['no_of_tickets']}</p>
                        <p><strong>Total Amount:</strong> ₹{booking_details['no_of_tickets'] * 500}</p>
                        <p><strong>Validity:</strong> 1 day from booking time</p>
                    </div>
                    
                    <p>To complete your booking, please click the button below to proceed with payment:</p>
                    <div style="text-align: center;">
                        <a href="{payment_url}" class="button">💳 Complete Payment</a>
                    </div>
                    
                    <p>After successful payment, you will receive your official Booking ID and QR code for museum entry.</p>
                </div>
                <div class="footer">
                    <p><strong>Athena Museum of Science and Technology</strong></p>
                    <p>123 Science Avenue, Mumbai, Maharashtra 400001, India</p>
                    <p>📞 +91 22 1234 5678 | 📧 info@athenamuseum.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

# Enhanced Firebase booking function with proper error handling
def create_booking(email, phone, tickets):
    try:
        if not db:
            return {"error": "Database connection failed"}
        
        # Clean up expired bookings first
        cleanup_expired_bookings()
        
        # Use email as document ID for easy retrieval
        email_doc_id = email.replace('.', '_').replace('@', '_at_')
        
        # Check if booking already exists for this email
        try:
            existing_doc = db.collection('bookings').document(email_doc_id).get()
            if existing_doc.exists:
                existing_data = existing_doc.to_dict()
                
                # Check if existing booking is still valid
                validity_date = existing_data.get('validity')
                if validity_date:
                    if hasattr(validity_date, 'replace'):
                        validity_datetime = validity_date.replace(tzinfo=None)
                    else:
                        validity_datetime = validity_date
                    
                    # If booking is expired, delete it
                    if validity_datetime <= datetime.now():
                        existing_doc.reference.delete()
                        # Also delete phone index
                        phone_clean = re.sub(r'[^\d+]', '', phone)
                        if phone_clean:
                            phone_doc_id = f"phone_{phone_clean}"
                            try:
                                db.collection('phone_index').document(phone_doc_id).delete()
                            except:
                                pass
                    else:
                        # Return existing valid booking
                        if existing_data.get('status') == 'pending':
                            return {
                                "success": True,
                                "booking_id": existing_data.get('booking_id', 'Pending'),
                                "amount": existing_data.get('amount', tickets * 500),
                                "payment_url": f"{FLASK_APP_URL}?email={email}",
                                "existing": True
                            }
        except Exception as e:
            st.write(f"No existing booking found: {e}")
        
        # Calculate amount
        amount = tickets * 500
        
        # Create booking timestamp
        booking_time = datetime.now()
        validity_time = booking_time + timedelta(days=1)
        
        # Create booking data with email as primary identifier
        booking_data = {
            "email": email,
            "phone": phone,
            "tickets": tickets,
            "amount": amount,
            "status": "pending",
            "created_at": booking_time,
            "validity": validity_time,
            "booking_id": None,  # Will be set by Flask after payment
            "hash": None,        # Will be set by Flask after payment
            "updated_at": booking_time,
            "doc_id": email_doc_id
        }
        
        # Store in Firebase using email as document ID
        db.collection('bookings').document(email_doc_id).set(booking_data)
        
        # Also create a phone number index for lookup
        if phone:
            phone_clean = re.sub(r'[^\d+]', '', phone)
            phone_doc_id = f"phone_{phone_clean}"
            phone_index_data = {
                "phone": phone,
                "email": email,
                "doc_id": email_doc_id,
                "created_at": booking_time
            }
            db.collection('phone_index').document(phone_doc_id).set(phone_index_data)
        
        # Send email confirmation
        booking_details = {
            "phone_number": phone,
            "no_of_tickets": tickets
        }
        email_sent = send_email_confirmation(email, booking_details)
        
        return {
            "success": True,
            "doc_id": email_doc_id,
            "amount": amount,
            "payment_url": f"{FLASK_APP_URL}?email={email}",
            "email_sent": email_sent
        }
        
    except Exception as e:
        st.error(f"Booking creation error: {str(e)}")
        return {"error": f"Booking failed: {str(e)}"}

# Enhanced get booking information function
def get_booking_info(identifier):
    try:
        if not db:
            return {"error": "Database connection failed"}
        
        # Clean up expired bookings first
        cleanup_expired_bookings()
        
        booking_doc = None
        
        # Search by email (primary key)
        if '@' in identifier:
            email_doc_id = identifier.replace('.', '_').replace('@', '_at_')
            try:
                booking_doc = db.collection('bookings').document(email_doc_id).get()
                if not booking_doc.exists:
                    return {"error": f"No booking found for email: {identifier}"}
            except Exception as e:
                return {"error": f"Error searching by email: {str(e)}"}
        
        # Search by booking ID
        elif identifier.upper().startswith('ATH'):
            try:
                bookings = db.collection('bookings').where('booking_id', '==', identifier.upper()).limit(1).get()
                if bookings:
                    booking_doc = bookings[0]
                else:
                    return {"error": f"No booking found with ID: {identifier}"}
            except Exception as e:
                return {"error": f"Error searching by booking ID: {str(e)}"}
        
        # Search by phone number
        elif any(char.isdigit() for char in identifier):
            try:
                # Clean phone number
                clean_phone = re.sub(r'[^\d+]', '', identifier)
                possible_phones = [
                    clean_phone,
                    clean_phone[-10:] if len(clean_phone) >= 10 else clean_phone,
                    f"91{clean_phone[-10:]}" if len(clean_phone) >= 10 else clean_phone
                ]
                
                email_found = None
                for phone_format in possible_phones:
                    phone_doc_id = f"phone_{phone_format}"
                    try:
                        phone_doc = db.collection('phone_index').document(phone_doc_id).get()
                        if phone_doc.exists:
                            email_found = phone_doc.to_dict().get('email')
                            break
                    except:
                        continue
                
                if email_found:
                    email_doc_id = email_found.replace('.', '_').replace('@', '_at_')
                    booking_doc = db.collection('bookings').document(email_doc_id).get()
                    if not booking_doc.exists:
                        return {"error": f"Booking data inconsistency for phone: {identifier}"}
                else:
                    return {"error": f"No booking found for phone: {identifier}"}
            except Exception as e:
                return {"error": f"Error searching by phone: {str(e)}"}
        
        else:
            return {"error": f"Invalid identifier format: {identifier}"}
        
        if not booking_doc or not booking_doc.exists:
            return {"error": f"No booking found for: {identifier}"}
        
        # Get the booking data
        booking_data = booking_doc.to_dict()
        
        # Calculate validity status
        validity_date = booking_data.get('validity')
        current_time = datetime.now()
        
        if validity_date:
            if hasattr(validity_date, 'replace'):  # Firestore timestamp
                validity_datetime = validity_date.replace(tzinfo=None)
            else:
                validity_datetime = validity_date
            
            is_valid = validity_datetime > current_time
            validity_str = validity_datetime.strftime('%d %b %Y, %H:%M')
            
            # Calculate remaining time
            if is_valid:
                time_remaining = validity_datetime - current_time
                hours_remaining = int(time_remaining.total_seconds() // 3600)
                minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
                validity_str += f" ({hours_remaining}h {minutes_remaining}m remaining)"
            else:
                validity_str += " (EXPIRED)"
        else:
            is_valid = False
            validity_str = "Not set"
        
        return {
            "success": True,
            "booking_id": booking_data.get('booking_id', 'Pending Payment'),
            "email": booking_data.get('email'),
            "phone": booking_data.get('phone'),
            "tickets": booking_data.get('tickets'),
            "amount": booking_data.get('amount'),
            "status": booking_data.get('status', 'pending'),
            "validity": validity_date,
            "validity_str": validity_str,
            "is_valid": is_valid,
            "hash": booking_data.get('hash', ''),
            "created_at": booking_data.get('created_at')
        }
        
    except Exception as e:
        st.error(f"Database query error: {str(e)}")
        return {"error": f"Failed to retrieve booking: {str(e)}"}

# Generate QR code
def generate_qr_code(booking_id, hash_code):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"ATHENA-MUSEUM-{booking_id}-{hash_code}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
    except Exception as e:
        st.error(f"QR code generation failed: {str(e)}")
        return None

# Chat with AI
def chat_with_ai(messages):
    try:
        system_message = {
            "role": "system",
            "content": """You are EaseEntry AI, the official assistant for the Athena Museum of Science and Technology. 

Museum Information:
- Name: Athena Museum of Science and Technology
- Address: 123 Science Avenue, Mumbai, Maharashtra 400001, India
- Hours: Monday-Saturday 9AM-5PM, Sunday 10AM-4PM
- Ticket Price: ₹500 per person
- Current Exhibitions: AI Revolution, Space Odyssey, Quantum Realm

Your main functions:
1. Help users book tickets (collect email, phone, number of tickets)
2. Provide museum information
3. Help users check their booking status
4. Answer general questions about the museum

Be friendly, helpful, and enthusiastic. Keep responses concise but informative.
If users want to book tickets, guide them to provide their email, phone number, and number of tickets.
If users want to check bookings, ask for their booking ID, email address, or phone number."""
        }
        
        api_messages = [system_message] + messages
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"I apologize, but I'm experiencing technical difficulties. Please try again. Error: {str(e)}"

# Function to display booking validity with stable rendering
def display_booking_validity(booking_info):
    """Display booking validity information with stable rendering"""
    if booking_info.get("success"):
        booking = booking_info
        
        # Create a unique key for this booking display
        booking_key = f"{booking['email']}_{booking.get('booking_id', 'pending')}"
        
        # Store in session state to prevent flickering
        if st.session_state.displayed_booking != booking_key:
            st.session_state.displayed_booking = booking_key
        
        # Determine status and validity
        if booking['status'] == 'completed':
            if booking['is_valid']:
                status_emoji = "✅"
                status_text = "CONFIRMED & VALID"
                status_color = "#00d4aa"
            else:
                status_emoji = "⚠️"
                status_text = "CONFIRMED BUT EXPIRED"
                status_color = "#feca57"
        elif booking['status'] == 'pending':
            status_emoji = "⏳"
            status_text = "PENDING PAYMENT"
            status_color = "#feca57"
        else:
            status_emoji = "❌"
            status_text = "CANCELLED"
            status_color = "#ff6b6b"
        
        # Create stable booking display
        with st.container():
            st.markdown(f"""
            <div class="ticket-display" id="booking-{booking_key}">
                <div class="ticket-header">
                    <h2>{status_emoji} Booking Status</h2>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Booking ID:</span>
                    <span class="ticket-value">{booking['booking_id']}</span>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Email:</span>
                    <span class="ticket-value">{booking['email']}</span>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Phone:</span>
                    <span class="ticket-value">{booking['phone']}</span>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Tickets:</span>
                    <span class="ticket-value">{booking['tickets']}</span>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Amount:</span>
                    <span class="ticket-value">₹{booking['amount']}</span>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Status:</span>
                    <span class="ticket-value" style="color: {status_color}; font-weight: bold;">{status_text}</span>
                </div>
                <div class="ticket-detail">
                    <span class="ticket-label">Valid Until:</span>
                    <span class="ticket-value">{booking['validity_str']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show payment link if pending
            if booking['status'] == 'pending':
                payment_url = f"{FLASK_APP_URL}?email={booking['email']}"
                st.markdown(f"""
                <div style="text-align: center; margin: 1rem 0;">
                    <a href="{payment_url}" target="_blank" class="payment-link">
                        💳 Complete Payment Now
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            # Show QR code info if completed and valid
            if booking['status'] == 'completed' and booking.get('hash') and booking['is_valid']:
                qr_code = generate_qr_code(booking['booking_id'], booking['hash'])
                if qr_code:
                    st.markdown(f"""
                    <div class="qr-container">
                        <h3>📱 Your QR Code</h3>
                        <img src="data:image/png;base64,{qr_code}" alt="QR Code" class="qr-code-img">
                        <p>Present this QR code at the museum entrance</p>
                        <p><strong>Security Hash:</strong> {booking['hash']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        return True
    else:
        st.markdown(f"""
        <div class="error-message">
            <h3>❌ Booking Not Found</h3>
            <p>{booking_info.get('error', 'No booking found with that information')}</p>
        </div>
        """, unsafe_allow_html=True)
        return False

# Main application
def main():
    # Initialize session state
    init_session_state()
    
    # Run initial cleanup
    run_initial_cleanup()
    
    # Load CSS
    st.markdown(load_optimized_css(), unsafe_allow_html=True)
    
    # Title
    st.markdown('<h1 class="main-title">🏛️ Athena Museum</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI-Powered Booking Assistant</p>', unsafe_allow_html=True)
    
    # Museum image
    st.image("https://images.unsplash.com/photo-1566127992631-137a642a90f4?ixlib=rb-4.0.3&auto=format&fit=crop&w=1600&q=90", 
             caption="Athena Museum of Science and Technology", use_column_width=True)
    
    # Chat interface
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user">
                <div class="avatar user">👤</div>
                <div class="message-content">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant">
                <div class="avatar assistant">🤖</div>
                <div class="message-content">{message["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show booking success message if booking was just created
    if st.session_state.booking_created and st.session_state.current_booking:
        booking = st.session_state.current_booking
        payment_url = booking['payment_url']
        
        st.markdown(f"""
        <div class="success-message">
            <h3>✅ Booking Created Successfully!</h3>
            <p><strong>Amount:</strong> ₹{booking['amount']}</p>
            <p>Your booking has been saved. Please complete your payment to confirm your booking.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Payment button with JavaScript redirect
        st.markdown(f"""
        <div style="text-align: center; margin: 2rem 0;">
            <a href="{payment_url}" target="_blank" class="payment-link">
                💳 Complete Payment Now - Click Here
            </a>
        </div>
        <script>
            window.open('{payment_url}', '_blank');
        </script>
        """, unsafe_allow_html=True)
        
        # Reset the booking created flag
        st.session_state.booking_created = False
        st.session_state.current_booking = None
    
    # Booking form
    if st.session_state.show_booking_form:
        st.markdown('<div class="booking-form">', unsafe_allow_html=True)
        st.markdown("### 🎫 Book Your Tickets")
        
        with st.form("booking_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("📧 Email Address", placeholder="your.email@example.com")
                tickets = st.number_input("🎫 Number of Tickets", min_value=1, max_value=10, value=1)
            with col2:
                phone = st.text_input("📱 Phone Number", placeholder="+91 XXXXXXXXXX")
                st.markdown(f"**Total Amount: ₹{tickets * 500}**")
            
            submitted = st.form_submit_button("🚀 Book Now", use_container_width=True)
            
            if submitted:
                if email and phone and tickets:
                    if not st.session_state.processing:
                        st.session_state.processing = True
                        
                        with st.spinner("Creating your booking..."):
                            result = create_booking(email, phone, tickets)
                        
                        if result.get("success"):
                            # Store booking info for display
                            st.session_state.current_booking = result
                            st.session_state.booking_created = True
                            
                            # Add to chat
                            if result.get("existing"):
                                chat_message = f"I found an existing pending booking for your email. Please complete your payment for ₹{result['amount']}."
                            else:
                                chat_message = f"Great! I've created your booking for ₹{result['amount']}. Please complete your payment using the link that will open automatically."
                            
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": chat_message
                            })
                            
                            st.session_state.show_booking_form = False
                            st.session_state.processing = False
                            st.rerun()
                        else:
                            st.markdown(f"""
                            <div class="error-message">
                                <h3>❌ Booking Failed</h3>
                                <p>{result.get('error', 'Unknown error occurred')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.session_state.processing = False
                else:
                    st.error("Please fill in all required fields.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Ticket info form
    if st.session_state.show_ticket_info:
        st.markdown('<div class="booking-form">', unsafe_allow_html=True)
        st.markdown("### 🔍 Check Your Booking")
        
        with st.form("ticket_info_form", clear_on_submit=True):
            identifier = st.text_input("🎫 Booking ID, 📧 Email, or 📱 Phone Number", 
                                     placeholder="Enter your booking ID, email, or phone number")
            submitted = st.form_submit_button("🔍 Check Booking", use_container_width=True)
            
            if submitted and identifier:
                with st.spinner("Retrieving your booking..."):
                    result = get_booking_info(identifier)
                
                if result.get("success"):
                    # Display booking validity with stable rendering
                    display_booking_validity(result)
                    
                    booking = result
                    validity_status = "valid" if booking['is_valid'] else "expired"
                    status_text = f"{booking['status']} and {validity_status}" if booking['status'] == 'completed' else booking['status']
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Found your booking! ID: {booking['booking_id']}, {booking['tickets']} tickets for ₹{booking['amount']}. Status: {status_text}."
                    })
                    
                    st.session_state.show_ticket_info = False
                    st.rerun()
                else:
                    st.markdown(f"""
                    <div class="error-message">
                        <h3>❌ Booking Not Found</h3>
                        <p>{result.get('error', 'No booking found with that information')}</p>
                        <p>Please check your booking ID, email, or phone number and try again.</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("💬 Type your message here...")
    
    if user_input and not st.session_state.processing:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Check if user input contains booking ID, email, or phone number
        identifier_type, identifier_value = detect_identifier_type(user_input)
        
        if identifier_type and identifier_value:
            # Direct booking lookup without showing form
            with st.spinner("Checking your booking..."):
                result = get_booking_info(identifier_value)
            
            if result.get("success"):
                # Display booking validity with stable rendering
                display_booking_validity(result)
                
                booking = result
                validity_status = "valid" if booking['is_valid'] else "expired"
                if booking['status'] == 'completed':
                    status_text = f"confirmed and {validity_status}"
                else:
                    status_text = booking['status']
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Found your booking! ID: {booking['booking_id']}, {booking['tickets']} tickets for ₹{booking['amount']}. Status: {status_text}."
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ {result.get('error', f'No booking found with {identifier_value}')}"
                })
            
            st.rerun()
        
        # Check for booking intent
        elif any(keyword in user_input.lower() for keyword in ["book", "ticket", "reserve", "buy", "purchase"]):
            st.session_state.show_booking_form = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I'd be happy to help you book tickets! Please fill out the form below:"
            })
            st.rerun()
        
        # Check for status checking intent
        elif any(keyword in user_input.lower() for keyword in ["check", "status", "booking", "my booking", "ticket info", "find"]):
            st.session_state.show_ticket_info = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I can help you check your booking status. Please enter your booking ID, email address, or phone number:"
            })
            st.rerun()
        
        else:
            # Get AI response
            with st.spinner("Thinking..."):
                ai_response = chat_with_ai(st.session_state.messages)
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": ai_response
            })
            st.rerun()
    
    # Museum information sidebar
    with st.sidebar:
        st.markdown("### 🏛️ Museum Information")
        st.markdown(f"""
        **📍 Address:**  
        {MUSEUM_INFO['address']}
        
        **🕒 Hours:**  
        Mon-Sat: {MUSEUM_INFO['hours']['monday_to_saturday']}  
        Sunday: {MUSEUM_INFO['hours']['sunday']}
        
        **🎫 Ticket Price:**  
        ₹{MUSEUM_INFO['ticket_prices']['adult']} per person
        
        **🎨 Current Exhibitions:**
        """)
        
        for exhibition in MUSEUM_INFO['exhibitions']:
            st.markdown(f"• **{exhibition['name']}** - {exhibition['description']}")
        
        # Cleanup button for manual cleanup
        if st.button("🧹 Clean Expired Bookings"):
            cleanup_expired_bookings()

if __name__ == "__main__":
    main()
