# SKALA3MA

Application to manage climbing gym routes and competitions. 

https://skala3ma.com

![logo](public/images/skala3ma-front.png)

## Features:
- Add and edit gym with logo, address, URL
- Add and edit multiple route sets
- Create a competition
- Public competition registration link
- Easy route entry during competition
- Instant scoring
- Multi-language
- Google and Facebook logins



## Technologies used

- Python 3
- Flask
  - OAuth libraries for authentication
- Jinja2 templates
- Apexcharts https://apexcharts.com/
- Tabulator https://tabulator.info/




![logo](public/images/skala3ma-route-edit.png)

## Development environment setup

Minimum version of Python is 3.7. 

1. Create certificate and key files:
``` 
 openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem
```

2. Create Python Virtual Environment
```
  python -m venv .venv
```

3. Enter Virtual Environment
```
  source .venv/bin/activate
```

4. Install the requirements
```
  pip install -r requirements.txt
```
4. Export the following variables 

```
   export DATA_DIRECTORY=<path to the data directory/create one as needed>
   export GOOGLE_CLIENT_ID=<your Google client id>
   export GOOGLE_CLIENT_SECRET=<your Google client secret>
```
   
   See how to create your Google client ID and secret at [https://developers.google.com/identity/protocols/oauth2?hl=en](https://developers.google.com/identity/protocols/oauth2?hl=en)

5. Run the server
```
  python server.py
```

6. Using your favorite browser go to https://localhost:5000/




