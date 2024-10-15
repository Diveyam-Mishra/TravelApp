from fastapi import UploadFile, HTTPException
from Models.user_models import User
from Controllers.Files import VALID_IMAGE_EXTENSIONS
from datetime import datetime
from typing import Optional
from Database.Connection import bug_file_container_name
from Schemas.EventSchemas import SuccessResponse
from uuid import uuid4

MAX_FILE_SIZE_MB = 10  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes

async def postNewBug(
    bug_description: str, 
    bug_image: Optional[UploadFile], 
    current_user: User, 
    blob_service_client,
    bug_container
):
    try:
        date = datetime.now()
        # print("ok")
        newId = str(uuid4())
        new_bug = {
            "id": newId,
            "bugId": "v0",  # Replace with appropriate logic to generate unique ID
            "user_id": current_user.id,
            "description": bug_description,
            # "image_url": file_url,
            "created_at": date.isoformat()
        }
        if bug_image:
            file_data = await bug_image.read()
        
            if len(file_data) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=400, detail="File size exceeds the maximum allowed size")
            
            ext = bug_image.filename.split('.')[-1].lower()
            if ext not in VALID_IMAGE_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"Invalid file extension. Only image files are allowed, file type provided: {ext}")
            
            # Generate file name using current user and date
            file_name = f"{current_user.id}_bug_{date.strftime('%Y%m%d%H%M%S')}.{ext}"

            # Upload to Azure Blob Storage
            blob_client = blob_service_client.get_blob_client(container=bug_file_container_name, blob=file_name)
            
            blob_client.upload_blob(file_data, overwrite=True)
            file_url = blob_client.url
            new_bug["image_url"] = file_url

            # Create new bug entry
        


        # Insert the bug entry into the container
        bug_container.create_item(new_bug)

        return SuccessResponse(message="Bug Data Added", success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{e}")