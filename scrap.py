# -*- coding: utf-8 -*-

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
from email_template import template

GLOBALS = Globals()


def parseInt(string):
    return int(''.join([x for x in string if x.isdigit()]))


class Scrapper:

    def __init__(self):
        self.firebase_client = firebase.FirebaseApplication(
            GLOBALS.firebaseAppUrl, None)
        self.default_img_url = "https://am21.akamaized.net/tms/cnt/uploads/2016/03/Grumpy-Cat.jpg"
        self._baseUrl = "https://www.leboncoin.fr/{category}/offres/{region}?f=a&th=1&q="
        self._filters = {
            "min_year": "rs",
            "max_year": "re",
            "cm3": "ccs"
        }

    def createSmsBody(self, title, price, url):
        return "Alert leboncoin : " + title + " " + str(price) + " euros : " + url

    def createMailBody(self, title, price, url, img):
        return template.format(
            title=title.encode('utf-8'),
            price=str(price).encode('utf-8'),
            url=url.encode('utf-8'),
            img=img.encode('utf-8'))

    # Send a mail when there is a match
    def sendMail(self, title, price, url, recipients, img):

        fromaddr = GLOBALS.smtpServerLogin
        toaddr = GLOBALS.smtpServerRecipient

        # edit the message
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        msg['Subject'] = title

        body = self.createMailBody(title, price, url, img)

        msg.attach(MIMEText(body, 'html', 'utf-8'))

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

    def getResults(self, url):
        resp = requests.get(url)
        html = resp.text.encode('utf-8')
        soup = BeautifulSoup.BeautifulSoup(html, "html.parser")
        return soup.find('section', attrs={"class": u"tabsContent"})

    # check real filter name in the filter map
    # then creaft filter in the form filter=value
    def craftFilter(self, expression):
        name, value = expression.split('=')
        return "{name}={value}".format(name=self._filters[name], value=value)

    def scrap(self, priceLimit, region='ile_de_france', category='annonces', args=[], filters=[], cities=[], match_all=False, recipients=[], sms=True):

        # Craft the url
        leboncoinUrl = self._baseUrl.format(category=category, region=region)

        url = leboncoinUrl + "+".join(args) + "&location=" + ",".join(cities)

        url += "&" + "".join(self.craftFilter(f) for f in filters)

        # get items
        results = self.getResults(url)

        if (results is not None):

            results = results.findAll('a')
            # Iterating the html parsing result
            for i in xrange(0, len(results)):

                # Get the item title
                title = results[i]['title']

                # Get the item price
                try:
                    price_text = results[i].find('h3', attrs={"class": u"item_price"}).text.strip()
                    price = parseInt(price_text)
                except:
                    price = 0

                # Get the url
                url = "https:" + results[i]['href']

                # Get image
                img = self.default_img_url
                try:
                    img = "http:" + results[i].find(
                                'span',
                                attrs={"class": "lazyload"})['data-imgsrc']
                except:
                    pass

                lowerCaseTitle = title.lower()
                if (price <= int(priceLimit) and (match_all == True or all(param in lowerCaseTitle for param in args))):
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
                        self.sendMail(title, price, url, recipients, img)

                        # Send sms
                        if sms and hasattr(GLOBALS, 'freeMobileApi'):
                            message = self.createSmsBody(
                                title, price, url)
                            self.sendSms(message)
