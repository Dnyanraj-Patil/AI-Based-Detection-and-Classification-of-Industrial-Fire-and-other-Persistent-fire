from fastapi import APIRouter, Query
import requests

router = APIRouter(prefix="/api/v1/locations", tags=["Locations"])

# Offline-first Indian location catalog. Nominatim is used only when the
# requested name is not in the catalog, so the core UI remains usable even
# when an external geocoder is temporarily unavailable.
LOCATIONS = {
    "delhi": (28.6139, 77.2090, "Delhi, India"),
    "new delhi": (28.6139, 77.2090, "New Delhi, India"),
    "mumbai": (19.0760, 72.8777, "Mumbai, Maharashtra, India"),
    "pune": (18.5204, 73.8567, "Pune, Maharashtra, India"),
    "nagpur": (21.1458, 79.0882, "Nagpur, Maharashtra, India"),
    "nashik": (19.9975, 73.7898, "Nashik, Maharashtra, India"),
    "thane": (19.2183, 72.9781, "Thane, Maharashtra, India"),
    "aurangabad": (19.8762, 75.3433, "Chhatrapati Sambhajinagar, Maharashtra, India"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru, Karnataka, India"),
    "bangalore": (12.9716, 77.5946, "Bengaluru, Karnataka, India"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad, Telangana, India"),
    "chennai": (13.0827, 80.2707, "Chennai, Tamil Nadu, India"),
    "kolkata": (22.5726, 88.3639, "Kolkata, West Bengal, India"),
    "ahmedabad": (23.0225, 72.5714, "Ahmedabad, Gujarat, India"),
    "surat": (21.1702, 72.8311, "Surat, Gujarat, India"),
    "jaipur": (26.9124, 75.7873, "Jaipur, Rajasthan, India"),
    "lucknow": (26.8467, 80.9462, "Lucknow, Uttar Pradesh, India"),
    "indore": (22.7196, 75.8577, "Indore, Madhya Pradesh, India"),
    "bhopal": (23.2599, 77.4126, "Bhopal, Madhya Pradesh, India"),
    "vadodara": (22.3072, 73.1812, "Vadodara, Gujarat, India"),
    "rajkot": (22.3039, 70.8022, "Rajkot, Gujarat, India"),
    "visakhapatnam": (17.6868, 83.2185, "Visakhapatnam, Andhra Pradesh, India"),
    "coimbatore": (11.0168, 76.9558, "Coimbatore, Tamil Nadu, India"),
    "patna": (25.5941, 85.1376, "Patna, Bihar, India"),
    "ranchi": (23.3441, 85.3096, "Ranchi, Jharkhand, India"),
    "bhubaneswar": (20.2961, 85.8245, "Bhubaneswar, Odisha, India"),
    "guwahati": (26.1445, 91.7362, "Guwahati, Assam, India"),
}

@router.get("/search")
def search_location(q: str = Query(..., min_length=2, max_length=120)):
    query = q.strip().lower()
    if query in LOCATIONS:
        lat, lon, label = LOCATIONS[query]
        return {"found": True, "latitude": lat, "longitude": lon, "label": label, "source": "catalog"}

    # Exact/partial catalog match first.
    for key, value in LOCATIONS.items():
        if query in key or key in query:
            lat, lon, label = value
            return {"found": True, "latitude": lat, "longitude": lon, "label": label, "source": "catalog"}

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q.strip(), "format": "json", "limit": 1, "countrycodes": "in"},
            headers={"User-Agent": "ThermoIntel-SIH26162/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        items = response.json()
        if items:
            item = items[0]
            return {
                "found": True,
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
                "label": item.get("display_name") or q.strip(),
                "source": "OpenStreetMap Nominatim",
            }
    except Exception:
        pass

    return {"found": False, "latitude": None, "longitude": None, "label": q.strip(), "source": None}
