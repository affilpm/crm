import random
from .utils import make_api_request

def update_random_contact(session, location_id):
    contacts_res = make_api_request(session, "GET", "https://services.leadconnectorhq.com/contacts/", params={"locationId": location_id, "limit": 25})
    if not contacts_res:
        return None

    contacts = contacts_res.json().get("contacts", [])
    if not contacts:
        return None

    contact = random.choice(contacts)
    contact_id = contact.get("id")

    fields_res = make_api_request(session, "GET", f"https://services.leadconnectorhq.com/locations/{location_id}/customFields")
    fields = fields_res.json().get("customFields", [])
    field_id = next((f.get("id") for f in fields if f.get("name") == "DFS Booking Zoom Link"), None)
    if not field_id:
        return None

    update_res = make_api_request(session, "PUT", f"https://services.leadconnectorhq.com/contacts/{contact_id}", headers={"Content-Type": "application/json"}, json={"customFields": [{"id": field_id, "value": "TEST"}]})
    return update_res.json() if update_res else None