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
from google.appengine.api import mail

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
	email = ndb.StringProperty()
	title = ndb.StringProperty()
	text0 = ndb.TextProperty()
	text1 = ndb.TextProperty()
	text2 = ndb.TextProperty()
	comments_active = ndb.BooleanProperty()
	login_fails_consec = ndb.IntegerProperty()		# consecutive login fails
	abuse_report_count = ndb.IntegerProperty()		# count abuse reports
	image_id0 = ndb.StringProperty()
	image_id1 = ndb.StringProperty()
	image_id2 = ndb.StringProperty()
	
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
	report_date = ndb.DateTimeProperty(auto_now_add=True)
	
class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		#cookie = kw.get('cookie', None)
		#if cookie:
		#	self.response.set_cookie('some_key', 'value', max_age=86400, path='/', domain='py.gl', secure=False)
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, cookie = None, **kw):
		"""
		problem mit none:
		'NoneType' object has no attribute 'split'
		if 'de' in self.request.headers.get('Accept-Language').split(",")[0]:
			# de
			#template = template + '-de.html'	# not used
			template = template + '-en.html'
		else:
			# en
			template = template + '-en.html'
		"""
		template = template + '-en.html'
		# undo escaping of <b> and </b>
		#output = self.render_str(template, **kw).replace("&lt;b&gt;","<b>").replace("&lt;/b&gt;","</b>")
		# undo escaping of <center> and </center>
		#output = output.replace("&lt;center&gt;","<center>").replace("&lt;/center&gt;","</center>")
		# undo escaping of </a>, "> and < a href=\"
		#output = output.replace("&lt;/a&gt;","</a>").replace("&#34;&gt;","\">").replace("&lt;a href=&#34;","<a href=\"")
		output = self.render_str(template, **kw)
		#self.write(output, cookie = '1')
		#self.write(output)
		if cookie:
			if cookie[0] == 'set':
				self.response.set_cookie(cookie[1], cookie[2], max_age=86400, path='/', domain='py.gl', secure=False)
			if cookie[0] == 'del':
				self.response.delete_cookie(cookie[1], path='/', domain='py.gl')
		self.response.out.write(output)

