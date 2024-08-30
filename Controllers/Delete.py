from fastapi import HTTPException, Depends
from uuid import uuid4
from sqlalchemy.orm import Session
from Schemas.EventSchemas import *
from Schemas.UserSchemas import SuccessResponse
from Models.user_models import User
from Models.Files import *
from fastapi import HTTPException, Depends
from Database.Connection import get_container, event_files_blob_container_name

async def delete_whole_event(event_id: takeString, current_user: User, container=Depends(get_container)) -> SuccessResponse:
    print ("2")
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    query = """
    SELECT * FROM eventcontainer e WHERE e.event_id = @event_id
    """
    
    params = [
        {"name": "@event_id", "value": event_id.eventId}
    ]
    print(3)
    items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    print ("1")
    if not items:
        raise HTTPException(status_code=404, detail="Event not found or you do not have permission to delete this event")
    print (items)
    # query="SELECT * FROM eventfilescontainer ef WHERE ef.eventId=@eventId"

    # params = [
    #     {"name": "@eventId", "value": event_id.eventId}
    # ]
    # items2 = list(container.query_items(query=query, params=params, enable_cross_partition_query=True))
    # print ("2")
    # # Delete the event
    # container.delete_item(items2[0]["id"], partition_key=items[0]["event_ID"])

    container.delete_item(item=items[0], partition_key=items[0]['id'])

    
    return SuccessResponse(message=f"Event with event_id: {event_id} deleted successfully", success=True)


async def delete_file(
    event_id:strAndint,
    current_user: User,
    file_container,
    blob_service_client
) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
     
    query_files = "SELECT * FROM eventfilescontainer ef WHERE ef.eventId = @eventId"
    params_files = [{"name": "@eventId", "value": event_id.event_id}]
    file_items = list(file_container.query_items(query=query_files, parameters=params_files, enable_cross_partition_query=True))

    if not file_items:
        raise HTTPException(status_code=404, detail="Event files not found")

    existing_files = file_items[0]
    file_name_key = f'fileName{event_id.image}'
    file_url_key = f'fileUrl{event_id.image}'
    file_type_key = f'fileType{event_id.image}'
    if file_name_key not in existing_files:
        raise HTTPException(status_code=404, detail=f"File {event_id.image} not found")
    file_name = existing_files[file_name_key]
    blob_client = blob_service_client.get_blob_client(container=event_files_blob_container_name, blob=file_name)
    blob_client.delete_blob()

    # Remove the file metadata from the existing files
    del existing_files[file_name_key]
    del existing_files[file_url_key]
    del existing_files[file_type_key]

    # Replace the existing file record with the updated metadata
    file_container.replace_item(item=existing_files['id'], body=existing_files)

    return SuccessResponse(message=f"File {event_id.image} deleted successfully", success=True)

def delete_avatar(user_id: takeString, current_user: User, db: Session) -> None:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    avatar = db.query(Avatar).filter(Avatar.user_id == user_id).first()
    if avatar:
        db.delete(avatar)
        db.commit()
def delete_carousel_file(event_id: takeString,  current_user: User, db: Session) -> None:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    carousel_file = db.query(Carousel_image).filter(Carousel_image.event_id == event_id).first()
    if carousel_file:
        db.delete(carousel_file)
        db.commit()