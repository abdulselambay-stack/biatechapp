"""
Utility Functions
WhatsApp API helpers and common functions
"""

import requests
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# WhatsApp API Config
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("ACCESS_TOKEN")
WHATSAPP_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

def send_template_message(phone_number: str, template_name: str, language_code: str = "tr", header_image_id: str = None) -> Dict:
    """
    WhatsApp Cloud API ile şablon mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
    }
    
    # Header image parametresi varsa ekle (boş string değilse)
    if header_image_id and header_image_id.strip():
        payload["template"]["components"] = [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "id": header_image_id.strip()
                        }
                    }
                ]
            }
        ]
        logger.info(f"Template with image header: {header_image_id}")
    
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        
        # Log response for debugging
        logger.info(f"WhatsApp API Response: {response.status_code}")
        
        if response.status_code == 200:
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json()
            }
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            logger.error(f"WhatsApp API Error: {error_msg}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": error_msg,
                "response": error_data
            }
    except requests.Timeout:
        logger.error(f"Timeout while sending to {phone_number}")
        return {
            "success": False,
            "error": "Request timeout (10s)"
        }
    except Exception as e:
        logger.error(f"Exception while sending to {phone_number}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def send_text_message(phone_number: str, text: str) -> Dict:
    """
    WhatsApp Cloud API ile text mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": True,
            "body": text
        }
    }
    
    try:
        logger.info(f"🚀 Sending text to {phone_number}")
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200:
            logger.info(f"✅ Message sent successfully: {response_data}")
            return {
                "success": True,
                "response": response_data
            }
        else:
            logger.error(f"❌ Message send failed: {response_data}")
            return {
                "success": False,
                "error": response_data.get("error", {}).get("message", "Unknown error"),
                "response": response_data
            }
    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def send_image_message(phone_number: str, image_url: str, caption: str = "") -> Dict:
    """
    WhatsApp Cloud API ile görsel mesajı gönder
    """
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    
    if caption:
        payload["image"]["caption"] = caption
    
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200:
            return {
                "success": True,
                "response": response_data
            }
        else:
            return {
                "success": False,
                "error": response_data.get("error", {}).get("message", "Unknown error"),
                "response": response_data
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
