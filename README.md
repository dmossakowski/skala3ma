SKALA3MA
=========================


![logo](public/images/skala3ma-front.png)

https://skala3ma.com

Application to manage climbing gym routes and competitions. 

Features:
- Add and edit gym
- Add and edit route sets
- Create a competition
- Public registration link
- Easy route entry during competition
- Instant scoring
- Multi-language
- Google and Facebook logins



Technologies used
-----------------

- Python 3
- Flask
- OAuth libraries for authentication with Spotify
- Jinja2 templates
- Apexcharts https://apexcharts.com/
- Tabulator https://tabulator.info/




![logo](public/images/skala3ma-route-edit.png)


To setup development environment:

1 Create certificate and key file:
# openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem

2. Create Python Virtual Environment
python -m venv $VIRTUALENV

3. Enter Virtual Environment
  source $VIRTUALENV/bin/activate

4 Install the requirements
$VIRTUALENV/bin/pip install -r requirements.txt

5 Run the server
python server.py

# create localhost certificats:
# openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout key.pem

# allow chrome to open self signed https localhost:
# chrome://flags/#allow-insecure-localhost


#deactivate


