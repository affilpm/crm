import requests
import random
import logging
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from .utils import api_request

logger = logging.getLogger(__name__)

def home(request):
    """Render the main page."""
    return render(request, 'home.html')

def status(request):
    """Check HighLevel connection status."""
    access_token = request.session.get("access_token")
    location_id = request.session.get("location_id")
    
    if access_token and location_id:
        return JsonResponse({
            "connected": True,
            "location_id": location_id,
            "company_id": request.session.get("company_id"),
            "message": "Connected to HighLevel"
        })
    return JsonResponse({"connected": False, "message": "Not connected"})


def connect(request):
    """Redirect to HighLevel OAuth."""
    auth_url = (
        f"https://marketplace.leadconnectorhq.com/oauth/chooselocation?"
        f"response_type=code&client_id={settings.CLIENT_ID}"
        f"&redirect_uri={settings.REDIRECT_URI}"
        "&scope=contacts.readonly%20contacts.write%20locations/customFields.readonly"
    )
    return redirect(auth_url)

def callback(request):
    """Handle OAuth callback."""
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "No authorization code"}, status=400)

    data = {
        "grant_type": "authorization_code",
        "client_id": settings.CLIENT_ID,
        "client_secret": settings.CLIENT_SECRET,
        "redirect_uri": settings.REDIRECT_URI,
        "code": code,
    }
    
    try:
        response = requests.post(
            "https://services.leadconnectorhq.com/oauth/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        tokens = response.json()
        request.session.update({
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "location_id": tokens.get("locationId"),
            "company_id": tokens.get("companyId")
        })
        request.session.modified = True
        
        return redirect('home')
        
    except requests.RequestException as e:
        logger.error(f"Token exchange failed: {e}")
        return JsonResponse({"error": "Failed to get tokens"}, status=500)

@csrf_protect
@require_http_methods(["POST"])
def logout(request):
    """Logout user by clearing session."""
    try:
        # Clear all session data
        request.session.flush()
        logger.info("User logged out successfully")
        
        return JsonResponse({
            "success": True,
            "message": "Logged out successfully"
        })
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return JsonResponse({
            "success": False,
            "error": "Logout failed"
        }, status=500)

@csrf_protect
@require_http_methods(["POST"])
def update_random(request):
    """Update random contact's 'DFS Booking Zoom Link' field to 'TEST'."""
    # Check if user is still connected
    access_token = request.session.get("access_token")
    location_id = request.session.get("location_id")
    
    if not access_token or not location_id:
        return JsonResponse({
            "error": "Connection lost. Please reconnect to HighLevel.",
            "reconnect_required": True
        }, status=401)

    # Get contacts
    contacts_response = api_request(
        request, "GET", 
        "https://services.leadconnectorhq.com/contacts/",
        params={"locationId": location_id, "limit": 25}
    )
    
    if not contacts_response:
        return JsonResponse({
            "error": "Connection disrupted. Failed to fetch contacts.",
            "reconnect_required": True
        }, status=500)

    contacts = contacts_response.json().get("contacts", [])
    if not contacts:
        return JsonResponse({"error": "No contacts found"}, status=404)

    # Get custom fields
    fields_response = api_request(
        request, "GET",
        f"https://services.leadconnectorhq.com/locations/{location_id}/customFields"
    )
    
    if not fields_response:
        return JsonResponse({
            "error": "Connection disrupted. Failed to fetch custom fields.", 
            "reconnect_required": True
        }, status=500)

    fields = fields_response.json().get("customFields", [])
    field_id = next(
        (f.get("id") for f in fields if f.get("name") == "DFS Booking Zoom Link"), 
        None
    )
    
    if not field_id:
        return JsonResponse({
            "error": "Custom field 'DFS Booking Zoom Link' not found"
        }, status=404)

    # Update random contact
    contact = random.choice(contacts)
    contact_id = contact.get("id")
    
    update_response = api_request(
        request, "PUT",
        f"https://services.leadconnectorhq.com/contacts/{contact_id}",
        headers={"Content-Type": "application/json"},
        json={"customFields": [{"id": field_id, "value": "TEST"}]}
    )
    
    if not update_response:
        return JsonResponse({
            "error": "Connection disrupted. Failed to update contact.",
            "reconnect_required": True
        }, status=500)

    # Verify update
    updated_contact = update_response.json().get("contact", {})
    custom_fields = updated_contact.get("customFields", [])
    
    if not any(f.get("id") == field_id and f.get("value") == "TEST" for f in custom_fields):
        return JsonResponse({"error": "Update verification failed"}, status=500)

    return JsonResponse({
        "message": "Contact updated successfully",
        "contact": {
            "id": contact_id,
            "name": f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip() or "Unknown",
            "email": contact.get("email", "No email")
        },
        "custom_field": {
            "id": field_id,
            "name": "DFS Booking Zoom Link",
            "value": "TEST"
        }
    })