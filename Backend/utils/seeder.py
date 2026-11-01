from database import db
from models.report import Report

SEED_REPORTS = [
    {
        "id": 101,
        "title": "Major Pothole on Elm Street",
        "category": "Roads & Footpaths",
        "description": "Deep pothole causing vehicle tire damage near the traffic signal.",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "status": "Pending"
    },
    {
        "id": 102,
        "title": "Burst Water Main Flooding Sidewalk",
        "category": "Water Supply",
        "description": "Significant potable water flow erupting onto pedestrian pavement.",
        "latitude": 37.7833,
        "longitude": -122.4167,
        "status": "In Progress"
    },
    {
        "id": 103,
        "title": "Overfilled Community Dumpsters",
        "category": "Garbage & Waste",
        "description": "Trash overflowing for over 3 days, spilling into driveway.",
        "latitude": 37.7690,
        "longitude": -122.4467,
        "status": "Pending"
    },
    {
        "id": 104,
        "title": "Broken Streetlight Cluster",
        "category": "Electricity",
        "description": "Four sequential lamps are dark, creating dangerous pedestrian conditions.",
        "latitude": 37.7600,
        "longitude": -122.4200,
        "status": "Resolved"
    },
    {
        "id": 105,
        "title": "Blocked Storm Drain Before Monsoon",
        "category": "Drainage & Sewage",
        "description": "Drain inlet clogged with solid debris and soil.",
        "latitude": 37.7900,
        "longitude": -122.4000,
        "status": "In Progress"
    }
]

def seed_database():
    """Seeds representative civic complaints."""
    for item in SEED_REPORTS:
        existing = Report.query.get(item["id"])
        if not existing:
            rep = Report(
                id=item["id"],
                title=item["title"],
                category=item["category"],
                description=item["description"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                status=item["status"]
            )
            db.session.add(rep)

    db.session.commit()
    print("[OK] CivicLens database verified and seeded.")
