# SKALA3MA

Application to manage climbing gym routes, your daily climbing progress and competitions. 

https://skala3ma.com

![logo](public/images/skala3ma-front.png)

## Features:
- Add and edit gym with logo, address, URL
- Add and edit multiple route sets
- Add and edit activities and mark each ascent as complete, flash or incomplete with a comment
- View graph of activities
- Create a competition with a poster
- Public competition registration link
- Easy route entry during competition
- Instant scoring and downloadable CSV results
- Multi-language
- Google and Facebook logins
- Printable route page for gyms



## Technologies used

- Python 3
- Flask
  - OAuth libraries for authentication
- Jinja2 templates
- Apexcharts https://apexcharts.com/
- Tabulator https://tabulator.info/




![logo](public/images/skala3ma-route-edit.png)

## Development environment setup

The following instructions are for local development. 

Minimum version of Python is 3.7. You will need to have either Google or Facebook developer account and add the app there to enable local authentication.

1. Create certificate and key files:
``` 
 openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -keyout key.pem -out cert.pem
```


certificate generation for mobile app:

```
cd /Users/david/dev/gitrepos/skala3ma && if [ -f dev-local.pem ] && [ -f dev-local-key.pem ]; then echo "dev cert exists"; else echo "Generating dev-local cert covering 127.0.0.1 localhost ::1 10.0.2.2 with openssl"; cat > openssl-dev.cnf <<'EOF'
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
prompt             = no
req_extensions     = req_ext
x509_extensions    = v3_req

[ req_distinguished_name ]
C            = US
ST           = Local
L            = Local
O            = Dev
OU           = Dev
CN           = 127.0.0.1

[ req_ext ]
subjectAltName = @alt_names

[ v3_req ]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[ alt_names ]
DNS.1   = localhost
IP.1    = 127.0.0.1
IP.2    = 10.0.2.2
IP.3    = ::1
EOF
 openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout dev-local-key.pem -out dev-local.pem -config openssl-dev.cnf; fi

 ```

 install it:

 ```
 export AUTHLIB_INSECURE_TRANSPORT=true; pkill -f "python .*server.py" || true; sleep 0.5; /Users/david/dev/gitrepos/skala3ma/venv312/bin/python /Users/david/dev/gitrepos/skala3ma/server.py | sed -u -e 's/\x1b\[[0-9;]*m//g' | head -n 5

 ```


 generate der for the certiifcate to install it on the app

 ```
 if [ -f dev-local.pem ]; then openssl x509 -outform der -in dev-local.pem -out /Users/david/dev/gitrepos/skala3ma/mobile/Skala3maMobile/android/app/src/main/res/raw/dev_local.cer; else echo "dev-local.pem not found"; fi

 if [ -f /Users/david/dev/gitrepos/skala3ma/dev-local.pem ]; then openssl x509 -outform der -in /Users/david/dev/gitrepos/skala3ma/dev-local.pem -out /Users/david/dev/gitrepos/skala3ma/mobile/Skala3maMobile/android/app/src/main/res/raw/dev_local.cer; else echo "dev-local.pem not found"; fi

```

rebuild the app
```

export PATH="/opt/homebrew/opt/node@20/bin:$PATH"; export JAVA_HOME="$(/usr/libexec/java_home -v 17)"; /Users/david/dev/gitrepos/skala3ma/mobile/Skala3maMobile/android/gradlew -p /Users/david/dev/gitrepos/skala3ma/mobile/Skala3maMobile/android :app:installDebug

adb logcat -c; adb shell am force-stop com.skala3mamobile; adb shell am start -n com.skala3mamobile/.MainActivity; sleep 2; adb logcat -d | grep -i -E "(SSLHandshakeException|CERTIFICATE|UnknownServiceException|https:\/\/10\.0\.2\.2:3000|gyms)" | tail -n 120

 ```





2. Create Python Virtual Environment
```
  python -m venv .venv
```

3. Enter Virtual Environment
```
  source .venv/bin/activate
  
  If on windows:
  source .venv/scripts/activate
```

4. Install the requirements
```
  pip install -r requirements.txt
```
4. Modify the .env file to set the correct values

```
  DATA_DIRECTORY=<path to the data directory>
  GOOGLE_CLIENT_ID=<your Google client id>
  GOOGLE_CLIENT_SECRET=<your Google client secret>
  FACEBOOK_CLIENT_ID=<facebook client id>
  FACEBOOK_CLIENT_SECRET=<facebook client secret>
  GODMODE=true
```
DATA_DIRECTORY can be relative but must exist. If omitted the system will create db and uploads directories in the current working directory.

See how to create your Google client ID and secret at [https://developers.google.com/identity/protocols/oauth2?hl=en](https://developers.google.com/identity/protocols/oauth2?hl=en)

To create your facebook client head to Meta console:
    https://developers.facebook.com/

You will need to create your development account and create a new app there. Add Facebook login product and add your URL to the redirect list of URLS: https://localhost:5000/facebook/auth

5. Run the server
```
  python server.py
```

You can also run the server using gunicorn:
```
  gunicorn --timeout 60 --limit-request-line 0 --limit-request-field_size 0 -b :5000 --keyfile=key.pem --certfile=cert.pem  -c app.py server:app
```

6. Using your favorite browser go to https://localhost:5000/

7. The first user that logs in will be given all permissions to create gyms, competitions, etc. This user is assumed to be a full admin. This functionality is independent of the GODMODE setting in .env file. Setting GODMODE=true in .env file will make every user a full admin. This is what happens on [skala3ma-develop.onrender.com](https://skala3ma-develop.onrender.com/) site where we do beta tests.

8. The application starts completely empty so to do any tests you will need to: 
  - create a gym 
  - create a competition 
  - sign up yourself for the competition
  - logout and sign up some anonymous users
  - manage the state of competition through admin console

  We will try to provide a test database that will have a good set of working data soon.




