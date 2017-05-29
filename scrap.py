import json
import smtplib
import urllib2
import hashlib
import requests
from params import *
import bs4 as BeautifulSoup
from firebase import firebase
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart

GLOBALS = Globals()


def parseInt(string):
    return int(''.join([x for x in string if x.isdigit()]))


class Scrapper:

    def __init__(self):

        self._filters = {}
        self._filters['ventes_immobilieres'] = {'house': 'ret=1'}
        self.firebase_client = firebase.FirebaseApplication(
            GLOBALS.firebaseAppUrl, None)

    def createMailBody(self, title, price, url):
        return "Alert leboncoin : " + title + " " + str(price) + " euros : " + url

    # Send a mail when there is a match
    def sendMail(self, title, price, url, recipients):

        fromaddr = GLOBALS.smtpServerLogin
        toaddr = GLOBALS.smtpServerRecipient

        # edit the message
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = title

        body = self.createMailBody(title, price, url)

        msg.attach(MIMEText(body.encode('utf-8'), 'plain'))

        # Init the smtp server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(fromaddr, GLOBALS.smtpServerPasswd)

        # Send mail to recipients
        for email in recipients:
            server.sendmail(fromaddr, email, msg.as_string())

        if len(recipients) < 1:
            server.sendmail(fromaddr, toaddr, msg.as_string())

        # quit smtp server
        server.quit()

    # Send an sms
    def sendSms(self, msg):
        msg = msg.split(' ')
        msg = "+".join(msg)
        urllib2.urlopen(GLOBALS.freeMobileApi + msg.encode('utf-8'))

    def create_hash(self, url):
        return hashlib.sha1(url).hexdigest()

    # Save a new match
    def persist(self, item_type, url, item):
        url_hash = self.create_hash(url)
        patch_url = '/{type}/{hash}'.format(type=item_type, hash=url_hash)
        result = self.firebase_client.patch(patch_url, item)

    # Check if an item already exists
    def checkIfExists(self, _url, _name):
        url_hash = self.create_hash(_url)
        item_url = '/{type}/{hash}'.format(type=_name, hash=url_hash)
        return self.firebase_client.get(item_url, None)

    def scrap(self, priceLimit, region=None, recipients=[], args=[], sms=True, category=None, cities=[], match_all=False, filters=None):
        # Craft the url
        cat = category
        region = (region + '/' if region is not None else '')
        category = (category + '/' if category is not None else 'annonces/')

        leboncoinUrl = 'https://www.leboncoin.fr/' + category + \
            'offres/ile_de_france/' + region + '?f=a&th=1&q='

        url = leboncoinUrl + "+".join(args) + "&location=" + ",".join(cities)

        if filters is not None:
            url += "&" + "".join(self._filters[cat][f] for f in filters)

        resp = requests.get(url)

        html = resp.text.encode('utf-8')

        soup = BeautifulSoup.BeautifulSoup(html, "html.parser")
        results = soup.find('section', attrs={"class": u"tabsContent"})

        if (results is not None):

            results = results.findAll('a')
            i = 0
            # Iterating the html parsing result
            while (i < len(results)):

                # Get the item title
                title = results[i]['title']

                # Get the item price
                div = results[i].find('h3', attrs={"class": u"item_price"})

                # Get the url
                url = results[i]['href']

                if (hasattr(div, 'string')):
                    price = parseInt(div.string.strip())
                    lowerCaseTitle = title.lower()
                    if (price <= priceLimit and (match_all == True or all(param in lowerCaseTitle for param in args))):
                        # This is a match

                        if (self.checkIfExists(url, args[0]) is None):
                            # The item is not present in the db so it's a new
                            # one

                            # save the item
                            self.persist(
                                args[0],
                                url,
                                {'title': title, 'price': price, 'url': url})

                            # Send a notification
                            self.sendMail(title, price, url, recipients)

                            # Send sms
                            if sms and hasattr(GLOBALS, 'freeMobileApi'):
                                message = self.createMailBody(
                                    title, price, url)
                                self.sendSms(message)
                i += 1
