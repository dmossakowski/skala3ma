# SKALA3MA

Application to manage climbing gym routes and competitions. 

https://skala3ma.com

![logo](public/images/skala3ma-front.png)

## Features:
- Add and edit gym with logo
- Add and edit route sets
- Create a competition
- Public registration link
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

5. Run the server
  ```
  python server.py
  ```

6. Using your favorite browser go to https:localhost:5000/




