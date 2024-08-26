from fastapi import APIRouter, Depends,HTTPException
from Schemas.UserSchemas import SuccessResponse
from Schemas.EventSchemas import *
from Database.Connection import *
from Controllers.Delete import*
from config import JWTBearer
from Controllers.Auth import get_current_user
from Models.user_models import User
router = APIRouter()


@router.post("/delete/event/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteEvent(event_id: takeString, current_user: User=Depends(get_current_user), container=Depends(get_container)):
    if(current_user is None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_whole_event(event_id,current_user,container)

@router.post("/delete/file/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteFile(event_id:strAndint, current_user: User=Depends(get_current_user), file_container=Depends(get_file_container),blob_service_client=Depends(get_blob_service_client)):
    if(current_user is None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_file(event_id,current_user,file_container,blob_service_client)

@router.post("/delete/avatar/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteAvatar(id:takeString, current_user: User=Depends(get_current_user),db: Session=Depends(get_db)):
    if(current_user is None or current_user.id!=id.eventId):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_avatar(id,current_user,db)

@router.post("/delete/carousel_file/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteCarousel(id:takeString, current_user: User=Depends(get_current_user),db: Session=Depends(get_db)):
    if(current_user is None ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_carousel_file(id,current_user,db)