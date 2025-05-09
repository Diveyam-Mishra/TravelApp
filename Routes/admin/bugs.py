from fastapi import APIRouter, UploadFile, File, Depends
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from typing import List
from Models.user_models import User
from Controllers.Auth import get_current_user
from Database.Connection import get_blob_service_client, get_db,\
    get_bugs_container
from Controllers.admin.promotionImages import upload_carousel_images
from sqlalchemy.orm import Session
from fastapi.exceptions import HTTPException
from Controllers.admin.bugs import fetchAllBugs

router = APIRouter()


@router.get("/bugs", dependencies=[Depends(JWTBearer())])
async def getAllBugs(current_user:User=Depends(get_current_user), bugs_container=Depends(get_bugs_container)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not Authenticated")
    if current_user.is_admin is False:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return await fetchAllBugs(bugs_container)