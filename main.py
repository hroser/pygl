# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# import library os for reading path directory name ..
import os
import datetime

# for routing subdomains
from webapp2_extras import routes

# for logging
import logging


# for working with regular expressions
import re

# to be able to import jinja2 , add to app.yaml
import jinja2
import webapp2

# for storing data in google cloud storage
import logging
import lib.cloudstorage as gcs

from google.appengine.api import app_identity

# for using datastore 
from google.appengine.ext import ndb
from google.appengine.api import images
from base64 import b64encode
from base64 import b64decode

# validate user inputs
import validate 

# use pygl tools
import pygltools as pt

# for REST APIs
import urllib
import urllib2
import json

# tell jinja2 where to look for files
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

class Pyglpage(ndb.Model):
	"""Models a pygl page"""
	created = ndb.DateTimeProperty(auto_now_add=True)
	last_edit = ndb.DateTimeProperty(auto_now_add=True)
	login_fail_last = ndb.DateTimeProperty()
	pygl_uri = ndb.StringProperty()
	password_hash = ndb.StringProperty()
	title = ndb.StringProperty()
	text0 = ndb.TextProperty()
	text1 = ndb.TextProperty()
	comments_active = ndb.BooleanProperty()
	login_fails_consec = ndb.IntegerProperty()		# consecutive login fails
	abuse_report_count = ndb.IntegerProperty()		# count abuse reports
	#image_id_0 = ndb.IntegerProperty()
	image_id0 = ndb.StringProperty()
	
class Pageviews(ndb.Model):
	"""Models a page view counter"""
	views = ndb.IntegerProperty()
	
class Pageimage(ndb.Model):
	"""store image name and id"""
	page_id = ndb.StringProperty()
	original_filename = ndb.StringProperty()
	
class Abusereport(ndb.Model):
	"""store abuse report comment and id"""
	page_id = ndb.StringProperty()
	comment = ndb.TextProperty()
	
class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		if 'de' in self.request.headers.get('Accept-Language').split(",")[0]:
			# de
			#template = template + '-de.html'	# not used
			template = template + '-en.html'
		else:
			# en
			template = template + '-en.html'
		# undo escaping of <b> and </b>
		output = self.render_str(template, **kw).replace("&lt;b&gt;","<b>").replace("&lt;/b&gt;","</b>")
		# undo escaping of </a>, "> and < a href=\"
		output = output.replace("&lt;/a&gt;","</a>").replace("&#34;&gt;","\">").replace("&lt;a href=&#34;","<a href=\"")
		self.write(output)

