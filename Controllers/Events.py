from sqlalchemy.orm import Session
from Schemas.EventSchemas import EventDetails
from Schemas.UserSchemas import SuccessResponse
from Controllers.Auth import pwd_context, JWT_SECRET
import jwt
from Models.event_models import Event
from Controllers.Auth import get_current_user
from Models.user_models import User
from fastapi import HTTPException, Depends


def create_event(db: Session, event_details: EventDetails, current_user: User) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
   
    existing_event = db.query(Event).filter(
        Event.name == event_details.event_name,
        Event.host_id == event_details.host_information.id,
        Event.type == ','.join(event_details.event_type),  # Convert list to comma-separated string
        Event.start_date == event_details.date_and_time.start,
        Event.end_date == event_details.date_and_time.end
    ).first()

    if existing_event:
        raise HTTPException(status_code=400, detail="Event already created")

    # Create a new event
    new_event = Event(
        name=event_details.event_name,
        description=event_details.event_description,
        type=','.join(event_details.event_type),  # Convert list to comma-separated string
        start_date=event_details.date_and_time.start,
        end_date=event_details.date_and_time.end,
        duration=event_details.duration,
        age_group=event_details.age_group,
        family_friendly=event_details.family_friendly,
        price_standard=event_details.price_fees.standard,
        price_early=event_details.price_fees.early_bird,
        price_group=event_details.price_fees.group_rate,
        max_capacity=event_details.capacity,
        host_id=event_details.host_information.id,
        media_files=','.join(event_details.media_files),  # Convert list to comma-separated string
        remaining_capacity=event_details.capacity,
        creator_id=current_user.id  # Use the current user's ID
    )
    
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    return SuccessResponse(message="Event Created Successfully", success=True)


def update_event(db: Session, event_details: EventDetails, current_user: User) -> SuccessResponse:
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")

    existing_event = db.query(Event).filter(
        Event.name == event_details.event_name,
        Event.host_id == event_details.host_information.id,
        Event.type == ','.join(event_details.event_type),  # Convert list to comma-separated string
        Event.start_date == event_details.date_and_time.start,
        Event.end_date == event_details.date_and_time.end
    ).first()



    if existing_event is None:
        raise HTTPException(status_code=400, detail="Event not found")
    

    if existing_event.creator_id != current_user.id:
        raise HTTPException(status_code=401, detail="Not Authorized")

    update_data = event_details.dict(exclude_unset=True)  # Exclude fields that were not set
    update_data['type'] = ','.join(update_data['event_type']) if 'event_type' in update_data else existing_event.type
    update_data['media_files'] = ','.join(update_data['media_files']) if 'media_files' in update_data else existing_event.media_files

    for key, value in update_data.items():
        setattr(existing_event, key, value)

    db.commit()
    db.refresh(existing_event)
    return SuccessResponse(message="Event Updated Successfully", success=True)
    

