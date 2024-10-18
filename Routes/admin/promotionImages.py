from fastapi import APIRouter, UploadFile, File, Depends
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from typing import List
from Models.user_models import User
from Controllers.Auth import get_current_user
from Database.Connection import get_blob_service_client, get_db,\
    AsyncSessionLocal
from Controllers.admin.promotionImages import upload_carousel_images
from sqlalchemy.orm import Session
from fastapi.exceptions import HTTPException

router = APIRouter()


@router.post("/admin/addCarouselImages", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def uploadCarouselImages(files: List[UploadFile]=File(...), current_user:User=Depends(get_current_user), carousel_blob_client=Depends(get_blob_service_client), db:AsyncSessionLocal=Depends(get_db)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not Authenticated")
    if current_user.is_admin is False:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await upload_carousel_images(files, carousel_blob_client, db)

