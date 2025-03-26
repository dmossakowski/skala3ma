import os
import requests
from flask import url_for
from itsdangerous import URLSafeTimedSerializer
import logging
from datetime import datetime

CONTACT_EMAIL = os.getenv('CONTACT_EMAIL')


class EmailSender:
    def __init__(self, reference_data):
        self.smtp_api_key = os.getenv("SMTP_API_KEY")
        self.reference_data = reference_data


    def send_registration_email(self, email, confirm_url):
        
        email_subject = self.reference_data['current_language']['registration_email_subject']
        email_text = """
<img src='https://skala3ma.com/public/images/favicon.png' width="35">
<span style="color: #44C662; font-size: 38px; font-weight:700; font-family: 'sans-serif', 'Arial'"> SKALA3MA</span>

<br><br>"""+self.reference_data['current_language']['hello']+"""  """+ email +"""  
<br><br>

"""+self.reference_data['current_language']['registration_email_text1']+"""

<a href='"""+confirm_url+"""'>"""+ self.reference_data['current_language']['registration_email_text2']+"""</a>.

<br><br>
"""+ self.reference_data['current_language']['registration_email_text3'] +""" 

<br><br>
    """

        ret = requests.post(
            "https://api.eu.mailgun.net/v3/skala3ma.com/messages",
            auth=("api", self.smtp_api_key),
            data={"from": "SKALA3MA Admin <do-not-reply@skala3ma.com>",
                "to": [email],
                "subject": email_subject,
                "text": "Thanks for registering. Copy and paste this link in your browser: "+confirm_url+"" ,
                "html": email_text
                })
                
        return 'mail sent'+str(ret.reason)+' '+str(ret.text)


    def send_password_reset_email(self, email, confirm_url):
        email_subject = self.reference_data['current_language']['reset_password_email_subject']
        
        email_text = """<img src='https://skala3ma.com/public/images/favicon.png' width="35">
                <span style="color: #44C662; font-size: 38px; font-weight:700; font-family: 'sans-serif', 'Arial'"> SKALA3MA</span>

                <br><br>
                <a href='"""+confirm_url+"""'>
                """+self.reference_data['current_language']['reset_password_email_text1']+"""
               </a>.
                <br><br> 
        """

        ret = requests.post(
            "https://api.eu.mailgun.net/v3/skala3ma.com/messages",
            auth=("api", self.smtp_api_key),
            data={"from": "SKALA3MA <do-not-reply@skala3ma.com>",
                "to": [email],
                "subject": email_subject,
                "text": "To reset password copy and paste this link in your browser: "+confirm_url+" ",
                "html": email_text
                })
        
        return 'mail sent reason='+str(ret.reason)+' text='+str(ret.text)+' ret.status_code='+str(ret.status_code)
    
    
    def send_email_to_participant(self, competition_name, competition_url, email_to, email_content):
        
        email_subject = self.reference_data['current_language']['competitions']+': '+competition_name
        email_link_text = self.reference_data['current_language']['reset_password_email_text1']
        #competition_url = f"{self.base_url}/competitionDetails/{competition_id}?token={token}"

        email_text = """
    <img src='https://skala3ma.com/public/images/favicon.png' width="35">
                <span style="color: #44C662; font-size: 38px; font-weight:700; font-family: 'sans-serif', 'Arial'"> SKALA3MA</span>

                <br><br>"""+self.reference_data['current_language']['competition_participants_email0']+"""
                <a href='"""+competition_url+"""'>"""+competition_name+"""</a>.
                <br>
                """+self.reference_data['current_language']['competition_participants_email1']+"""
                <pre style="font-family: Arial, Helvetica, sans-serif; white-space: pre-wrap; background-color: #f9f9f9; padding: 10px; border-radius: 5px;">
"""+email_content+"""
                </pre>
                <br><br> 
                """+self.reference_data['current_language']['competition_participants_email2']+"""
                
        """

        ret = requests.post(
            "https://api.eu.mailgun.net/v3/skala3ma.com/messages",
            auth=("api", self.smtp_api_key),
            data={"from": "SKALA3MA <do-not-reply@skala3ma.com>",
                "to": [email_to],
                "subject": email_subject,
                "text": "This is a message from competition organizers: "+email_content+"   "+competition_url+" ",
                "html": email_text
                })
        
        return 'mail sent'+ret.reason+' '+ret.text
        


    def send_email_to_organizer(self, email_from, name, subject, email_content, email_to, competition_string, competition_url):
        
        # if email_to is not an array
        if not isinstance(email_to, list):
            raise ValueError('email_to must be a list')
        
        email_subject = self.reference_data['current_language']['competitions']
        email_link_text = self.reference_data['current_language']['reset_password_email_text1']
        competition_contact_email0 = self.reference_data['current_language']['competition_contact_email0']
        competition_contact_email1 = self.reference_data['current_language']['competition_contact_email1']
        
        competition_name = 'Contact message'
        if subject is None:
            subject = 'No subject'
        email_text = """
    
                <span style="color: #44C662; font-size: 38px; font-weight:700; font-family: 'sans-serif', 'Arial'"> SKALA3MA</span>
                <br><br>"""+competition_contact_email0+""" 
                <br><br>"""+name+""" ("""+email_from+""")"""+ competition_contact_email1+""" '"""+competition_string+"""'
                <br>    
                
                <pre style="font-family: Arial, Helvetica, sans-serif; white-space: pre-wrap; background-color: #f9f9f9; padding: 10px; border-radius: 5px;">
"""+email_content+"""
                </pre>
                <br><br>Competition URL: <a href='"""+competition_url+"""'>"""+competition_url+"""</a>
        """

        ret = requests.post(
            "https://api.eu.mailgun.net/v3/skala3ma.com/messages",
            auth=("api", self.smtp_api_key),
            data={"from": "SKALA3MA <do-not-reply@skala3ma.com>",
                "to": email_to,
                "subject": ""+name+" - "+subject,
                "text": "Contact message from:  "+name+" \n"+email_from+"\n"+email_content,
                "html": email_text
                })

    
    def send_contact_email(self, session_email, email_from, name, subject, email_content, email_to=CONTACT_EMAIL,):
        if email_from is None:
            raise ValueError('email_from must be provided')
        
        current_date = datetime.now().strftime("%Y-%m-%d")

        email_subject = self.reference_data['current_language']['competitions']
        email_link_text = self.reference_data['current_language']['reset_password_email_text1']
        competition_url = "BLAH BLAH" # f"{self.base_url}/competitionDetails/"
        competition_name = 'Contact message'
        if session_email is None:
            session_email = 'Not logged in'

        if subject is None:
            subject = 'No subject'
        email_text = """
    
                <span style="color: #44C662; font-size: 38px; font-weight:700; font-family: 'sans-serif', 'Arial'"> SKALA3MA</span>
                <br><br>Contact email from """+name+""" at """+email_from+""" - logged in as """+session_email+"""
               
                <br>
                <pre style="font-family: Arial, Helvetica, sans-serif; white-space: pre-wrap; background-color: #f9f9f9; padding: 10px; border-radius: 5px;">
"""+email_content+"""
                </pre>
                
        """

        ret = requests.post(
            "https://api.eu.mailgun.net/v3/skala3ma.com/messages",
            auth=("api", self.smtp_api_key),
            data={"from": "SKALA3MA <do-not-reply@skala3ma.com>",
                "to": [email_to],
                "subject": "Contact from "+name+" - "+current_date+ " - "+subject,
                "text": "Contact message from:  "+name+"  "+email_from+"  "+email_content,
                "html": email_text
                })
        
        return 'mail sent'+ret.reason+' '+ret.text
        
