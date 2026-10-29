**Issues Analysis**

This file lists the three most important product issues and the three most important code issues in the Polygon migration tool. Each group is ranked from highest to lowest priority. The four edge case questions are answered at the end.

**Summary**

Product issues: 0 critical, 1 high, 2 medium, 0 low. Total 3.

Code issues: 0 critical, 1 high, 2 medium, 0 low. Total 3.

**Product Issues**

**[P1] Tests with empty input or output are skipped, but the page says the migration worked**

Severity: High.

Location: problems/polygon_api.py, in migrate_to_azure_blob (the part that uploads each test).

Description: When the tool uploads tests to the bucket, it skips any test whose input or output is empty. It does this without telling the user. At the end the page still shows a success message. Some real problems have a test with an empty answer, so this can happen on good data.

Impact: The bucket can end up with fewer tests than Polygon has. The judge will then check solutions against fewer tests, and a wrong solution may pass. Nobody notices, because the screen says success. The staff user who ran the migration is the one who is misled.

Suggested Fix: Count how many tests Polygon returned and how many were uploaded. Show both numbers on the page. If some were skipped, show a warning with the test numbers. Better still, upload tests with an empty answer, because that is a valid test.

**[P2] The database keeps cut-off tests that look like full tests**

Severity: Medium.

Location: problems/models.py (ProblemTestCase) and the Migrate Test Description to Database action in problems/views.py.

Description: This action saves only the first 260 characters of each input and output into ProblemTestCase. The fields are called input and output, so anyone reading the table or the admin page thinks they hold the whole test. Nothing on the page or in the data says that the text was cut.

Impact: A person who debugs a problem from the database sees wrong data. Any feature that reads ProblemTestCase and expects the full test will give wrong results. The cut can fall in the middle of a number or a line, which looks like a real mistake in the test.

Suggested Fix: Rename the fields or add a flag such as is_truncated. Show a note on the button that only 260 characters are saved. Or save the bucket file path in the row, so the full test can always be found.

**[P3] Running Create/Update again changes saved data without any warning**

Severity: Medium.

Location: problems/views.py, in the migrate_to_db action, and problems/templates/problems/index.html (the database form).

Description: When the problem already exists, the button overwrites it with the data from Polygon. It also deletes the old tags and writes the tags that are in the tag picker. The page asks for a difficulty every time, so the user has to choose it again. There is no message that says this problem already exists and will be overwritten.

Impact: A staff member can lose tags or edits that were made on our side. They can also change the difficulty by mistake while they only wanted to refresh the statement. The loss is silent, so it is found much later.

Suggested Fix: When the problem already exists, show a clear message and ask for confirmation before saving. Fill the tag picker and the difficulty with the saved values first, so a re-run keeps them unless the user changes them.

**Code Issues**

**[C1] A failed re-migration deletes the good test files that were already in the bucket**

Severity: High.

Location: problems/views.py (the except block of the storage migration) and problems/polygon_api.py (delete_azure_blob).

Description: The view sets the uploaded flag to True before the migration starts. If anything fails, the rollback calls delete_azure_blob, which deletes everything under test_cases/{db_problem_id}/. This works well for a first migration. But if the problem was migrated before and the second run fails halfway, the rollback also deletes the older good files.

Impact: The judge can lose all test files for a problem because of one network error in a later run. The files can be made again by migrating once more, but until then the problem cannot be judged. It is a data loss that the user did not ask for.

Suggested Fix: Remember which keys were uploaded in this run and delete only those. Or check first whether the folder already had files, and skip the folder-wide delete in that case. Another option is to upload to a temporary folder and move the files into place only when all uploads worked.

**[C2] Slow Polygon calls run on every click and inside an open database transaction**

Severity: Medium.

Location: problems/views.py (the index view, the transaction.atomic block) and problems/polygon_api.py (get_all_test_cases).

Description: The view opens transaction.atomic() and then, on every click, it fetches the problem info, downloads the whole problem package and loads the test cases. This includes the Fetch Problem button, which saves nothing. Loading the tests uses two Polygon calls for each test, one after the other. All of this happens while the database transaction is open.

Impact: The page is slow, especially for problems with many tests. The database connection and any locks stay open during the slow network calls. If Polygon is slow or fails, the whole request fails, even for actions that did not need those calls.

