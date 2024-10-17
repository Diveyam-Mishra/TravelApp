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
from Database.Connection import get_db, AsyncSessionLocal
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
JWT_SECRET = settings.JWT_SECRET
ALGORITHM = settings.ALGORITHM
# router = APIRouter()

from sqlalchemy import select

async def add_organization(org_details: Organization_details, db: AsyncSessionLocal) -> SuccessResponse:
    # Check if the organization already exists
    result = await db.execute(select(Organization).filter(
        Organization.org_name == org_details.org_name,
        Organization.venue == org_details.location.venue
    ))
    existing_org = result.scalar_one_or_none()

    if existing_org:
        raise HTTPException(status_code=400, detail="Organization already added in the server")
    
    # Create new organization entry
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
    await db.commit()
    await db.refresh(org_entry)
    
    return SuccessResponse(message="Organization Added Successfully", success=True)


async def get_organization(org_id: int, db: AsyncSessionLocal = Depends(get_db)) -> Organization_details:
    # Fetch the organization entry asynchronously
    result = await db.execute(select(Organization).filter(Organization.id == org_id))
    org_entry = result.scalar_one_or_none()

    if not org_entry:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Return organization details
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

async def get_city_organizations(city: str, token: str = Depends(oauth2_scheme), db: AsyncSessionLocal = Depends(get_db)):
    try:
        # Decode the JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Fetch the user asynchronously
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        # Fetch organizations by city
        result = await db.execute(select(Organization).filter(Organization.city == city))
        organizations = result.scalars().all()

        if not organizations:
            raise HTTPException(status_code=404, detail="No organizations found in the specified city")
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return organizations