class MainPage(Handler):
	def get(self):
		self.response.out.write(self.request.headers.get('Accept-Language'))
		self.render('create-page', comments_checked="checked")
		
		#logging.info("hello")
		
	def post(self):

		err_title = False
		err_uri_not_available = False
		err_uri_invalid = False
		err_passwort_format = False
		err_password_retype = False
		err_captcha = False
	
		page_uri = self.request.get('page_uri')
		page_uri_val = pt.validate_uri(page_uri)
		page_title = self.request.get('page_title')
		page_text0 = self.request.get('page_text0')
		page_text1 = self.request.get('page_text1')
		if self.request.get('comments_active'):
			comments_active = True
			comments_checked = "checked"		# for reloading page when error
		else:
			comments_active = False
			comments_checked = ""
		page_password = pt.validate_password(self.request.get('page_password'))
		page_repassword = self.request.get('page_repassword')
		#page_image = self.request.get('preview_image')		#TODO verify
		#page_image = self.get_uploads()[0]
		#pygl_page = PyglPage(pygl_id=page_id, password=page_password, title=page_title, text=page_text, image=page_image.file.read())
		
		
		page_image_id0 = self.request.get('image_id0')		#TODO verify
		logging.info("id:"+page_image_id0)
		
		
		if page_uri_val:
			page_id = page_uri_val.replace("-","")
			# check if page already exists
			key = ndb.Key(Pyglpage, page_id)
			page = key.get()
			if page:
				err_uri_not_available = True
		else:
			err_uri_invalid = True
			
		#if (page_title == "") and (page_text0 == "") and (page_text1 == "") and (not page_image):
			#err_title = True
			
		if (not page_password):
			err_passwort_format = True
		
		if page_password and (page_password != page_repassword):
			err_password_retype = True
			
		if (err_uri_not_available == True) or (err_title == True) or (err_password_retype == True) or (err_uri_invalid == True) or (err_passwort_format == True):
			self.render('create-page', page_title = page_title, page_text0 = page_text0, page_text1 = page_text1, 
				page_uri = page_uri, comments_checked=comments_checked, err_uri_not_available=err_uri_not_available, 
				err_title=err_title, err_password_retype=err_password_retype, err_uri_invalid=err_uri_invalid, 
				err_passwort_format=err_passwort_format, err_captcha=err_captcha)
			return
			
		######################
		
		# sample query
		
		# query = Pyglpage.query(Pyglpage.pygl_id == page_id).fetch(1)	# query page
		# page = query[0]
		
		######################
		
		
		pygl_page = Pyglpage(id=page_id)
		pygl_page.pygl_uri = page_uri_val
		pygl_page.password_hash = pt.make_pw_hash(page_id, page_password)
		pygl_page.title = page_title
		pygl_page.text0 = page_text0
		pygl_page.text1 = page_text1
		pygl_page.comments_active = comments_active
		pygl_page.login_fails_consec = 0
		pygl_page.abuse_report_count = 0
		
		
		# save image id in page datastore entity
		pygl_page.image_id0 = page_image_id0
		
		
		page_views = Pageviews(id=page_id)
		page_views.views = 0
		page_views.put()
		
		datastore_image = Pageimage()
		datastore_image.pygl_id = page_id
		
		
		

		
		
		##page_image = images.resize(self.request.get("page_image"), 32, 32)
		##page_image = self.request.get('page_image')
		
		#also get filename
		#datastore_image.original_filename = 
		
		##page_image = images.resize(page_image, 800, 600)
		"""
		if page_image:
			
			#####################
			# image upload
			
			image_key = datastore_image.put()
			image_id = image_key.id()
			self.response.out.write(image_id)
			
			# save image id in page datastore entity
			pygl_page.image_id0 = image_id
			
			#bucket_name = "pygl-page.appspot.com"
			# alternativ bucket name automatisch setzen:
			# dann muss aber in der lokalen Entwicklungsumgebung 
			# dev_appserver.py . --default_gcs_bucket_name=pygl-page.appspot.com
			# benutzt werden
			bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
			
			# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
			filename = str(image_id)
			gcs_file = gcs.open('/' + bucket_name + '/images/' + filename, 'w', content_type='image/jpeg')
			#gcs_file = gcs.open('/pygl-page.appspot.com/testfile', 'w', content_type='image/jpeg')
			gcs_file.write(page_image)
			gcs_file.close()
			
			#####################
		"""
		''' Begin reCAPTCHA validation '''
		recaptcha_response = self.request.get('g-recaptcha-response')
		recaptcha_url = 'https://www.google.com/recaptcha/api/siteverify'
		values = {'secret': "6Le1hicUAAAAAAX3u5ccpJ08kFecBLdZQnbi77iz", 'response': recaptcha_response}
		if recaptcha_response:
			# get info from recaptcha server
			data = urllib.urlencode(values)
			req = urllib2.Request(recaptcha_url, data)
			response = urllib2.urlopen(req)
			result = json.load(response)
			if result['success']:
				pygl_page.put()
				self.redirect("/" + page_uri_val)
			else:
				err_captcha = True
				self.render('create-page', page_title = page_title, page_text0 = page_text0, page_text1 = page_text1, 
					page_uri = page_uri, comments_checked=comments_checked, err_uri_not_available=err_uri_not_available, 
					err_title=err_title, err_password_retype=err_password_retype, err_uri_invalid=err_uri_invalid, 
					err_passwort_format=err_passwort_format, err_captcha=err_captcha)
		else:
			err_captcha = True
			self.render('create-page', page_title = page_title, page_text0 = page_text0, page_text1 = page_text1, 
				page_uri = page_uri, comments_checked=comments_checked, err_uri_not_available=err_uri_not_available, 
				err_title=err_title, err_password_retype=err_password_retype, err_uri_invalid=err_uri_invalid, 
				err_passwort_format=err_passwort_format, err_captcha=err_captcha)
		''' End reCAPTCHA validation '''
		
		
		