Suggested Fix: Do the Polygon calls before opening the transaction, and open it only around the database writes. Fetch the package and the tests only for the actions that need them. Cache the parsed package in Redis like the tests, and make the test downloads run in parallel with a small limit.

**[C3] The data model has no guard rails against duplicates and wrong counts**

Severity: Medium.

Location: problems/models.py (Problem, SampleTestCase, ProblemTestCase).

Description: There are three small problems. First, polygon_id is unique but also allows blank, so only one problem can ever have an empty polygon_id, and a second one will fail in a confusing way. Second, SampleTestCase and ProblemTestCase have no rule that makes problem and order unique together, so two runs at the same time can create two rows with the same order. Third, test_case_count is a separate number that is saved by hand, so it can disagree with the real number of rows or with the files in the bucket.

Impact: Duplicate test rows give wrong results when the tests are shown or judged. A wrong test_case_count can make the judge look for files that are not there. The blank polygon_id case gives a hard-to-read database error.

Suggested Fix: Add a unique constraint on problem and order for both test tables. Remove blank=True from polygon_id, or use null with unique. Calculate test_case_count from the real rows, or update it in the same place that creates the rows.

**Edge Case Analysis**

**Q1: A Polygon problem has 0 sample test cases but 15 regular test cases. What happens when you migrate this problem?**

Nothing in the models needs a sample, so the migration works. The Create/Update button saves the Problem row and creates zero SampleTestCase rows. The problem page will show no examples in the statement. Migrating the test files uploads all 15 tests to the bucket, as 01 to 15 with their .a answer files, because that step does not depend on samples. Migrating the descriptions creates 15 ProblemTestCase rows with is_sample set to False. The only risk is in how the code picks out the samples. If it assumes at least one sample exists, it could fail. The tool should also show a warning, because a problem with no examples is probably a mistake in Polygon.

**Q2: A problem is migrated with 20 test cases. Later, the problem setter removes 8 test cases on Polygon (now 12 remain). The problem is re-migrated. What happens?**

The first 12 tests are written again, so they match Polygon. The risk is in the 8 tests that are gone. In the bucket, files 13 to 20 and their .a files stay there, unless the migration first clears the folder. The storage base class has an empty_blob function that can do this, so the code must be checked to see if it calls it. In the database, the ProblemTestCase rows for order 13 to 20 also stay unless the code deletes them, because creating or updating rows by order never removes extra rows. If they stay, the judge may still see 20 tests, and 8 of them are old tests that no longer exist on Polygon. The test_case_count should also be set to 12.

**Q3: Two different Polygon problems have the exact same title: "Two Sum". You migrate the first one successfully. Then you try to migrate the second one. What happens?**

The two problems have different Polygon IDs, so polygon_id does not clash. The title is not unique either. But the slug must be unique. If the slug is made from the title, both problems get the slug two-sum. In that case the second save fails with a database integrity error, the transaction is rolled back, and the user sees the message that the migration failed. The first problem is not touched. If the code instead finds the problem by slug and updates it, the second problem would overwrite the first one, which is worse. If the code adds a number or the Polygon ID to the slug, both problems are saved. The safe fix is to add the Polygon ID or a counter to the slug and to show the real reason when it fails.

**Q4: When test cases are saved to the database via Migrate Test Cases to DB, some data is intentionally discarded. What data is lost? Why might this cause problems?**

Only the first 260 characters of each input and each output are kept. Everything after that is lost. This includes the rest of long inputs, such as big arrays or graphs, and the rest of long outputs. The exact full text is not in the database at all. It exists only in the bucket.

This can cause problems in four ways. First, the saved text looks like the full test, because the fields are called input and output. Second, the cut can happen in the middle of a number or a line, so the data looks broken. Third, the database copy cannot be used to judge a solution or to compare with the bucket file, because it does not match. Fourth, any code that reads ProblemTestCase and expects the full test will give wrong results, and nobody gets an error.

**Notes**

The code still has Azure names in many places, such as migrate_to_azure, migrate_to_azure_blob, delete_azure_blob and the form id migrate-azure-form. They work with Google Cloud Storage now, but they are confusing and should be renamed in one clean change. The old file problems/AzureTestcase.py is still in the project, and the folder problems also has a stray copy of gcs.py next to views.py. The README still describes Azure Blob Storage and does not mention Google Cloud Storage. The tests and the database are not covered by one single transaction, so a database save and a bucket upload can end in different states when something fails.
