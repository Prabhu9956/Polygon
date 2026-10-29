**Polygon Migration Tool: The Five Main Flows**

Each flow below answers six questions: what the user clicks, what the frontend sends, what the backend does, which outside APIs are called, what is read or written, and what the user sees.

Four of the flows happen on the home page at "/". One view, called index in problems/views.py, handles it, and its template is problems/templates/problems/index.html. Each button is a POST form that sends problem_id (the Polygon ID) and one flag. A loading screen shows on every submit.

**Flow 1: User login**

Click: The user opens /users/login/, types email and password, and submits.

Sends: A POST to /users/login/ with the email and password.

Backend: The login code in the users app checks the email and password against the custom user model, which uses email instead of a username. If they match, Django starts a session and sets a session cookie. If not, the login page shows again. The migration page is for staff users only.

Outside APIs: None.

Database: Reads the user row from PostgreSQL. Django also saves a session and updates the last login time.

User sees: After a good login, the user is sent on to the app. After a bad login, the login page shows again. The exact redirect and error text are in users/views.py.

**Flow 2: Fetching a problem from Polygon**

Click: The user types a Polygon problem ID and clicks Fetch Problem.

Sends: A POST to "/" with problem_id and no flag.

Backend: The index view creates a PolygonAPI object (problems/polygon_api.py) and looks for a Problem with this polygon_id. If it exists, the view updates the working copy and reads the solutions to find the main solution. It opens transaction.atomic(). It calls get_problem_info, then download_and_extract_package and reads problem.html for the title, legend, formats and notes. Then it loads the tests with get_all_test_cases and renders the page.

Outside APIs: The Polygon API, with every call signed in _make_request. The methods are problem.updateWorkingCopy, problem.solutions, problem.info, the package download, the list of tests, problem.testInput and problem.testAnswer.

Database: Reads one Problem row. Writes nothing.

User sees: The page filled with the problem: statement, limits, the tests with a View Full button, the main solution with a Copy button, the difficulty choice, the tag picker and the other three buttons.

**Flow 3: Migrating a problem to the database**

Click: The user picks a difficulty and tags, then clicks Create/Update problem in Database.

Sends: A POST to "/" with problem_id, the flag migrate_to_db, the difficulty and the tags. JavaScript copies the chosen tags into hidden inputs named tags before submit.

Backend: Same start as Flow 2, including the Polygon calls. Then it creates or updates the Problem row, deletes the old tags and saves the new ones, and creates or updates the SampleTestCase rows. If anything fails, transaction.atomic() rolls everything back.

Outside APIs: The Polygon API, same calls as Flow 2.

Database: Reads the Problem row. Writes to Problem, ProblemTag (through extra_tags) and SampleTestCase. Models are in problems/models.py.

User sees: The problem page again with a success message. On failure, the message says the migration failed and all changes were rolled back.

**Flow 4: Migrating test cases to the database**

Click: The user clicks Migrate Test Description to Database. The problem must already be in the database.

Sends: A POST to "/" with problem_id and the flag migrate_test_cases_to_db.

Backend: Same start as Flow 2. If the problem is not in the database, the view stops with an error. Otherwise, for each test it cuts the input and output to the first 260 characters and creates or updates one ProblemTestCase row. Any failure rolls everything back.

Outside APIs: The Polygon API, mainly the list of tests, problem.testInput and problem.testAnswer.

Database: Reads the Problem row. Writes ProblemTestCase rows. Only 260 characters of each input and output are kept, so these are short descriptions, not full tests.

User sees: The problem page with a success message, or an error if the problem was not saved first or the rollback message if it failed.

**Flow 5: Uploading test cases to cloud storage**

Click: The user clicks Migrate Test Cases to Cloud Storage. The problem must already be in the database.

Sends: A POST to "/" with problem_id and the flag migrate_to_azure, from the form migrate-azure-form. The Azure names are old and were kept so the view did not need to change.

Backend: The view checks that the problem exists and takes its database ID (problem_obj.id), because storage folders use this ID and not the Polygon ID. It checks for a custom checker with get_custom_checker_info. It sets the cleanup flags first, then calls api.migrate_to_azure_blob(polygon_id, problem_id). That method gets the backend from get_storage() (problems/storage/__init__.py), which returns GCSBackend (problems/storage/gcs.py). For each test it uploads the input and the answer, skipping tests with an empty input or output. For a custom checker it fetches the source, compiles it with g++ and uploads the binary, or uploads the .cpp if compiling fails. On failure, the except block calls api.delete_azure_blob to delete the uploaded files, and the database is rolled back.

Outside APIs: The Polygon API for the checker and the tests, and the Google Cloud Storage API for the uploads and the rollback delete.

Storage: Writes test_cases/{db_problem_id}/{NN} for inputs, test_cases/{db_problem_id}/{NN}.a for answers, and custom_checker, custom_checker.exe or custom_checker.cpp for the checker. On failure it deletes everything under that folder. Nothing new is written to PostgreSQL.

User sees: The problem page with a success message, or the rollback message on failure. To check, look in the bucket for test_cases/<db id>/01, 01.a, 02, 02.a and so on.