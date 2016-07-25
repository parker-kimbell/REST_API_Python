# Invalid request errors
DELETE_INVALID = "DELETE requests require a GUID in the request URL"
GET_INVALID = "GET requests require a GUID in the request URL"
USER_INVALID = "User property must be present and non-blank in a POST request"
TIMESTAMP_INVALID = "Expire property must be valid UNIX timestamp"
GUID_INVALID = "Given GUID is malformed. GUIDs must be 32 character hexadecimal strings with all uppercase letters."

# The amount of time a GUID will exist on the server
DEFAULT_EXPIRE_TIME = 30

#TODO: Move this conf to an actual configuration file
# Names test and production collections, respectively
TEST_COLLECTION = "test_guids"
COLLECTION = "guids"

# DBs for our test Redis DB and our production Redis DB, respectively
TEST_REDIS_DB = 1
REDIS_DB = 0

#URLs for our connections to our cache and DB, respectively
REDIS_URL = "localhost"
MONGO_URL = "localhost"
 