import webbrowser
import threading

import requests
import json
from time import sleep

from http.server import BaseHTTPRequestHandler, HTTPServer
import time

serverPort = 80
webServer = None

client_id = "82jp16pdf8ksb9wvvp14cilktjcp9p"
client_secret = "dmnk4xymgjucdiv2axdz9qfm07kv2d"
scopes = "channel:edit:commercial user:read:email"
accessToken = None
refreshToken = None
username = None

def askUsername():
	name = input("Your twitch name: ")
	if(name):
		return name
	return askUsername()

def getAccessToken(code):
	url = "https://id.twitch.tv/oauth2/token"
	url += "?client_id=" + client_id
	url += "&client_secret=" + client_secret
	url += "&code=" + code
	url += "&grant_type=authorization_code"
	url += "&redirect_uri=http://localhost"
	re = requests.post(url)
	if(re.status_code != 200):
		return None
	return json.loads(re.text)

def redirect():
	auth_url = "https://id.twitch.tv/oauth2/authorize"
	auth_url += "?client_id=" + client_id
	auth_url += "&redirect_uri=http://localhost"
	auth_url += "&response_type=code"
	auth_url += "&scope="  + scopes
	webbrowser.open(auth_url)

def refresh():
	global refreshToken
	global accessToken
	url = "https://id.twitch.tv/oauth2/token"
	url += "?grant_type=refresh_token"
	url += "&refresh_token=" + refreshToken
	url += "&client_id=" + client_id
	url += "&client_secret=" + client_secret
	re = requests.post(url)
	if(re.status_code == 200):
		j = json.loads(re.text)
		accessToken = j["access_token"]
		refreshToken = j["refresh_token"]
		print("Tokens refreshed")
		print("Token: " + accessToken)
	else:
		print()
		print(re.text)
		print("Refreshing failed")
		print()

def req(method, url, body = {}, retried = False):
	global accessToken
	if(method == "get"):
		re = requests.get(url, headers={
			"Client-ID": client_id,
			"Authorization": "Bearer " + accessToken
		}, data=body)
	elif(method == "post"):
		re = requests.post(url, headers={
			"Client-ID": client_id,
			"Authorization": "Bearer " + accessToken
		}, data=body)

	if(re.status_code == 401 and retried == False):
		refresh()
		return req(method, url, body, True)
	return re

def getUser():
	re = req("get", "https://api.twitch.tv/helix/users?login=" + username)
	if(re.status_code == 200):
		return json.loads(re.text)["data"][0]
	else:
		return None

def askTime():
	exec_time = input("Minutes between ads: ")
	if(not exec_time):
		return askTime()

	try:
		exec_time = float(exec_time)
	except:
		print("Invalid time")
		return askTime()

	return exec_time

def showAd(broadcaster_id):
	re = req("post", "https://api.twitch.tv/helix/channels/commercial", {
		"broadcaster_id": broadcaster_id,
		"length": 30
	})
	if(re.status_code == 200):
		j = json.loads(re.text)
		print()
		print("New advertisement triggered. length: " + str(j["length"]) + "seconds")
		print("Another advertisement executable after " + str(j["retryAfter"] / 60) + " minutes")
	else:
		print()
		print("Executing advertisement failed")
		print(re.text)

def startChedule():
	webServer.server_close() #Server not needed anymore

	user = getUser()
	if(user == None):
		print("Couldn't retrieve user '" + username + "'")
		return

	displayName = user["display_name"]
	broadcaster_id = user["id"]
	print()
	print("Welcome " + displayName)
	print()

	minutes = askTime()
	if(minutes < 1):
		minutes = 1
		
	seconds = minutes * 60
	print("Timer started. Time: " + str(minutes) + " minutes")
	try:
		while True:
			sleep(seconds)
			showAd(broadcaster_id)
	except KeyboardInterrupt:
		pass

class Server(BaseHTTPRequestHandler):
	def do_GET(self):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		path = self.path
		if("?code=" in path):
			code = path.split("code=")[1].split("&")[0]
			global accessToken
			global refreshToken
			if(accessToken == None and code):
				tokens = getAccessToken(code)
				if(tokens == None):
					print("Requesting access token failed")
					return
				accessToken = tokens["access_token"]
				refreshToken = tokens["refresh_token"]

				print("Twitch authentication completed")
				self.wfile.write("Twitch authentication completed. Close this windows and get back to the console.".encode())
				threading.Thread(target=startChedule).start()
			else:
				self.wfile.write("Twitch authentication failed. We will try again. You can close this window.".encode())
				print("getting authentication code failed. retrying")
		else:
			self.wfile.write("For some reason twitch didn't provide the authentication we needed. Contact the author.".encode())

		self.wfile.write('<script>window.close();</script>'.encode())
	def log_message(self, format, *args):
		return

def run():
	print("Copyright, Toni.I")
	print()
	global username
	username = askUsername()
	global webServer
	webServer = HTTPServer(("localhost", 80), Server)
	redirect()
	try:
		webServer.serve_forever()
	except:
		pass

	webServer.server_close()

if __name__ == "__main__":
	run()