class PyglPage(Handler):
	def get(self, requested_uri):
		
		# load page
		requested_id = requested_uri.replace("-","").lower()		#TODO verify
		key = ndb.Key(Pyglpage, requested_id)
		page = key.get()

		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return
		
		
		if (page.pygl_uri != requested_uri):
			self.redirect("/" + page.pygl_uri)
			return
		
		
		#format text
		page_text_formatted0 = re.sub(r"[a-zA-Z0-9_.+-/:?#%&$=]+\.[a-zA-Z0-9_.+-/:?#@%&$=]+", pt.format_text_links, page.text0)
		page_text_formatted0 = re.sub(r"\*(.*?)\*", pt.format_text_bold, page_text_formatted0)
		page_text_formatted1 = re.sub(r"[a-zA-Z0-9_.+-/:?#%&$=]+\.[a-zA-Z0-9_.+-/:?#@%&$=]+", pt.format_text_links, page.text1)
		page_text_formatted1 = re.sub(r"\*(.*?)\*", pt.format_text_bold, page_text_formatted1)
		
		#######################
		
		# could cause performance issue, only about 5 writes per seconds
		# possible solution: sharding
		
		# get pageviews
		key = ndb.Key(Pageviews, requested_id)
		page_views = key.get()
		
		# count page view
		page_views.views = page_views.views + 1
			
		# update datastore entry
		page_views.put()
		
		########################
		
		self.render('page', page_title=page.title, page_text0=page_text_formatted0, page_text1=page_text_formatted1, comments_active = page.comments_active, page_views=page_views.views, page_created = page.created.date(), page_last_edit = page.last_edit.date(), pygl_uri=page.pygl_uri, image_id0=page.image_id0)
		
		return
		
		# not used
		#
		#if page.image_id:
		#	bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
		#	
		#	# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
		#	filename = str(page.image_id)
		#	page_image = gcs.open('/' + bucket_name + '/images/' + filename)
		#	#image = b64encode(page_image)			
		#	self.render('page.html', page_title=page.title, page_text0=page_text_formatted0, page_text1=page_text_formatted1, comments_active = page.comments_active, page_views=page_views.views, page_created = page.created.date(), page_last_edit = page.last_edit.date(), pygl_uri=page.pygl_uri, image_id=image_id)
		#	page_image.close()
		#else:
		#	#self.render('page.html', page_title=page.title, page_text0=page_text_formatted0, page_text1=page_text_formatted1, comments_active = page.comments_active, page_views=page_views.views, page_created = page.created.date(), page_last_edit = page.last_edit.date(), pygl_uri=page.pygl_uri)
		#	self.render('page.html', page_title=page.title, page_text0=page_text_formatted0, page_text1=page_text_formatted1, comments_active = page.comments_active, page_views=page_views.views, page_created = page.created.date(), page_last_edit = page.last_edit.date(), pygl_uri=page.pygl_uri)
		
		
class PyglPageEdit(Handler):
	def get(self, edit_uri):
		self.render('checkpassword')
	
	def post(self, edit_uri):
	
		password = self.request.get('password')
		
		# load page
		edit_id = edit_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, edit_id)
		page = key.get()
		
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return
		
	
		save_page = self.request.get('save_page')
		
		if (page.login_fails_consec >= 3) and ((datetime.datetime.utcnow() - page.login_fail_last) < datetime.timedelta(minutes=10)):
			self.response.out.write("sorry, wrong password 3 times, please wait 10 minutes")
			return
		
		if pt.valid_pw(edit_id, password, page.password_hash):
			page.login_fails_consec = 0		
			page.put()
		else:
			self.response.out.write("sorry, wrong password")
			page.login_fails_consec = page.login_fails_consec + 1
			page.login_fail_last = datetime.datetime.utcnow()			# remember last failed login datetime
			page.put()
			return
		
		
		if (save_page == "True"):
		
			''' Begin reCAPTCHA validation '''
			recaptcha_response = self.request.get('g-recaptcha-response')
			recaptcha_url = 'https://www.google.com/recaptcha/api/siteverify'
			values = {'secret': "6Le1hicUAAAAAAX3u5ccpJ08kFecBLdZQnbi77iz", 'response': recaptcha_response}
			if recaptcha_response:
				# get info from recaptcha server
				data = urllib.urlencode(values)
				req = urllib2.Request(recaptcha_url, data)
				response = urllib2.urlopen(req)
				result = json.load(response)
				if result['success']:
				
					page_title = self.request.get('page_title')		#TODO verify
					page.title = page_title
					page_text0 = self.request.get('page_text0')		#TODO verify
					page.text0 = page_text0
					page_text1 = self.request.get('page_text1')		#TODO verify
					page.text1 = page_text1
					if self.request.get('comments_active'):
						page.comments_active = True
					else:
						page.comments_active = False
					page.last_edit = datetime.datetime.utcnow()
					
					page.put()
					self.redirect("/" + page.pygl_uri)
				else:
					self.response.out.write("check failed")
			else:
				self.response.out.write("please check the recaptcha")
			''' End reCAPTCHA validation '''
		
		else:
			if page.comments_active:
				comments_checked = "checked"
			else:
				comments_checked = ""
			self.render('edit-page', page_title=page.title, page_text0=page.text0, page_text1=page.text1, page_uri=page.pygl_uri, comments_checked=comments_checked)
		
