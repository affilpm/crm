import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def refresh_token_if_needed(request):
    """Refresh access token using refresh token."""
    refresh_token = request.session.get("refresh_token")
    if not refresh_token:
        request.session.flush()
        return None

    data = {
        "grant_type": "refresh_token",
        "client_id": settings.CLIENT_ID,
        "client_secret": settings.CLIENT_SECRET,
        "refresh_token": refresh_token,
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
            "refresh_token": tokens.get("refresh_token")
        })
        request.session.modified = True
        return tokens.get("access_token")
        
    except requests.RequestException as e:
        logger.error(f"Token refresh failed: {e}")
        request.session.flush()
        return None

def api_request(request, method, url, **kwargs):
    """Make API request with automatic token refresh on 401."""
    access_token = request.session.get("access_token")
    if not access_token:
        return None

    headers = kwargs.get('headers', {})
    headers.update({
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28",
        "Accept": "application/json"
    })
    kwargs['headers'] = headers

    try:
        response = getattr(requests, method.lower())(url, **kwargs)
        
        # Retry once with refreshed token on 401
        if response.status_code == 401:
            new_token = refresh_token_if_needed(request)
            if new_token:
                headers["Authorization"] = f"Bearer {new_token}"
                response = getattr(requests, method.lower())(url, **kwargs)
        
        response.raise_for_status()
        return response
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return None