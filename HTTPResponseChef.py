from argparse import ArgumentParser
from array import array
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import re
from urllib.parse import urlparse

class RecipeMeta(object):
	def __init__(self, parent_path: str):
		self.parentPath = parent_path

class MatchAndReplaceRule(object):
	def __init__(self, request_match_regex: str, response_replacement_regex: str, replace_value: str):
		self.request_match_regex = request_match_regex
		self.response_replacement_regex = response_replacement_regex
		self.replace_value = replace_value

class RecipeOptions(object):
	def __init__(self, auto_content_length: bool, match_and_replace_rules: array):
		self.auto_content_length = auto_content_length
		self.match_and_replace_rules = [MatchAndReplaceRule(**x) for x in match_and_replace_rules]

class RecipeBody(object):
	def __init__(self, body_string: str, body_relative_file_path: str, sp_body_absolute_file_path: str):
		self._body_string = body_string
		self._body_relative_file_path = body_relative_file_path
		self._sp_body_absolute_file_path = sp_body_absolute_file_path

	def get_body(self) -> bytes:
		if self._sp_body_absolute_file_path:
			with open(self._sp_body_absolute_file_path, 'rb') as file:
				return file.read()
		return self._body_string.encode('utf-8')		

class Recipe(object):
	def __init__(self, version: str, code: int, reason: str, headers: object, body: dict, options: dict):
		self.version = version
		self.code = code
		self.reason = reason
		self.headers = headers
		self.body = RecipeBody(**body)
		self.options = RecipeOptions(**options)

class RecipeFile(object):
	def __init__(self, meta: dict, recipe: dict):
		self.meta = meta
		self.recipe = recipe

def load_recipe(recipe_path: str) -> Recipe:
	recipe_dict = {}
	file_path = recipe_path
	current_directory, parent_path = os.path.split(file_path)
	while parent_path:
		file_path = os.path.join(current_directory, parent_path)
		current_directory = os.path.dirname(file_path)
		with open(file_path, 'rb') as file:
			recipe_config = RecipeFile(**json.loads(file.read()))

			# Capture absolute path to body file based on current directory
			body_relative_file_path = recipe_config.recipe['body']['body_relative_file_path']
			if body_relative_file_path:
				recipe_config.recipe['body']['sp_body_absolute_file_path'] = os.path.join(current_directory, body_relative_file_path)
			else:
				recipe_config.recipe['body']['sp_body_absolute_file_path'] = None

			recipe_dict = recipe_config.recipe | recipe_dict
			parent_path = recipe_config.meta["parent_path"]
	return Recipe(**recipe_dict)

# Only inheriting SimpleHTTPRequestHandler instead of BaseHTTPRequestHandler
# so I can borrow some useful methods like translate_path
class CustomSimpleHTTPRequestHandler(SimpleHTTPRequestHandler):

	def __init__(self, req, client_addr, server):
		SimpleHTTPRequestHandler.__init__(self, req, client_addr, server)
		
	def do_GET(self):	
		self._handle_request('GET')

	def do_POST(self):
		self._handle_request('POST')

	def do_PUT(self):
		self._handle_request('PUT')

	def do_PATCH(self):
		self._handle_request('PATCH')

	def do_DELETE(self):
		self._handle_request('DELETE')

	def do_HEAD(self):
		self._handle_request('HEAD')

	def _handle_request(self, http_method):
		request_body = b''
		if 'Transfer-Encoding' in self.headers and self.headers['Transfer-Encoding'] == 'chunked':
			chunk_size = None
			while chunk_size != 0:
				chunk_size = int(self.rfile.readline(), 16)
				request_body += self.rfile.read(chunk_size)
				self.rfile.readline() # Read passed the next \r\n
		elif 'Content-Length' in self.headers:
			content_length = int(self.headers['Content-Length'])
			request_body = self.rfile.read(content_length)

		full_request = f"{http_method} {str(self.path)} {self.request_version}\n{str(self.headers)}{request_body.decode('utf-8')}"
		
		response_config = load_recipe(self.translate_path(self.path))

		self.protocol_version = response_config.version
		self.send_response_only(response_config.code, response_config.reason)

		response_body = response_config.body.get_body()

		for match_and_replace_rule in response_config.options.match_and_replace_rules:
			request_match = re.search(match_and_replace_rule.request_match_regex, full_request)
			if request_match:
				response_body = re.sub(bytes(match_and_replace_rule.response_replacement_regex, 'utf-8'), bytes(match_and_replace_rule.replace_value, 'utf-8'), response_body)

		headers = response_config.headers
		if response_config.options.auto_content_length:
			headers['Content-Length'] = len(response_body)

		for headerName, headerValue in headers.items():
			self.send_header(headerName, headerValue)

		self.end_headers()
		self.wfile.write(response_body)

parser = ArgumentParser(description='A super light, highly customizable HTTP Server in a single python script')
parser.add_argument('--addr', dest='address', type=str, help='Local HTTP Server IP Address', default='0.0.0.0')
parser.add_argument('--port', dest='port', type=int, help='Local HTTP Server Port', default=8888)
parser.add_argument('--dir', dest='directory', type=str, help='Local Web Server Directory')
parser.add_argument('--def', dest='default_config_path', type=str, help='Default Response Config Path', default='examples/example')

args = parser.parse_args()

server_address = (args.address, args.port)
local_web_directory = args.directory
if not local_web_directory:
	local_web_directory = os.getcwd()
else:
	os.chdir(local_web_directory)
setattr(CustomSimpleHTTPRequestHandler, 'web_directory', local_web_directory)
setattr(CustomSimpleHTTPRequestHandler, 'default_config_path', args.default_config_path)
with ThreadingHTTPServer(server_address, CustomSimpleHTTPRequestHandler) as httpd:
	logging.basicConfig(level=logging.DEBUG)
	logging.info('Running server at %s:%d...', args.address, args.port)
	httpd.serve_forever()