# LeboncoinScrapper
Little python script to alert (gmail) when a new item that match criteria is available on leboncoin.fr, using BeautifulSoup and firebase

### It's damn simple :

##### First external dependencies are needed :BeautifulSoup and Firebase
```
pip install beautifulsoup4

sudo pip install requests==1.1.0
sudo pip install python-firebase
```

##### Then create a little conf file for retrieving credentials, name it : params.py 
```python
class Globals():
    smtpServerLogin     = "SENDER_ACCOUNT_LOGIN@gmail.com";
    smtpServerPasswd    = "SENDER_ACCOUNT_PASSWORD";
    smtpServerRecipient = "RECIPIENT_EMAIL";
    firebaseAppUrl      = "YOU_FIREBASE_IO_URL";
```

```python
# import scrapper object from scrap.py
from scrap import Scrapper

# instanciate the scrapper
scrapper = Scrapper();

# scrap(PRICE_LIMIT, ALL_YOUR_CRITERIA, ...)
scrapper.scrap(500, "guitare", "fender", "usa");
```