class MainPage(Handler):
	def get(self):
	
		landing_text = ""
		# load from bucket
		bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
		# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
		try:
			gcs_file = gcs.open('/' + bucket_name + '/pages/' + 'pygl', 'r')
			landing_text = b64decode(gcs_file.read()).decode('utf-8')
			gcs_file.close()
		except:
			pass

		#self.response.out.write(self.request.headers.get('Accept-Language'))
		self.render('create-page', page_text0 = landing_text, comments_checked="checked")
		
	def post(self):

		err_title = False
		err_uri_not_available = False
		err_uri_invalid = False
		err_passwort_format = False
		err_password_retype = False
		err_captcha = False
		
		
	
		page_uri = self.request.get('page_uri')
		page_uri_val = pt.validate_uri(page_uri)
		#page_title = self.request.get('page_title')
		page_text0 = self.request.get('page_text0')
		#page_text1 = self.request.get('page_text1')
		#page_text2 = self.request.get('page_text2')
		if self.request.get('comments_active'):
			comments_active = True
			comments_checked = "checked"		# for reloading page when error
		else:
			comments_active = False
			comments_checked = ""
		page_password = pt.validate_password(self.request.get('page_password'))
		page_repassword = self.request.get('page_repassword')
		page_email = self.request.get('page_email')
		
		#page_image_id0 = self.request.get('image_id0')	
		#page_image_id1 = self.request.get('image_id1')	
		#page_image_id2 = self.request.get('image_id2')	
		#logging.info("image_id0:"+page_image_id0+" image_id1:"+page_image_id1+" image_id2:"+page_image_id2)
		
		
		if page_uri_val:
			page_id = page_uri_val.replace("-","").lower()
			# check if page already exists
			key = ndb.Key(Pyglpage, page_id)
			page = key.get()
			if page:
				err_uri_not_available = True
		else:
			err_uri_invalid = True
			
		if (not page_password):
			err_passwort_format = True
		
		if page_password and (page_password != page_repassword):
			err_password_retype = True
			
		if (err_uri_not_available == True) or (err_title == True) or (err_password_retype == True) or (err_uri_invalid == True) or (err_passwort_format == True):
			self.render('create-page', page_text0 = page_text0,  
				page_uri = page_uri, comments_checked=comments_checked, page_email = page_email, err_uri_not_available=err_uri_not_available, 
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
		pygl_page.email = page_email
		#pygl_page.title = page_title
		#pygl_page.text0 = page_text0
		#pygl_page.text1 = page_text1
		#pygl_page.text2 = page_text2
		pygl_page.comments_active = comments_active
		pygl_page.login_fails_consec = 0
		pygl_page.abuse_report_count = 0
		
		
		# save image id in page datastore entity
		#pygl_page.image_id0 = page_image_id0
		#pygl_page.image_id1 = page_image_id1
		#pygl_page.image_id2 = page_image_id2
		
		
		page_views = Pageviews(id=page_id)
		page_views.views = 0
		page_views.put()
		
		datastore_image = Pageimage()
		datastore_image.pygl_id = page_id


		''' Begin reCAPTCHA validation '''
		'''
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
				# write datastore
				pygl_page.put()
				# write file in bucket
				bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
				# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
				gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(page_id), 'w', content_type='text/html')
				gcs_file.write(b64encode(page_text0.encode('utf-8')))
				gcs_file.close()
				redirect_string = 'http://' + page_uri_val + '.py.gl'
				# redirect string must be str, no unicode
				self.redirect(str(redirect_string))
			else:
				logging.info("recaptche not successful: " + json.dumps(result))
				err_captcha = True
				self.render('create-page', page_text0 = page_text0, 
					page_uri = page_uri, comments_checked=comments_checked, page_email = page_email, err_uri_not_available=err_uri_not_available, 
					err_title=err_title, err_password_retype=err_password_retype, err_uri_invalid=err_uri_invalid, 
					err_passwort_format=err_passwort_format, err_captcha=err_captcha)
		else:
			err_captcha = True
			self.render('create-page', page_text0 = page_text0, 
				page_uri = page_uri, comments_checked=comments_checked, page_email = page_email, err_uri_not_available=err_uri_not_available, 
				err_title=err_title, err_password_retype=err_password_retype, err_uri_invalid=err_uri_invalid, 
				err_passwort_format=err_passwort_format, err_captcha=err_captcha)
		'''
 		''' End reCAPTCHA validation '''
		
    # write datastore
		pygl_page.put()
		# write file in bucket
		bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
		# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
		gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(page_id), 'w', content_type='text/html')
		gcs_file.write(b64encode(page_text0.encode('utf-8')))
		gcs_file.close()
		redirect_string = 'http://' + page_uri_val + '.py.gl/r/landing'

		if (page_email != "" and pt.validate_email(page_email)):
			# send mail
			mail.send_mail(sender="py.gl Website <noreply@pygl-page.appspotmail.com>", to=page_email, subject="Thank you for creating " + page_uri_val + ".py.gl", body="""
Thank you for creating a website with py.gl!


Your free website is now available at: """ + page_uri_val + """.py.gl

To edit your website visit """ +  page_uri_val + """.py.gl/edit and log in with your password.

You also find your website editor by selecting 'Edit page' at the bottom of your page.


Enjoy and share your free website!

The py.gl Team
			""")
		
		# redirect string must be str, no unicode
		#self.redirect(str(redirect_string))
		# display landing page
		self.render('landing', ['set', 'pyglpage', pt.make_cookie_hash(page_id)], page_uri=page_uri_val)
		
		
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
			
		# load from bucket
		bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
		# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
		gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(requested_id), 'r')
		page_text0 = b64decode(gcs_file.read()).decode('utf-8')
		gcs_file.close()

		
		#format text
		#page_text_formatted0 = re.sub(r"[a-zA-Z0-9_.+-/:?#@%&$=]+\.[a-zA-Z0-9_.+-/:?#@%&$=]+", pt.format_text_links, page.text0)
		#page_text_formatted0 = re.sub(r"\*\*(.*?)\*\*", pt.format_text_center, page_text_formatted0, flags=re.DOTALL)
		#page_text_formatted0 = re.sub(r"\*(.*?)\*", pt.format_text_bold, page_text_formatted0, flags=re.DOTALL)
		
		#page_text_formatted1 = re.sub(r"[a-zA-Z0-9_.+-/:?#@%&$=]+\.[a-zA-Z0-9_.+-/:?#@%&$=]+", pt.format_text_links, page.text1)
		#page_text_formatted1 = re.sub(r"\*\*(.*?)\*\*", pt.format_text_center, page_text_formatted1, flags=re.DOTALL)
		#page_text_formatted1 = re.sub(r"\*(.*?)\*", pt.format_text_bold, page_text_formatted1, flags=re.DOTALL)
		
		#page_text_formatted2 = re.sub(r"[a-zA-Z0-9_.+-/:?#@%&$=]+\.[a-zA-Z0-9_.+-/:?#@%&$=]+", pt.format_text_links, page.text2)
		#page_text_formatted2 = re.sub(r"\*\*(.*?)\*\*", pt.format_text_center, page_text_formatted2, flags=re.DOTALL)
		#page_text_formatted2 = re.sub(r"\*(.*?)\*", pt.format_text_bold, page_text_formatted2, flags=re.DOTALL)
		#
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
		cookie = None;
		if self.request.get('logout') == 'true':
			cookie = ['del', 'pyglpage', '']
		
		self.render('page', cookie, page_text0=page_text0, comments_active = page.comments_active, page_views=page_views.views, page_created = page.created.date(), page_last_edit = page.last_edit.date(), pygl_uri=page.pygl_uri)
		
		return
		
		
