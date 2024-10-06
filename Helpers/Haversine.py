import math

def deg2rad(deg):
    return deg * (math.pi / 180)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the earth in km
    dLat = deg2rad(lat2 - lat1)  # Convert latitude difference to radians
    dLon = deg2rad(lon2 - lon1)  # Convert longitude difference to radians

    a = math.sin(dLat / 2) ** 2 + math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  # Use atan2 instead of asin for better accuracy

    distance = R * c  # Distance in kilometers
    return round(distance, 2)
