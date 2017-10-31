#comment
import re
import random
import string
import hashlib

def format_text_bold(text_inputstring):
	text_string = text_inputstring.group()
	text_outputstring = "<b>"+text_string[1:-1]+"</b>"
	return text_outputstring
	
def format_text_links(text_inputstring):
	text_string = text_inputstring.group()
	if text_string[0:4] == "http":
		text_outputstring = "<a href=\"" + text_string + "\">" + text_string + "</a>"
	else:
		text_outputstring = "<a href=\"http://" + text_string + "\">" + text_string + "</a>"
	return text_outputstring
	
def validate_password(password_inputstring):
	if re.match(r'^[A-Za-z0-9@#$%^!?&+=]{6,}$', password_inputstring):
		return password_inputstring
	else:
		return None	
		
def validate_uri(uri_inputstring):
	if re.match(r'^[A-Za-z0-9\-]{2,160}$', uri_inputstring):
		uri_inputstring = uri_inputstring.lower()
		return uri_inputstring
	else:
		return None	
		
#function make_salt returns a string of 5 random characters

def make_salt():
	return ''.join(random.choice(string.letters) for x in xrange(5))
	
# function make_pw_hash(name, pw) returns a hashed password 
# of the format: 
# HASH(name + pw + salt),salt
# use sha256

def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return '%s,%s' % (h, salt)
	
# function valid_pw() returns True if a user's password 
# matches its hash
	
def valid_pw(name, pw, h):
	salt = h.split(',')[1]
	return h == make_pw_hash(name, pw, salt)
