from fastapi import HTTPException
from Database.Connection import event_files_blob_container_name
from Models.Files import Carousel_image
from Schemas.EventSchemas import SuccessResponse


async def upload_carousel_images(files, blob_service_client, db):
    if files:
        if len(files) > 7:
            raise HTTPException(status_code=400, detail="Maximum 7 files can be uploaded at once")

        file_metadata = []

        # Get the current count of carousel images in the database
        total_items = db.query(Carousel_image).count()

        for i, file in enumerate(files):
            if i >= 7:
                break

            ind = i + total_items

            # Construct the file name
            file_extension = file.filename.split('.')[-1]
            file_name = f"carousel_image_{ind + 1}.{file_extension}"
            
            # Get a blob client
            blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
            
            try:
                # Read file data and upload it to Azure Blob Storage
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

            except Exception as e:
                # Handle the exception (log it, re-raise, or rollback as needed)
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Error uploading file {file_name}: {str(e)}")

        # Commit the transaction to save changes
        db.commit()

    return SuccessResponse(message="Carousel Files Added Successfully", success=True)

        