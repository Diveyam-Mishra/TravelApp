# Project Name

## Description
This project is a comprehensive event management system that allows users to create, manage, and participate in various events. It includes features such as user authentication, event creation, file uploads, and more.

## Features
- User Authentication
- Event Creation and Management
- File Uploads
- Event Filtering and Search
- User-specific Data Management
- Integration with Azure Blob Storage

## Project Structure
 ├── Constants/ │ └── SampleEvents.py ├── Controllers/ │ ├── AiInteract.py │ ├── Auth.py │ ├── Bugs.py │ ├── Delete.py │ └── ... ├── Database/ │ └── ... ├── Helpers/ │ └── initialize.py ├── Models/ │ └── ... ├── Queues/ │ └── ... ├── Routes/ │ ├── admin/ │ │ ├── bugs.py │ │ └── promotionImages.py │ ├── AiInteract.py │ ├── Auth.py │ ├── Delete.py │ ├── EventRoutes.py │ ├── Files.py │ ├── Fiters.py │ └── Payments.py ├── Schemas/ │ ├── EventSchemas.py │ ├── Files.py │ ├── userSpecific.py │ └── ... ├── Secure/ │ └── ... ├── Test/ │ ├── jsonify │ ├── Testapi.py │ └── ... ├── Tickster/ │ ├── frame1.html │ ├── frame2.html │ ├── frame3.html │ ├── frame4.html │ ├── frame5.html │ └── frame6.html ├── .env ├── .gitignore ├── config.py ├── docker-compose-sendTicket.yml ├── docker-compose.yml ├── dockerfile ├── dockerfile.send_ticket ├── div.txt ├── install-tools.sh ├── myenv/ ├── nginx/ ├── odbc.ini ├── README.md ├── requirements.txt ├── send_ticket_worker.py ├── startup.sh └── webhook_payload.txt

 ## Installation
1. Clone the repository:
    ```sh
    git clone <repository-url>
    ```
2. Navigate to the project directory:
    ```sh
    cd <project-directory>
    ```
3. Create a virtual environment:
    ```sh
    python -m venv myenv
    ```
4. Activate the virtual environment:
    - On Windows:
        ```sh
        myenv\Scripts\activate
        ```
    - On macOS/Linux:
        ```sh
        source myenv/bin/activate
        ```
5. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage
1. Set up the environment variables by creating a [.env](http://_vscodecontentref_/37) file in the project root directory.
2. Run the application:
    ```sh
    uvicorn main:app --reload
    ```

## Contributing
1. Fork the repository.
2. Create a new branch:
    ```sh
    git checkout -b feature-branch
    ```
3. Make your changes and commit them:
    ```sh
    git commit -m "Description of changes"
    ```
4. Push to the branch:
    ```sh
    git push origin feature-branch
    ```
5. Create a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Contact
For any inquiries or issues, please don't contact.

# Auth Controller Functions

## `get_user`
Fetches a user by their ID from the database.

## `get_user_by_email`
Fetches a user by their email from the database.

## `get_user_by_username`
Fetches a user by their username from the database.

## `get_current_user`
Decodes the JWT token to get the current user and fetches their details from the database.

## `get_current_user_optional`
Decodes the JWT token to get the current user optionally and fetches their details from the database.

## `update_user`
Updates the user's details in the database.

## `check_unique_username`
Checks if the username is unique in the database.

## `create_user`
Creates a new user in the database.

## `delete_user`
Deletes the current user from the database and adds them to the deletedUser table.

## `register_user`
Registers a new user by sending an OTP to their email.

## `login_user`
Logs in a user by sending an OTP to their email.

## `login_verify`
Verifies the OTP for login and generates a JWT token.

## `look_up_username`
Looks up a user by their username and returns their details along with their avatar URL.

## `add_interest_areas_to_user`
Adds interest areas to the user's profile.

## `add_recent_search`
Adds a recent search term to the user's profile.

## `get_user_specific_data`
Fetches user-specific data including booked events and recent searches.

## `get_bookings`
Fetches the user's booked events.

## `fetch_carousel_images_db`
Fetches carousel images from the database.

## `get_recent_search_data`
Fetches the user's recent search data.

## `add_credit_card`
Adds a credit card to the user's profile.

## `add_banking_details`
Adds or updates the user's banking details.

## `get_banking_details`
Fetches the user's banking details.

