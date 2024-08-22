from fastapi import HTTPException
from Database.Connection import event_files_blob_container_name
from Models.Files import Carousel_image
from Schemas.EventSchemas import SuccessResponse


async def upload_carousel_images(files, blob_service_client, db):
    if files:
        if len(files) > 7:
            raise HTTPException(status_code=400, detail="Maximum 7 files can be uploaded at once")
        
        file_metadata = []

        for i, file in enumerate(files):
            if i >= 7:
                break

            file_name = f"carousel_image_{i+1}.{file.filename.split('.')[-1]}"
            blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
            file_data = await file.read()
            blob_client.upload_blob(file_data, overwrite=True)
            file_url = blob_client.url

            # Prepare file metadata
            file_metadata.append({
                "fileName": file_name,
                "fileUrl": file_url,
                "fileType": file.content_type
            })

            # Add file metadata to the database
            new_image = Carousel_image(
                filename=file_name,
                fileurl=file_url,
                filetype=file.content_type
            )
            db.add(new_image)

        # Commit the transaction to save changes
        db.commit()
    return SuccessResponse(message="Carousel Files Added Successfully", success=True)

        