class PyglPageEdit(Handler):
	def get(self, requested_uri):
		err_wrong_password = False;
		err_password_locked = False;
		status_saved = False;
		
		requested_id = requested_uri.replace("-","").lower()
		
		cookiehash = self.request.cookies.get('pyglpage')
		if cookiehash and pt.check_cookie_hash(requested_id, cookiehash):
			key = ndb.Key(Pyglpage, requested_id)
			page = key.get()
			err_wrong_password = False;
			err_password_locked = False;
			status_saved = False;
			if page.comments_active:
				comments_checked = "checked"
			else:
				comments_checked = ""
				
			# load from bucket
			bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
			# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
			gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(requested_id), 'r')
			page_text0 = b64decode(gcs_file.read()).decode('utf-8')
			gcs_file.close()
			self.render('edit-page', ['set', 'pyglpage', pt.make_cookie_hash(requested_id)], page_text0=page_text0, page_uri=page.pygl_uri, comments_checked=comments_checked, page_email = page.email, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked, status_saved = status_saved)
			return
		
		self.render('checkpassword', page_uri=requested_uri, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked, status_saved=status_saved)
	
	def post(self, requested_uri):
	
		err_wrong_password = False;
		err_password_locked = False;
	
		password = self.request.get('password')
		
		# load page
		edit_id = requested_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, edit_id)
		page = key.get()
		
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return
			
		
		
		save_page = self.request.get('save_page')
		
		#page_title = self.request.get('page_title')
		page_text0 = self.request.get('page_text0')
		#page_text1 = self.request.get('page_text1')
		#page_text2 = self.request.get('page_text2')
		#page_image_id0 = self.request.get('image_id0')
		#page_image_id1 = self.request.get('image_id1')
		#page_image_id2 = self.request.get('image_id2')
		
		
		page_email = self.request.get('page_email')
		if self.request.get('comments_active'):
			comments_checked = "checked"
		else:
			comments_checked = ""
		
		if (page.login_fails_consec >= 5) and ((datetime.datetime.utcnow() - page.login_fail_last) < datetime.timedelta(minutes=10)):
			err_password_locked = True;
			status_saved = False;
			if (save_page == "True"):
				self.render('edit-page', page_text0=page_text0, page_uri=page.pygl_uri, comments_checked=comments_checked, page_email = page_email, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked, status_saved=status_saved)
			else:
				self.render('checkpassword', page_uri=requested_uri, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked)
			return
		
		cookiehash = self.request.cookies.get('pyglpage')
		
		if (cookiehash and pt.check_cookie_hash(edit_id, cookiehash)) or pt.valid_pw(edit_id, password, page.password_hash):
			page.login_fails_consec = 0		
			page.put()
		else:
			err_wrong_password = True;
			status_saved = False;
			if (save_page == "True"):
				self.render('edit-page', page_text0=page_text0, page_uri=page.pygl_uri, comments_checked=comments_checked, page_email = page_email, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked, status_saved=status_saved)
			else:
				self.render('checkpassword', page_uri=requested_uri, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked)
			page.login_fails_consec = page.login_fails_consec + 1
			page.login_fail_last = datetime.datetime.utcnow()			# remember last failed login datetime
			page.put()
			return
		
		
		if (save_page == "True"):
		
			''' Begin reCAPTCHA validation '''
			'''
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
				
					#page.title = page_title
					#page.text0 = page_text0
					#page.text1 = page_text1
					#page.text2 = page_text2
					#page.image_id0 = page_image_id0
					#page.image_id1 = page_image_id1
					#page.image_id2 = page_image_id2
					page.email = page_email
					if self.request.get('comments_active'):
						page.comments_active = True
					else:
						page.comments_active = False
					page.last_edit = datetime.datetime.utcnow()
					
					page.put()
					
					# write file in bucket
					bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
					# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
					gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(edit_id), 'w', content_type='text/html')
					gcs_file.write(b64encode(page_text0.encode('utf-8')))
					gcs_file.close()
					
					redirect_string = 'http://' + page.pygl_uri + '.py.gl'
					# redirect string must be str, no unicode
					self.redirect(str(redirect_string))
				else:
					self.response.out.write("check failed")
			else:
				self.response.out.write("please check the recaptcha")
			'''
			''' End reCAPTCHA validation '''
			
			page.email = page_email
			if self.request.get('comments_active'):
				page.comments_active = True
			else:
				page.comments_active = False
			page.last_edit = datetime.datetime.utcnow()
					
			page.put()
					
			# write file in bucket
			bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
			# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
			gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(edit_id), 'w', content_type='text/html')
			gcs_file.write(b64encode(page_text0.encode('utf-8')))
			gcs_file.close()
					
			redirect_string = 'http://' + page.pygl_uri + '.py.gl'
			# redirect string must be str, no unicode
			#self.redirect(str(redirect_string))
			err_wrong_password = False;
			err_password_locked = False;
			status_saved = True;
			self.render('edit-page', ['set', 'pyglpage', pt.make_cookie_hash(edit_id)], page_text0=page_text0, page_uri=page.pygl_uri, comments_checked=comments_checked, page_email = page.email, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked, status_saved = status_saved)
		
		else:
			if page.comments_active:
				comments_checked = "checked"
			else:
				comments_checked = ""
				
			# load from bucket
			bucket_name = os.environ.get('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())	
			# 'w': write (create or overwrite) 'r' (read), content_type (MIME type)
			gcs_file = gcs.open('/' + bucket_name + '/pages/' + str(edit_id), 'r')
			page_text0 = b64decode(gcs_file.read()).decode('utf-8')
			gcs_file.close()
				
			status_saved = False;
			self.render('edit-page', ['set', 'pyglpage', pt.make_cookie_hash(edit_id)], page_text0=page_text0, page_uri=page.pygl_uri, comments_checked=comments_checked, page_email = page.email, err_wrong_password=err_wrong_password, err_password_locked=err_password_locked, status_saved = status_saved)
		
class PyglReportAbuse(Handler):
	def get(self, requested_uri = ""):
	
		# set page_uri empty string, if abuse report is called without uri, display input field
		page_uri = ""
		
		# request coming from py.gl/r/report-page?q=...
		if (requested_uri == ""):
			requested_uri = self.request.get('q')
		
		if (requested_uri != ""):
			# load page
			report_id = requested_uri.replace("-","").lower()
			key = ndb.Key(Pyglpage, report_id)
			page = key.get()
			
			if not page:
				self.response.out.write("sorry, pygl-page does not exist")
				return
				
			page_uri=page.pygl_uri

		# display abuse report page
		self.render('report-abuse-page', page_uri=page_uri)
		
	def post(self, requested_uri = ""):
	
		# request coming from py.gl/r/report-page
		if (requested_uri == ""):
			requested_uri = self.request.get('page_uri')
	
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
				
				report_id = requested_uri.replace("-","").lower()
		
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
				self.render('report-page-sent', page_uri=requested_uri)
			else:
				self.response.out.write("check failed")
		else:
			self.response.out.write("please check the recaptcha")
			''' End reCAPTCHA validation '''
	
	
class PyglPageLanding(Handler):
	def get(self, requested_uri = ""):
			
		# display landing page
		self.render('landing', page_uri=requested_uri)
        
        
class PyglChangePassword(Handler):
	def get(self, requested_uri):
		
		err_wrong_password = False;
		err_password_locked = False;
		err_password_retype = False;
		err_passwort_format = False;
		
		if (requested_uri == ""):
			self.response.out.write("sorry, pygl-page does not exist")
			return
		
		# load page
		page_id = requested_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, page_id)
		page = key.get()
			
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return
			
		# display change password page
		self.render('changepassword', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password, err_password_retype=err_password_retype, err_passwort_format=err_passwort_format)
		
	def post(self, requested_uri):
		err_wrong_password = False;
		err_password_locked = False;
		err_password_retype = False;
		err_passwort_format = False;
		msg_password_changed = False;
		
		password = self.request.get('password')
		password_new = pt.validate_password(self.request.get('password_new'))
		password_new_retype = pt.validate_password(self.request.get('password_new_retype'))
		
		# load page
		page_id = requested_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, page_id)
		page = key.get()
		
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return
		
		if (page.login_fails_consec >= 5) and ((datetime.datetime.utcnow() - page.login_fail_last) < datetime.timedelta(minutes=10)):
			err_password_locked = True;
			self.render('changepassword', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password, err_password_retype=err_password_retype, err_passwort_format=err_passwort_format, msg_password_changed=msg_password_changed)
			return
		
		if pt.valid_pw(page_id, password, page.password_hash):
		# reset pw consec fail count
			page.login_fails_consec = 0	
			
			# check new password
			if (not password_new):
				err_passwort_format = True;
				self.render('changepassword', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password, err_password_retype=err_password_retype, err_passwort_format=err_passwort_format, msg_password_changed=msg_password_changed)
				page.put()
				return
			
			# check new password
			if password_new != password_new_retype:
				err_password_retype = True;
				self.render('changepassword', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password, err_password_retype=err_password_retype, err_passwort_format=err_passwort_format, msg_password_changed=msg_password_changed)
				page.put()
				return
				
			page.password_hash = pt.make_pw_hash(page_id, password_new)
			page.put()
		else:
			err_wrong_password = True;
			self.render('changepassword', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password, err_password_retype=err_password_retype, err_passwort_format=err_passwort_format, msg_password_changed=msg_password_changed)
			page.login_fails_consec = page.login_fails_consec + 1
			page.login_fail_last = datetime.datetime.utcnow()			# remember last failed login datetime
			page.put()
			return
		
		msg_password_changed = True;
		self.render('changepassword', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password, err_password_retype=err_password_retype, err_passwort_format=err_passwort_format, msg_password_changed=msg_password_changed)
		
  
  
