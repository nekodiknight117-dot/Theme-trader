import datetime
from sqlalchemy.orm import Session
from . import models

def get_cached_value(db: Session, key: str) -> str | None:
    """
    Retrieve a cached value by key. Checks expiration.
    Returns None if missing or expired.
    """
    entry = db.query(models.CacheEntry).filter(models.CacheEntry.key == key).first()
    if not entry:
        return None
        
    # Check expiration
    if entry.expires_at:
        expires_at = datetime.datetime.fromisoformat(entry.expires_at)
        if datetime.datetime.now(datetime.timezone.utc) > expires_at:
            # Expired, clean it up
            db.delete(entry)
            db.commit()
            return None
            
    return entry.value

def set_cached_value(db: Session, key: str, value: str, ttl_hours: int = 24):
    """
    Set a cache value with an optional time-to-live in hours.
    """
    # Calculate expiration
    expires_at = None
    if ttl_hours > 0:
        expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ttl_hours)).isoformat()

    # Check if exists
    entry = db.query(models.CacheEntry).filter(models.CacheEntry.key == key).first()
    if entry:
        entry.value = value
        entry.expires_at = expires_at
    else:
        entry = models.CacheEntry(key=key, value=value, expires_at=expires_at)
        db.add(entry)
        
    db.commit()
