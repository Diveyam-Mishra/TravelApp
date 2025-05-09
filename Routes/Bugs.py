from fastapi import APIRouter, Depends, File, HTTPException, Form, UploadFile
from typing import Optional
from config import JWTBearer
from Schemas.EventSchemas import SuccessResponse
from Database.Connection import get_blob_service_client, get_bugs_container
from Controllers.Auth import get_current_user
from Controllers.Bugs import postNewBug
from Models.user_models import User

router= APIRouter()

@router.post("/bug/post", dependencies=[Depends(JWTBearer())])
async def post_a_bug(
    bug_description: str = Form(None),
    bug_image: Optional[UploadFile] = File(None),
    blob_client=Depends(get_blob_service_client),
    current_user: User = Depends(get_current_user),
    bug_container=Depends(get_bugs_container)
):
    if current_user is None: 
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if bug_description is None:
        raise HTTPException(status_code=400, detail="Bug description is required")
    # print("ok")
    return await postNewBug(bug_description, bug_image, current_user, blob_client, bug_container)


