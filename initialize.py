# main.py
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from Routes.OrganizationRoutes import router as organization_router
from Routes.Auth import router as auth_router
# from Controllers.Auth import (settings, engine)
from Database.Connection import engine, Base
from config import settings
from Routes.forgot_password import router as forgot_password
from Routes.EventRoutes import router as events
from Routes.AiInteract import router as AiInteract
from Routes.Files import router as FileRouter
from Routes.Fiters import router as FilterRouter
from Routes.Payments import router as PaymentRouter
from Routes.admin.promotionImages import router as adminImageRouter
from Routes.Delete import router as DeleteRouter
from Routes.PaymentWebhook import router as Webhook
from Routes.Bugs import router as BugRouter
from Routes.admin.bugs import router as AdminBugRouter
from sqlalchemy import MetaData
from  datetime import datetime
# print(settings.sqlURI)

app = FastAPI(title="Backend with MongoDB and SQL")

origins = ['http://localhost:3000']

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(adminImageRouter, tags=["Admin - File Management"])
app.include_router(AdminBugRouter, tags=["Admin-Bugs"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(organization_router, tags=["Organizations"])
app.include_router(forgot_password, tags=["Forgot Password"])
app.include_router(events, tags=["Events"])
app.include_router(DeleteRouter, tags=["Delete"])
app.include_router(AiInteract, tags=["AI Interaction"])
app.include_router(FileRouter, tags=["File Management"])
app.include_router(FilterRouter, tags=["Filters"])
app.include_router(PaymentRouter, tags=["Payments"])
app.include_router(Webhook, tags=["Webhook"])
app.include_router(BugRouter, tags=["Bugs"])


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)

    metadata = MetaData()
    metadata.reflect(bind=engine)


@app.get("/")
async def read_root():
    return {"Trabii Server!!"}


@app.middleware("http")
async def log_time_middleware(request: Request, call_next):
    # Get the time when the request is received
    start_time = datetime.now()
    request_time = start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"Request received at: {request_time}")

    # Process the request and get the response
    response = await call_next(request)

    # Get the time when the response is sent
    end_time = datetime.now()
    response_time = end_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"Response sent at: {response_time}")

    # Calculate the difference in milliseconds
    time_diff = (end_time - start_time).total_seconds() * 1000  # Convert to milliseconds
    print(f"Time taken to process the request: {time_diff:.2f} ms")

    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
