import re
import os
import binascii
from calendar import timegm
import datetime
import constants.constants as constants

# This function will return a spec-valid GUID if passed a falsey parameter.
# If passed an invalid guid it will raise an exception
# If passed a valid guid it will return the valid guid
def validateGuid(client_guid):
	if(client_guid):
		if(guidIsValid(client_guid)):
			return client_guid
		else:
			raise Exception(constants.GUID_INVALID)
	else:
		return createRandom32CharHexString() 

def createRandom32CharHexString():
	# This function first creates a random string of 16 bytes. We create 16 because the 
	# following call to binascii.b2a_hex converts each byte into its two digit Hex equivalent, giving us a 32 byte length string.
	# This string is then decoded into a utf-8 string since that's what we're using throughout the rest of the project,
	# and finally all lower case letters are converted to uppercase.
	return binascii.b2a_hex(os.urandom(16)).decode("utf-8").upper()

def guidIsValid(client_guid):
	# This regex will match on strings that are exactly 32 characters in length, and that contain only 
	# combinations of the numbers 0 through 9 and the uppercase letters A through F
	# Example 9094E4C980C74043A4B586B420E69DDF
	return re.match("^[0-9A-F]{32}$", client_guid)

def validateExpire(body):
	if ("expire" in body):
		if (expirationIsValid(body["expire"])):
			return body["expire"]
		else:
			raise Exception(constants.TIMESTAMP_INVALID)
	else:
		return createTimestampPlus30Days()		

def expirationIsValid(expiration):
	try:
		datetime.datetime.fromtimestamp(int(expiration)).strftime('%Y-%m-%d %H:%M:%S')
		print ('guid expiration is valid')
		return True
	except:
		print("Time stamp is invalid")
		return False

# Returns a Unix timestamp representing the time 30 days after it was called
def createTimestampPlus30Days():
	print ('creating time stamp on server')
	thirtyDaysInTheFuture = datetime.datetime.utcnow() + datetime.timedelta(days=constants.DEFAULT_EXPIRE_TIME)
	# This step converts our time tuple into a unix timestamp
	return timegm(thirtyDaysInTheFuture.timetuple())

def validateUser(body):
	if ("user" in body and body["user"] != ""):
		return body["user"]
	else:
		raise Exception(constants.USER_INVALID)