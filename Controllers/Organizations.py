from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from Models.user_models import  User
from Models.org_models import Organization
from Models.org_models import Organization_details, Location, GeoTag
from Schemas.UserSchemas import SuccessResponse
import jwt
from jose import JWTError
from config import settings
from fastapi.security import OAuth2PasswordBearer
from Database.Connection import get_db
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
JWT_SECRET = settings.JWT_SECRET
ALGORITHM = settings.ALGORITHM
# router = APIRouter()



def add_organization(org_details: Organization_details, db: Session) -> SuccessResponse:
    existing_org = db.query(Organization).filter(
        Organization.org_name == org_details.org_name,
        Organization.venue == org_details.location.venue
    ).first()
    
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization already added in the server")
    
    org_entry = Organization(
        org_name=org_details.org_name,
        venue=org_details.location.venue,
        city=org_details.location.city,
        latitude=org_details.location.geo_tag.latitude,
        longitude=org_details.location.geo_tag.longitude,
        contact_info=org_details.contact_info,
        bio=org_details.bio
    )
    db.add(org_entry)
    db.commit()
    db.refresh(org_entry)
    return SuccessResponse(message="Organization Added Successfully", success=True)


def get_organization(org_id: int, db: Session=Depends(get_db)):
    org_entry = db.query(Organization).filter(Organization.id == org_id).first()
    if not org_entry:
        raise HTTPException(status_code=404, detail="Organization not found")
    return Organization_details(
        org_name=org_entry.org_name,
        location=Location(
            venue=org_entry.venue,
            city=org_entry.city,
            geo_tag=GeoTag(latitude=org_entry.latitude, longitude=org_entry.longitude)
        ),
        contact_info=org_entry.contact_info,
        bio=org_entry.bio
    )


def get_city_organizations(city: str, token: str=Depends(oauth2_scheme), db: Session=Depends(get_db)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        organizations = db.query(Organization).filter(Organization.city == city).all()
        if not organizations:
            raise HTTPException(status_code=404, detail="No organizations found in the specified city")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return organizations

