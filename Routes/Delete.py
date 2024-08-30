from fastapi import APIRouter, Depends, HTTPException
from Schemas.UserSchemas import SuccessResponse
from Schemas.EventSchemas import *
from Database.Connection import *
from Controllers.Delete import*
from config import JWTBearer
from Controllers.Auth import get_current_user
from Models.user_models import User
router = APIRouter()


@router.delete("/delete/event/{event_id}", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteEvent(event_id: str, current_user: User=Depends(get_current_user), container=Depends(get_container), file_container=Depends(get_file_container), blob_client=Depends(get_blob_service_client)):
    if(current_user is None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_whole_event(event_id, current_user, container, file_container, blob_client)


@router.delete("/delete/file/{eventid}/{fileName}", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteFile(event_id:str, fileName: str, current_user: User=Depends(get_current_user),
event_container=Depends(get_container), file_container=Depends(get_file_container), blob_service_client=Depends(get_blob_service_client)):
    if(current_user is None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_file(event_id, fileName, current_user, file_container, blob_service_client, event_container)


@router.delete("/delete/avatar/", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteAvatar(current_user: User=Depends(get_current_user), db: Session=Depends(get_db), blob_client=Depends(get_blob_service_client)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_avatar(current_user, db, blob_client)


@router.delete("/delete/carousel_file/{fileName}", dependencies=[Depends(JWTBearer())], response_model=SuccessResponse)
async def deleteCarousel(fileName:str, current_user: User=Depends(get_current_user), db: Session=Depends(get_db), blob_service_client=Depends(get_blob_service_client)):
    if(current_user is None or current_user.is_admin is False):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await delete_carousel_file(fileName, current_user, db, blob_service_client)