class PyglReportAbuse(Handler):
	def get(self, report_uri):
		
		# load page
		report_id = report_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, report_id)
		page = key.get()
		
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return

		self.render('report-abuse-page', page_uri=page.pygl_uri)
		
	def post(self, report_uri):
	
		''' Begin reCAPTCHA validation '''
		recaptcha_response = self.request.get('g-recaptcha-response')
		recaptcha_url = 'https://www.google.com/recaptcha/api/siteverify'
		values = {'secret': "6Le1hicUAAAAAAX3u5ccpJ08kFecBLdZQnbi77iz", 'response': recaptcha_response}
		if recaptcha_response:
			# get info from recaptcha server
			data = urllib.urlencode(values)
			req = urllib2.Request(recaptcha_url, data)
			response = urllib2.urlopen(req)
			result = json.load(response)
			if result['success']:
				
				report_id = report_uri.replace("-","")
		
				# load page
				key = ndb.Key(Pyglpage, report_id)
				page = key.get()
				
				if not page:
					self.response.out.write("sorry, pygl-page does not exist")
					return
				
				abuse_report = Abusereport()
				abuse_report.page_id = report_id
				abuse_report.comment = self.request.get('abuse_report_comment')
				abuse_report.put()
				
				page.abuse_report_count = page.abuse_report_count + 1
				page.put()
				self.response.out.write("thank you for reporting")
			else:
				self.response.out.write("check failed")
		else:
			self.response.out.write("please check the recaptcha")
			''' End reCAPTCHA validation '''
	
		
class GetImage(Handler):
	def get(self):
		image_id = self.request.get('q')
		
		bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
		# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
		filename = str(image_id)
		page_image = gcs.open('/' + bucket_name + '/images/' + filename)
		self.response.headers.add_header('Content-Type',"image/jpeg; charset=utf-8")
		self.response.out.write(page_image.read())
		
		page_image.close()
		
		
class UploadImage(Handler):
	def post(self):
		name = self.request.get('name')
		data = self.request.get('dataurl')
		
		datastore_image = Pageimage()
		#datastore_image.pygl_id = page_id
		image_key = datastore_image.put()
		image_id = image_key.id()
		self.response.out.write(image_id)
		
		#bucket_name = "pygl-page.appspot.com"
		# alternativ bucket name automatisch setzen:
		# dann muss aber in der lokalen Entwicklungsumgebung 
		#dev_appserver.py . --default_gcs_bucket_name=pygl-page.appspot.com
		# benutzt werden
		bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())
		
		# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
		filename = str(image_id)
		gcs_file = gcs.open('/' + bucket_name + '/images/' + filename, 'w', content_type='image/jpeg')
		
		# base64 encoded format is:
		# data:image/jpeg;base64,datastring
		# we only need the datastring part
		gcs_file.write(b64decode(data.split(';')[1][7:]))
		gcs_file.close()

		
app = webapp2.WSGIApplication([
    ('/', MainPage),
    webapp2.Route(r'/r/image', handler=GetImage),
    webapp2.Route(r'/r/upload', handler=UploadImage),
    webapp2.Route(r'/<edit_uri>/edit', handler=PyglPageEdit),
    webapp2.Route(r'/<report_uri>/report-abuse', handler=PyglReportAbuse),
    webapp2.Route(r'/<requested_uri>', handler=PyglPage),
    routes.DomainRoute('<requested_uri>.8080-dot-1957920-dot-devshell.appspot.com', [webapp2.Route('/', handler=PyglPage)]),
    routes.DomainRoute('<requested_uri>.pygl-page.appspot.com', [webapp2.Route('/', handler=PyglPage)]),
    routes.DomainRoute('<requested_uri>.py.gl', [webapp2.Route('/', handler=PyglPage)]),
], debug=True)





