# GUID API
An example of a REST API built in Python that utilizes Redis. This was built in Python 3.5.2.

## Project Setup (Using Python 3)
0) Note: You will likely need to set up a virtualenv to run this on Mac. I found this very useful in doing that, if you’re not familiar (https://hackercodex.com/guide/python-development-environment-on-mac-osx/). Once you have created your foobar3 directory from that link, enter into your virtualenv with the ```source foobar3/bin/activate``` command. Now follow the steps below to run the app.
1) In the project directory run
 ```pip install -r /path/to/requirements.txt```. This will install project requirements. I have also included a development_requirements file to show what I was using to aid development which you can install using the same method, but it's not necessary to run the service.
 2) I'm using MongoDB (https://docs.mongodb.com/manual/installation/) as my backend. I didn't have time to get a server set up, so the app is expecting an instance to be running on your local machine. You can find the appropriate install for your OS at the link provided as well as instructions on how to get a local copy running.
 3) I used Redis for the cache. I don't have a conf file included but defaults should work. You can find the installer here http://redis.io/download. This will also help for Mac (http://jasdeep.ca/2012/05/installing-redis-on-mac-os-x/)


## To Run
1) Open a terminal in the project ```src``` directory. Run the ```python guid_server.py``` command to start the server. The default port is 3000.
    2) I recommend using a request tool such as Postman (https://chrome.google.com/webstore/detail/postman/fhbjgbiflinjbdggehcddcbncdddomop?hl=en) to test the app.

## To Test
1) Open a terminal in the project directory and run the ```py.test``` command, alternatively, you can install the development_requirements and run ```sniffer```

## Branching Methodology
1) I used the basic parts of this branching model (http://nvie.com/posts/a-successful-git-branching-model/). I have a master branch that represents commits to production, and commits to develop that represent steps towards a release. Each commit to develop should be green on tests and should build. Separate branches have been created to add features.

## File structure
 * ./requirements.txt -- A file to be used with pip to install the requirements for the app.
 * ./README.md -- A description of the project
 * ./task_list.txt -- A working task list I used to track tickets/issues/requirements
 * ./development_requirements.txt -- A list of optional requirements used during development
 * ./src/ -- contains all source files for the project
 * ./src/guid_server.py -- The main file for the app. This starts the app listening on port 3000 and is called when unit tests are run.
 * ./src/test_guid.py -- The test file for the app. Run with the ```py.test``` command.
 * ./src/validators/ -- Contains all functions used to validate client input.
 * ./src/validators/guidValidator.py -- Contains functions to validate user input such as GUID, expiration, etc.
 * ./src/endpoints/guid.py -- The main driver for the app. This handles the GET, POST, and DELETE requests sent to the API.
 * ./src/CRUDLib/ -- This contains all functions that handle CRUD operations with external servers
 * ./src/CRUDLib/mongoCacheCRUD.py -- This file contains wrapper functions that pair cache and DB read/writes
 * ./src/constants -- This file contains a number of constants and currently doubles as a configuration file.

## Known Major Issues
1) POSTS that include an expiration date before now() are currently accepted (as long as they're a valid timestamp).
2) Guids that are past their expiration point are not handled in any way. They should be deleted when someone tries to access them.

## Planned Improvements
1) Asynch Redis cache
2) Remote Redis server
3) Remote Mongo server
4) Include hypermedia controls in response
5) Conform to a well known REST protocol. Probably JSON API (http://jsonapi.org/)
6) Report errors through response body instead of just through headers
7) Add unit tests for caching functionality
8) Refactor ./src/test_guid.py
9) Factor out magic numbers (specifically connection ports)
10) Create actual configuration file (refactor constants file)
11) Currently I'm accepting anything on the /guid/ endpoint and then validating after the request is received. Need to improve this regex.
12) Reduce entropy of style.

## Validations
1) On a POST, the "user" field must be present and non-blank.
2) GUIDs from the user must always conform to the length and content requirements of the spec.
3) DELETE and GET requests must have a GUID present in the URL.
4) Expire values sent along must be valid Unix timestamps.
5) The body of a POST must be valid JSON.