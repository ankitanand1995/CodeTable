from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect	
from .languages import lang, lang_to_ext
import requests
import json
import string
import random
from datetime import datetime
from django.core.signing import Signer
from .models import Code, Session
from django.shortcuts import redirect

# Note : Cross-check for the randomly generated string that it's not already used

RUN_URL = u'https://api.hackerearth.com/v3/code/run/'
COMPILE_URL = u'https://api.hackerearth.com/v3/code/compile/'
CLIENT_SECRET = '9b6d81acf7b7c1d91d0dddbdbe1cb6de1c7bc7fe'


'''
=> Index function is matched with the CodeTable_app url.
=> It generates a 10 digit unique key which is also the id of the code. Then it redirets user to that detail page.
=> It also checks whether theuser has any cookie or not. If the user has cookies, it adds that to session. Else it saves 
   a new cookie to the dataase.
'''
def index(request):
	N = 10
	file_name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))
	file_url = '/CodeTable_app/' + file_name + '/'
	signer = Signer()
	value = signer.sign(file_name)
	# print 'Result : ', value, file_name

	response = HttpResponseRedirect(file_url)

	c = Code(code_id = file_name, last_edited = datetime.now(), code_actual = "")
	c.save()

	if 'key' in request.COOKIES:
		key = request.COOKIES.get('key')
		# print 'yay'

	else:
		key =''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(20))
		response.set_cookie('key', key)
		# print 'no'

	allowed_key = [key]
	session = Session(code_id = file_name)
	session.setlist(allowed_key)
	session.save()

	return response

'''
=> Invoked when fork button is pressed by the user.
=> Does the same work of index(). Just that it initilises the new code generated with the exisiting source code.
=> Increases the clone_count by one each time function is called..
'''

def clone(request):
	key = request.COOKIES.get('key')
	source = request.GET['code']
	file_id = request.GET['code_id']
	# print source
	file_name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))
	
	# Updating exisiting code
	code = Code.objects.get(code_id = file_id)
	code.clone_count = code.clone_count + 1
	code.save()

	# Making New Code DB
	code = Code()
	code.code_actual = source
	code.code_id = file_name
	# code.clone_count = code.clone_count + 1
	code.save()

	#Updating Session Db
	session = Session(code_id = file_name)
	allowed_key = [key]
	session.setlist(allowed_key)
	session.save()
	return HttpResponse(file_name)


'''
=> Only function which renders a html web page.
=> Receives the code_id. Fetches detail from the database. Sends all the detail to html using context as json.
=> Checks for user authorization also.
'''
def detail(request, file_id):
	lang['code_id'] = file_id
	code = Code.objects.get(code_id = file_id)
	source = code.code_actual
	last_change = str(code.last_edited)
	run_count = code.run_count
	user_name = code.user_name
	clone_count = code.clone_count
	ret = [source, last_change, run_count, user_name, clone_count]
	def_lang = code.code_lang

	if 'key' not in request.COOKIES:
		lang['Info']['auth'] = False
		lang['Info']['code_id'] = file_id

	else:
		key = request.COOKIES['key']
		session = Session.objects.get(code_id = file_id)
		allowed_keys = json.loads(session.allowed_list)

		if key in allowed_keys:
			lang['Info']['auth'] = True

		else:
			lang['Info']['auth'] = False

	# lang['def_lang'] = lang_to_ext[def_lang]
	lang['Info']['extra'] = ret
	lang['def_lang'] = def_lang
	context = {'language': lang}

	return render(request, 'CodeTable_app/index.html', {"obj_as_json": json.dumps(lang)})