class PyglPageDelete(Handler):
	def get(self, requested_uri):
	
		err_wrong_password = False;
		err_password_locked = False;
	
		if (requested_uri == ""):
			self.response.out.write("sorry, pygl-page does not exist")
			return
		

		# load page
		report_id = requested_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, report_id)
		page = key.get()
			
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return
			
		# display delete page
		self.render('delete-page', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password)
		
	def post(self, requested_uri):
	
		err_wrong_password = False;
		err_password_locked = False;
	
		password = self.request.get('password')
		
		# load page
		delete_id = requested_uri.replace("-","").lower()
		key = ndb.Key(Pyglpage, delete_id)
		page = key.get()
		
		if not page:
			self.response.out.write("sorry, pygl-page does not exist")
			return

		if (page.login_fails_consec >= 5) and ((datetime.datetime.utcnow() - page.login_fail_last) < datetime.timedelta(minutes=10)):
			err_password_locked = True;
			self.render('delete-page', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password)
			return
		
		if pt.valid_pw(delete_id, password, page.password_hash):
			page.login_fails_consec = 0		
			page.put()
		else:
			err_wrong_password = True;
			self.render('delete-page', page_uri=page.pygl_uri, err_password_locked=err_password_locked, err_wrong_password=err_wrong_password)
			page.login_fails_consec = page.login_fails_consec + 1
			page.login_fail_last = datetime.datetime.utcnow()			# remember last failed login datetime
			page.put()
			return


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
				
				# delete page
				key.delete()
				
				self.response.out.write(requested_uri + ".py.gl deleted")
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
		# set header to allow subdomain pages to access upload
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		# write out id
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
		
		
class PyglCheckUrl(Handler):
	def get(self):
		page_uri = self.request.get('q')
		
		if (page_uri == ""):
			self.response.out.write("empty")
			return
		
		page_uri = pt.validate_uri(page_uri)
		
		if (not page_uri):
			self.response.out.write("invalid")
			return
			
		# load page
		page_uri = page_uri.replace("-","").lower()
		
		key = ndb.Key(Pyglpage, page_uri)
		page = key.get()
		
		if page:
			self.response.out.write("used")
		else:
			self.response.out.write("free")


		
