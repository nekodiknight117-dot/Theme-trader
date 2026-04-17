import random
from app.database import SessionLocal, engine
from app import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

HOBBIES = [
    "gaming", "photography", "traveling", "reading sci-fi", "gardening", 
    "fitness", "cooking", "crypto mining", "astronomy", "cars", "DIY electronics",
    "sustainable living", "personal finance", "real estate investing"
]

EDUCATIONAL_BACKGROUNDS = [
    "Computer Science", "Medicine", "Business Administration", "Law", 
    "Mechanical Engineering", "Graphic Design", "Data Science", 
    "Environmental Science", "Economics", "History"
]

RISK_TOLERANCES = ["low", "medium", "high"]

def generate_fake_users(db, num_users=50):
    users_created = 0
    for i in range(num_users):
        # Generate random combinations
        username = f"user_{random.randint(1000, 99999)}_{i}"
        risk = random.choice(RISK_TOLERANCES)
        
        # Pick 2-3 random hobbies and 1 background
        selected_hobbies = random.sample(HOBBIES, k=random.randint(2, 3))
        background = random.choice(EDUCATIONAL_BACKGROUNDS)
        
        interests_str = f"Background in {background}. Hobbies include {', '.join(selected_hobbies)}."
        
        db_user = models.UserProfile(
            username=username,
            risk_tolerance=risk,
            interests=interests_str
        )
        db.add(db_user)
        users_created += 1
        
    db.commit()
    return users_created

if __name__ == "__main__":
    print("Connecting to database...")
    db = SessionLocal()
    try:
        print("Generating 50 fake users with varied backgrounds and interests...")
        count = generate_fake_users(db, 50)
        print(f"Successfully populated database with {count} users!")
        
        # Verify
        total_users = db.query(models.UserProfile).count()
        print(f"Total users now in database: {total_users}")
        
        print("\nSample User Profiles:")
        sample_users = db.query(models.UserProfile).limit(3).all()
        for u in sample_users:
            print(f"- {u.username} | Risk: {u.risk_tolerance} | Interests: {u.interests}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()
