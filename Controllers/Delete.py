from fastapi import HTTPException, Depends
from uuid import uuid4
from sqlalchemy.orm import Session
from Schemas.EventSchemas import *
from Schemas.UserSchemas import SuccessResponse
from Models.user_models import User
from Models.Files import *
from fastapi import HTTPException, Depends
from Database.Connection import get_container, event_files_blob_container_name, \
    avatar_container_name


async def delete_whole_event(
    event_id: str,
    current_user: User,
    event_container,
    file_container,
    blob_service_client
) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User not found")
    current_time = datetime.datetime.now()
    print(current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    # Step 1: Retrieve the event details
    query = """
    SELECT * FROM c 
    WHERE c.id = @event_ID 
    AND ARRAY_CONTAINS(c.editor_access, @userID)
    """
    params = [
        {"name": "@event_ID", "value": event_id},
        {"name": "@userID", "value": current_user.id}
    ]
    items = list(event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    current_time = datetime.datetime.now()
    print(current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])
    if not items:
        raise HTTPException(status_code=404, detail="Event not found or you do not have permission to delete this event")

    item_to_delete = items[0]
    print (item_to_delete)
    # Step 2: Get file names associated with the event
    file_names = [item_to_delete.get(f'fileName{i+1}') for i in range(5) if item_to_delete.get(f'fileName{i+1}')]

    # Step 3: Delete files from Azure Blob Storage
    for file_name in file_names:
        blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
        try:
            blob_client.delete_blob()
            print(f"Deleted file {file_name} successfully")
        except Exception as e:
            print(f"Failed to delete file {file_name}: {str(e)}")

    # Step 4: Delete file metadata from the file container
    for file_name in file_names:
        query = "SELECT c.id FROM c WHERE c.filename = @file_name"
        params = [{"name": "@file_name", "value": file_name}]
        file_items = list(file_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        
        for file_item in file_items:
            try:
                file_container.delete_item(item=file_item['id'], partition_key=file_item['id'])
                print(f"Deleted file metadata with id {file_item['id']} successfully")
            except Exception as e:
                print(f"Failed to delete file metadata with id {file_item['id']}: {str(e)}")

    # Step 5: Delete the event record from the event container
    try:
        event_container.delete_item(item=item_to_delete['id'], partition_key=item_to_delete['event_ID'])
        print(f"Deleted event with id {item_to_delete['id']} successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete the event: {str(e)}")

    return SuccessResponse(message=f"Event with event_id: {event_id} deleted successfully", success=True)


#to be done SELECT *
async def delete_file(
    event_id: str,
    file_name: str,
    current_user: User,
    file_container,
    blob_service_client,
    event_container  # Add event_container parameter
) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Step 1: Retrieve the event details to verify ownership and get file metadata
    query = """
    SELECT * FROM c 
    WHERE c.id = @event_ID 
    AND ARRAY_CONTAINS(c.editor_access, @userID)
    """
    params = [
        {"name": "@event_ID", "value": event_id},
        {"name": "@userID", "value": current_user.id}
    ]
    event_items = list(event_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

    if not event_items:
        raise HTTPException(status_code=404, detail="Event not found or you do not have permission to delete this event")

    file_query = """SELECT * FROM c WHERE c.id = @event_ID"""
    params = [{"name": "@event_ID", "value": event_id}]
    file_items = list(file_container.query_items(query=file_query, parameters=params, enable_cross_partition_query=True))

    if not file_items:
        raise HTTPException(status_code=404, detail="Files not found")

    event_item = file_items[0]

    # Check if the file to be deleted is part of the event
    file_found = any(file_name == event_item.get(f'fileName{i+1}') for i in range(5))
    if not file_found:
        raise HTTPException(status_code=404, detail="File not found in the specified event")

    # Step 2: Delete the file from Azure Blob Storage
    blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
    try:
        blob_client.delete_blob()
        print(f"Deleted file {file_name} successfully from blob storage")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file from blob storage: {str(e)}")

    # Step 3: Delete file metadata from the file container
    query = "SELECT id FROM c WHERE c.filename = @file_name"
    params = [{"name": "@file_name", "value": file_name}]
    file_items = list(file_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    
    # if not file_items:
    #     raise HTTPException(status_code=404, detail="File metadata not found")

    for file_item in file_items:
        try:
            file_container.delete_item(item=file_item['id'], partition_key=file_item['id'])
            print(f"Deleted file metadata with id {file_item['id']} successfully")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file metadata: {str(e)}")

    # Step 4: Update the event's thumbnail field to null if the file name ends with '1'
    file_name_temp = file_name.split('.')[0]
    if file_name_temp.endswith('1'):
        event_update_query = """
        SELECT thumbnail,id FROM c 
        WHERE c.id = @event_ID
        """
        params = [{"name": "@event_ID", "value": event_id}]
        event_items = list(event_container.query_items(query=event_update_query, parameters=params, enable_cross_partition_query=True))
        
        if event_items:
            event_item = event_items[0]
            event_item['thumbnail'] = None  # Update the thumbnail field to null
            
            try:
                event_container.replace_item(item=event_item['id'], body=event_item)
                print(f"Updated event {event_id} thumbnail to null successfully")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to update event thumbnail: {str(e)}")

    return SuccessResponse(message=f"File {file_name} deleted successfully from event {event_id}", success=True)




async def delete_avatar(current_user: User, db: Session, blob_client) -> SuccessResponse:
    avatar = db.query(Avatar).filter(Avatar.userID == current_user.id).first()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    blob_client = blob_client.get_blob_client(container=avatar_container_name, blob=avatar.filename)
    
    try:
        blob_client.delete_blob()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file from blob storage: {str(e)}")

    # Delete the avatar record from the database
    db.delete(avatar)
    db.commit()

    return SuccessResponse(message="Avatar deleted successfully", success=True)


async def delete_carousel_file(file_name: str, current_user: User, db: Session, blob_service_client) -> SuccessResponse:
    # Check if current user has the right permissions
    if not current_user.is_admin:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Find the file metadata in the database
    carousel_image = db.query(Carousel_image).filter(Carousel_image.filename == file_name).first()
    
    if not carousel_image:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete the file from Azure Blob Storage
    blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
    
    try:
        blob_client.delete_blob()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file from blob storage: {str(e)}")

    # Delete the file metadata from the database
    db.delete(carousel_image)
    db.commit()

    return SuccessResponse(message="Carousel file deleted successfully", success=True)
