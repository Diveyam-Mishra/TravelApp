from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.orm import Session
from typing import List
from Models.org_models import Organization
from Models.org_models import Organization_details
from Schemas.UserSchemas import SuccessResponse
from Schemas.OrganizationSchemas import OrganizationSchema
from Controllers.Organizations import add_organization, get_organization, get_city_organizations
from Database.Connection import get_db, AsyncSessionLocal
from Models.user_models import User
from Controllers.Auth import get_current_user
from config import JWTBearer
router = APIRouter()

@router.post("/orgs/create_org/",dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def create_new_org(org_details: Organization_details, db: AsyncSessionLocal = Depends(get_db),current_user: User=Depends(get_current_user)):
    if current_user is None:
            raise HTTPException(status_code=400, detail="User Not Found")
    return await add_organization(org_details, db)

@router.get("/orgs/get_org_details/{org_id}", response_model=Organization_details)
async def get_organization_details(org_id: int, db: AsyncSessionLocal=Depends(get_db)):
    return await get_organization(org_id, db)


@router.get("/orgs/get_city_org/{city}/", response_model=List[OrganizationSchema])
async def get_all_city_org(city: str, organizations: List[Organization]=Depends(get_city_organizations)):
    return organizations  