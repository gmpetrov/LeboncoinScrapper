from params import *
from urllib2 import urlopen
import bs4 as BeautifulSoup
import re
import smtplib
from firebase import firebase
import json
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

GLOBALS = Globals();

# Send a mail when there is a match
def sendMail(title, price, url):

    fromaddr = GLOBALS.smtpServerLogin;
    toaddr   = GLOBALS.smtpServerRecipient;

    # edit the message
    msg = MIMEMultipart();
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = title;

    body = "Alert leboncoin : " + title + " " + str(price) + " euros : " + url;
    msg.attach(MIMEText(body, 'plain'))

    # Init the smtp server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, GLOBALS.smtpServerPasswd)  

    # Send the mail
    server.sendmail(fromaddr, toaddr, msg.as_string())

    # quit smtp server
    server.quit()

# Save a new match
def persist(item):
    app = firebase.FirebaseApplication(GLOBALS.firebaseAppUrl, None)
    result = app.post('/casque', item);

# Get all the saved match
def getHelmets():
    app = firebase.FirebaseApplication(GLOBALS.firebaseAppUrl, None)
    results = app.get('/casque', None);
    data = json.dumps(results);
    return json.loads(data);

# Check if an item already exists
def checkIfExists(_url):
    data = getHelmets();
    if (data != None):
        for key in data :
            url = data[key]['url'];
            if (_url == url):
                return True;
    return False;
    

url = 'http://www.leboncoin.fr/annonces/offres/ile_de_france/?f=a&th=1&q=casque+schuberth';
html = urlopen(url).read()
soup = BeautifulSoup.BeautifulSoup(html, "html.parser")
results = soup.find('div',attrs={"class":u"list-lbc"}).findAll('a')
i = 0;

# Iterating the html parsing result
while (i < len(results)):

    # Get the item title
    title = results[i]['title'];

    # Get the item price
    div = results[i].find('div',attrs={"class":u"price"});

    # Get the url
    url = results[i]['href'];
    
    if (hasattr(div, 'string')):
        price = div.string.strip();
        price = int(re.search(r'\d+', price).group());
        lowerCaseTitle = title.lower();
        if (price <= 160 and "schuberth" in lowerCaseTitle and "c3" in lowerCaseTitle):
            # This is a match

            if (checkIfExists(url) == False):
                # The item is not present in the db so it's a new one
                
                # save the item
                persist({ 'title' : title, 'price' : price, 'url' : url });

                # Send a notification
                sendMail(title, price, url)
    i += 1;


