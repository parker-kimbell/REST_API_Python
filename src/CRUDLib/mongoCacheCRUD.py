from tornado.escape import json_decode
from tornado import gen

@gen.coroutine
def readGuid(guid_collection, client_guid, cache):
	cached_guid = cache.get(client_guid) 
	if (cached_guid): # Case: We have found an instance of this guid in this cache so we will decode and return it
		return json_decode(cached_guid.decode('utf-8').replace("'", '"'))
	else: # Case: There is no cached version of this guid, so we need to determine if the guid exists in the database or not
		found_guid = yield guid_collection.find_one({"guid" : client_guid})
		if (found_guid): # Case: The guid exists in the database, so we clean it and cache it before returning it
			# Remove the native _id that Mongo inserts into collections as it cannot be serialized
			del found_guid['_id']
			cache.set(found_guid['guid'], found_guid)
			return found_guid
		else: # Case: The guid does not exist
			return None

@gen.coroutine		
def updateGuid(guid_collection, updated_guid, existing_guid, cache):
	yield guid_collection.update({"guid" : existing_guid["guid"]}, {
		"$set" : updated_guid
	})
	# Add the existing guid property into the JSON object we're about to return as this is part of the spec
	updated_guid["guid"] = existing_guid["guid"]
	cache.set(updated_guid["guid"], updated_guid)
	return updated_guid

@gen.coroutine
def insertGuid(guid_collection, new_guid, cache):
	yield guid_collection.insert(new_guid)
	# Remove the Mongo ID that was inserted after our insert because it is not part of the spec
	del new_guid["_id"]
	cache.set(new_guid["guid"], new_guid)
	return new_guid

def deleteGuid(guid_collection, client_guid, cache):
	guid_collection.remove({"guid" : client_guid})
	cache.delete(client_guid)