'''
=> This function is invoked when user calls a webpagewith id of 30 letters.
=> Parses the url received. Checks whether the user is authorized or not. Accordingly redirects to the 
   detail view with Code - Id.
=> If user is authorized to edit the code, session needs to be updated also.
'''
def auth(request, auth_id):
	code_id = auth_id[0:10]
	key = auth_id[10:]
	# print code_id, auth_id
	r_url = '/CodeTable_app/' + code_id + '/'

	response = HttpResponseRedirect(r_url)

	session = Session.objects.get(code_id = code_id)
	allowed_keys = json.loads(session.allowed_list)
	# print "X - ", allowed_keys, key

	# 	# if key not in allowed_key.getlist():
	if key in allowed_keys:
		# .. To append that List. With Originial key
		# Redirect.
		# s_key = request.COOKIES['key']

		if 'key' in request.COOKIES:
			s_key = request.COOKIES.get('key')
			# print 'yay'

		else:
			s_key =''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(20))
			response.set_cookie('key', key)
			# print 'no'

		if s_key not in allowed_keys:
			allowed_keys.append(s_key)
			session.setlist(allowed_keys)
			session.save()	
	else:
		# print "Unauthorize access"
		lang['Info']['auth'] = False

	return response


'''
=> Invoked when Run Button in pressed.
=> Receives the code_id, code, language from web page. Sends all the data to hackerearth server. Receives 
   the output. Sends the output back to web page as AJAX request return. Formaat of return = JSON
'''
def runCode(request):
	source = request.GET['code']
	lang = request.GET['lang']
	inputt = request.GET['input']
	code_id = request.GET['code_id']

	code = Code.objects.get(code_id = code_id)
	code.run_count = code.run_count + 1
	code.save()
	data = {
	    'client_secret': CLIENT_SECRET,
	    'async': 0,
	    'source': source,
	    'lang': lang,
	    'time_limit': 5,
	    'memory_limit': 262144,
	    'input' : inputt,
	}
	r = requests.post(RUN_URL, data=data)
	# print r.json()
	return HttpResponse(json.dumps(r.json()), content_type="application/json")


'''
=> Invoked when Compile Button in pressed.
=> Receives the code_id, code, language from web page. Sends all the data to hackerearth server. Receives 
   the output. Sends the output back to web page as AJAX request return. Formaat of return = JSON
'''
def compileCode(request):
	source = request.GET['code']
	lang = request.GET['lang']

	data = {
	    'client_secret': CLIENT_SECRET,
	    'async': 0,
	    'source': source,
	    'lang': lang,
	    'time_limit': 5,
	    'memory_limit': 262144,
	}

	r = requests.post(COMPILE_URL, data=data)
	# print r.json()
	return HttpResponse(json.dumps(r.json()), content_type="application/json")


'''
=> Invoked when Save Button in pressed.
=> Receives the code_id, code, language from web page. Updates all the data to database. 
   In return sends back the current time of updatation.
'''
def saveCode(request):
	source = request.GET.get('code', '') 
	code_id = request.GET.get('code_id', '') 
	code_lang = request.GET.get('lang', '') 
	print 'Source :- ', source, code_id, code_lang

	code = Code.objects.get(code_id = code_id)
	code.code_actual = source
	code.last_edited = datetime.now()
	code.code_lang  = code_lang
	code.save()
	return HttpResponse(datetime.now())


'''
=> Invoked when Update Name Button in pressed.
=> Receives the code_id, code_name from web page. Updates all the data to database. 
   In return sends back None.
'''
def update_name(request):
	code_id = request.GET.get('code_id', '') 
	user_name = request.GET.get('name', '')
	# print "Hello World \n", user_name
	code = Code.objects.get(code_id = code_id)
	code.user_name = user_name
	code.save()
	return HttpResponse()


'''
=> Invoked when delete code in pressed.
=> Receives the code_id. Deletes the record of that code_id from the database. The user is 
   redirected to a new page.
'''
def delete(request):
	code_id = request.GET.get('code_id', '') 

	code = Code.objects.get(code_id = code_id)
	session = Session.objects.get(code_id = code_id)
	code.delete()
	session.delete()
	return HttpResponse()

