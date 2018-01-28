
#(SAFE)Quake: 310 Final Project
# Riti Gupta & Sharon Heung
# url: https://safequakedirectory.appspot.com
# Twilio phone number: 1 (334) 339-7233

# For context, the Earthquake Catalog API, by USGS, allows custom searches for earthquake information using
# a wide array of parameters. The Twilio API allows us to recieve texts and process that data adding a person to our
# directory. For the scope of this project we assume that the user will text our Twilio pone number in the right "first name last name, age"
# format. We use Google App Engine to display the directory and make it interactive.

import webapp2, urllib, urllib2, webbrowser, json
import jinja2
from google.appengine.api import urlfetch
import logging
from HTMLParser import HTMLParser

import os
from twilio.twiml.messaging_response import Message, MessagingResponse

from google.appengine.ext import db

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                                       extensions=['jinja2.ext.autoescape'],
                                       autoescape=True)

# used to decode
JINJA_ENVIRONMENT.filters['jsondumps'] = json.dumps

class Survivor(db.Model):
    name = db.StringProperty()
    age = db.StringProperty()
    country = db.StringProperty()

class MainHandler(webapp2.RequestHandler):
    def get(self):
        logging.info("In MainHandler")
        template_values = {}
        template_values['page_title'] = "(SAFE)Quake"
        template_values['scaryearthquakes'] = getQuakesByLoc()
        template = JINJA_ENVIRONMENT.get_template('greetform.html')
        self.response.write(template.render(template_values))

def pretty(obj):
    return json.dumps(obj, sort_keys=True, indent=2)

def earthquakeREST(method, format="geojson", params={}):
    baseurl = "https://earthquake.usgs.gov/fdsnws/event/1/"
    params['format'] = format
    url = baseurl + method + "?" + urllib.urlencode(params)
    try:
        response = urlfetch.fetch(url)
        data = json.loads(response.content)
        return data
    except urlfetch.Error:
        logging.exception('Caught exception fetching url')
        return None

# returns earthquakes of specific magnitude and alert-level that would possibly need a directory
def getQuakesByLoc(method = "query", minmag = '5.4', orderby = 'magnitude', params = {}):
    datadict = earthquakeREST(method,params = {'minmag':minmag, 'orderby':orderby})
    datadict = datadict["features"]
    earthquakes = []
    for quake in datadict:
        if ((quake['properties']['alert'] != "green") and (quake['properties']['alert'] != "None")):
            earthquakes.append(quake)
    return earthquakes

class GreetResponseHandlr(webapp2.RequestHandler):
    def post(self):
        latlng = self.request.headers.get("X-AppEngine-CityLatLong", None)
        vals = {}
        vals['page_title'] = "(SAFE)Quake"

        ## get rid of HTML encoding that JINJA is doing before converting back to JSON -sm
        h = HTMLParser()
        jsonquakestring = h.unescape(self.request.get("quake"))
        logging.info(jsonquakestring)
        earthquake = json.loads(jsonquakestring)
        vals['quake'] = earthquake

        q = db.Query(Survivor)
        survivors = []
        for survivor in q.run():
            survivors.append(survivor)
        vals['survivors'] = survivors

        template = JINJA_ENVIRONMENT.get_template('greetresponse.html')
        self.response.write(template.render(vals))

# This class serves as a webhook for Twilio.
# Handles the incoming text message to our Twilio phone number and responses
class smsReceiverHandler(webapp2.RequestHandler):

    def post(self):
        message_body = self.request.get('Body')
        # accessing datastore entities
        mySurvivor = Survivor()

        # once we get the search function going, we will use this age variable to filter out individuals
        index = message_body.find(",")
        index2 = message_body.find("(")
        name = message_body[:index]
        age = message_body[index+1:index2]
        country = message_body[message_body.find("(")+1:message_body.find(")")]
        mySurvivor.name = name
        mySurvivor.age = age
        mySurvivor.country = country
        mySurvivor.put()
        resp = MessagingResponse()
        str = "You have marked %s as safe in %s.\n-(SAFE)Quake"%(name, country)
        resp.message(str)
        self.response.write(resp)

application = webapp2.WSGIApplication([ \
    ('/gresponse', GreetResponseHandlr),
    ('/smsReceived', smsReceiverHandler),
    ('/.*', MainHandler)
],
    debug=True)