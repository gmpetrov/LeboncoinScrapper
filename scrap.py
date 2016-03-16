from params import *
import bs4 as BeautifulSoup
# import re
import smtplib
from firebase import firebase
import json
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import requests
import urllib2

GLOBALS = Globals();

def parseInt(string):
    return int(''.join([x for x in string if x.isdigit()]))

class Scrapper:

    def createMailBody(self, title, price, url):
        return "Alert leboncoin : " + title + " " + str(price) + " euros : " + url;

    # Send a mail when there is a match
    def sendMail(self, title, price, url):

        fromaddr = GLOBALS.smtpServerLogin;
        toaddr   = GLOBALS.smtpServerRecipient;

        # Sepcial Susanne
        if ("thinkpad" in title.lower()):
            toaddr = "susanne.thierfelder@gmail.com";

        # edit the message
        msg = MIMEMultipart();
        msg['From'] = fromaddr;
        msg['To'] = toaddr;
        msg['Subject'] = title;

        body = self.createMailBody(title, price, url)

        msg.attach(MIMEText(body.encode('utf-8'), 'plain'));

        # Init the smtp server
        server = smtplib.SMTP('smtp.gmail.com', 587);
        server.starttls()
        server.login(fromaddr, GLOBALS.smtpServerPasswd)

        # Send the mail
        server.sendmail(fromaddr, toaddr, msg.as_string())

        # quit smtp server
        server.quit()


    # Send an sms
    def sendSms(self, msg):
        msg = msg.split(' ');
        msg = "+".join(msg);
        urllib2.urlopen(GLOBALS.freeMobileApi + msg.encode('utf-8'));

    # Save a new match
    def persist(self, url, item):
        app = firebase.FirebaseApplication(GLOBALS.firebaseAppUrl, None)
        result = app.post('/' + str(url), item);

    # Get all the saved match
    def getHistoryOf(self, name):
        app = firebase.FirebaseApplication(GLOBALS.firebaseAppUrl, None)
        results = app.get('/' + str(name), None);
        data = json.dumps(results);
        return json.loads(data);

    # Check if an item already exists
    def checkIfExists(self, _url, _name):
        data = self.getHistoryOf(_name);
        if (data != None):
            for key in data :
                url = data[key]['url'];
                if (_url == url):
                    return True;
        return False;

    def scrap(self, priceLimit, *arg):

        # Craft the url
        leboncoinUrl = 'http://www.leboncoin.fr/annonces/offres/ile_de_france/?f=a&th=1&q=';
        url = leboncoinUrl + "+".join(arg);

        # Parse html
        #html = urlopen(url).read()

        resp = requests.get(url);

        html = resp.text.encode('utf-8')

        soup = BeautifulSoup.BeautifulSoup(html, "html.parser")
        results = soup.find('ul',attrs={"class":u"tabsContent"});

        if (results is not None):

            results = results.findAll('a');
            i = 0;
            # Iterating the html parsing result
            while (i < len(results)):

                # Get the item title
                title = results[i]['title'];

                # Get the item price
                div = results[i].find('h3',attrs={"class":u"item_price"});

                # Get the url
                url = results[i]['href'];

                if (hasattr(div, 'string')):
                    price = parseInt(div.string.strip());
                    lowerCaseTitle = title.lower();
                    if (price <= priceLimit and all(param in lowerCaseTitle for param in arg)):
                        # This is a match

                        if (self.checkIfExists(url, arg[0]) == False):
                            # The item is not present in the db so it's a new one

                            # save the item
                            self.persist(arg[0], { 'title' : title, 'price' : price, 'url' : url });

                            # Send a notification
                            self.sendMail(title, price, url)

                            # Send sms
                            if hasattr(GLOBALS, 'freeMobileApi'):
                                message = self.createMailBody(title, price, url)
                                self.sendSms(message);
                i += 1;