app = webapp2.WSGIApplication([
    routes.DomainRoute('www.py.gl', [
    webapp2.Route(r'/', handler=MainPage)
    ]),
    routes.DomainRoute('<requested_uri>.py.gl', [
    webapp2.Route(r'/edit', handler=PyglPageEdit),
    webapp2.Route(r'/r/edit', handler=PyglPageEdit),
    webapp2.Route(r'/r/changepassword', handler=PyglChangePassword),
    webapp2.Route(r'/r/landing', handler=PyglPageLanding),
    webapp2.Route(r'/r/report-page', handler=PyglReportAbuse),
    webapp2.Route(r'/r/delete', handler=PyglPageDelete),
    webapp2.Route(r'/', handler=PyglPage)
    ]),
    routes.DomainRoute('www.<requested_uri>.py.gl', [
    webapp2.Route(r'/edit', handler=PyglPageEdit),
    webapp2.Route(r'/r/edit', handler=PyglPageEdit),
    webapp2.Route(r'/r/changepassword', handler=PyglChangePassword),
    webapp2.Route(r'/r/landing', handler=PyglPageLanding),
    webapp2.Route(r'/r/report-page', handler=PyglReportAbuse),
    webapp2.Route(r'/r/delete', handler=PyglPageDelete),
    webapp2.Route(r'/', handler=PyglPage)
    ]),
    webapp2.Route(r'/r/image', handler=GetImage),
    webapp2.Route(r'/r/upload', handler=UploadImage),
    webapp2.Route(r'/r/report-page', handler=PyglReportAbuse),
    webapp2.Route(r'/r/check-url', handler=PyglCheckUrl),
    webapp2.Route(r'/<requested_uri>', handler=PyglPage),
    webapp2.Route(r'/', handler=MainPage),
], debug=True)





