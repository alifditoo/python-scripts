import os
import base64
import time
from oauth2client import file, client, tools
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from httplib2 import Http
from googleapiclient import errors

class EmailUtilities:
    def __init__(self, user_name, user_email, google_credentials_path, google_token_path):
        ''' 
        Explanation: The code above initializes the attributes needed to send an email. 
        user_name and user_email are used to specify the sender of the email, 
        while google_credentials_path and google_token_path are used to authenticate access to the Gmail API.
        
        Parameters:
        user_name (str): The name of the user that will be displayed as the sender of the email.
        user_email (str): The email address of the user that will be used as the sender.
        google_credentials_path (str): The path to the Google credentials file for authentication.
        google_token_path (str): The path to the Google token file used to store the access token.
        scope (list): The scope of access requested for the Gmail API, in this case, it allows modifying Gmail.
        '''
        self.user_name = user_name
        self.user_email = user_email
        self.google_credentials_path = google_credentials_path
        self.google_token_path = google_token_path
        self.scope = ['https://www.googleapis.com/auth/gmail.modify']
        
    def send_email(self, subject, html_content, alias=None, alias_email=None, attachment_files=None, to=None, cc=None):
        ''' 
        This function is used to send an email with a subject, HTML content, 
        alias, alias email, attachment files, recipients, and cc specified.
        
        Parameters:
        subject (str): The subject of the email to be sent.
        html_content (str): The content of the email in HTML format.
        alias (str, optional): The alias name of the sender. Default is None.
        alias_email (str, optional): The alias email address of the sender. Default is None.
        attachment_files (list, optional): A list of attachment files to be sent. Default is None.
        to (str or list, optional): The recipient's email address. Can be a string or a list. Default is None.
        cc (str or list, optional): The email address for cc. Can be a string or a list. Default is None.
        '''
        store = file.Storage(self.google_token_path)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(self.google_credentials_path, self.scope)
            creds = tools.run_flow(flow, store)
        service_email = build('gmail', 'v1', http=creds.authorize(Http()))

        message = MIMEMultipart()
        
        if alias:
            message['from'] = f'{alias} <{alias_email}>'
        else:
            message['from'] = f'{self.user_name} <{self.user_email}>'
        message['to'] = ', '.join(to) if isinstance(to, list) else to
        if cc:
            message['cc'] = ', '.join(cc) if isinstance(cc, list) else cc
        message['subject'] = subject

        message.attach(MIMEText(html_content,'html'))

        if attachment_files:
            for attachment_file in attachment_files:
                attachment = open(attachment_file, 'rb')
                part = MIMEBase('application', 'octet-stream')
                part.set_payload((attachment).read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename= %s' % os.path.basename(attachment_file))
                print(os.path.basename(attachment_file))
                message.attach(part)

        raw = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')}

        while True:
            try:
                result = (service_email.users().messages().send(userId='me', body=raw).execute())
                print('Message Id: %s' % result['id'])
                return result
            except Exception as err:
                print('An error occurred: %s' % err)
            time.sleep(30)

    def get_message_ids(self, query='', user_id='me'):
        ''' 
        This function is used to retrieve message IDs based on the provided query 
        and user ID.
        
        Parameters:
        query (str, optional): The search query to retrieve messages. Default is an empty string.
        user_id (str, optional): The Gmail user ID. Default is 'me', which means the current user.
        
        Returns:
        list: A list of messages found based on the query.
        '''
        store = file.Storage(self.google_token_path)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(self.google_credentials_path, self.scope)
            creds = tools.run_flow(flow, store)
        service_email = build('gmail', 'v1', http=creds.authorize(Http()))
        
        try:
            response = service_email.users().messages().list(userId=user_id, q=query).execute()
            messages = []
            if 'messages' in response:
                messages.extend(response['messages'])
            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = service_email.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
                messages.extend(response['messages'])
            return messages
        except errors.HttpError as error:
            print('An error occurred: {}'.format(error))

    def get_attachments_from_email(self, msg_id, prefix="", user_id='me'):
        ''' 
        This function is used to retrieve attachments from an email 
        based on the provided message ID.
        
        Parameters:
        msg_id (str): The message ID of the email from which to retrieve attachments.
        prefix (str, optional): The prefix for the filename when saving the attachment. Default is an empty string.
        user_id (str, optional): The Gmail user ID. Default is 'me', which means the current user.
        
        Returns:
        None: This function does not return a value, but saves the attachments to files.
        '''
        store = file.Storage(self.google_token_path)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(self.google_credentials_path, self.scope)
            creds = tools.run_flow(flow, store)
        service_email = build('gmail', 'v1', http=creds.authorize(Http()))
        
        try:
            message = service_email.users().messages().get(userId=user_id, id=msg_id).execute()
            for part in message['payload'].get('parts', ''):
                if part['filename']:
                    if 'data' in part['body']:
                        data = part['body']['data']
                    else:
                        att_id = part['body']['attachmentId']
                        att = service_email.users().messages().attachments().get(userId=user_id, messageId=msg_id,
                                                                                id=att_id).execute()
                        data = att['data']
            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
            path = os.path.join(prefix, msg_id + '_' + part['filename'])
            print(path)
            print('Getting ' + part['filename'])
            with open(path, 'wb') as f:
                f.write(file_data)
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def get_df_from_attachments(self, msg_id, user_id='me'):
        ''' 
        This function is used to retrieve data from attachments 
        based on the provided message ID.
        
        Parameters:
        msg_id (str): The message ID of the email from which to retrieve data.
        user_id (str, optional): The Gmail user ID. Default is 'me', which means the current user.
        
        Returns:
        bytes: The data from the attachment that has been decoded.
        '''
        store = file.Storage(self.google_token_path)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(self.google_credentials_path, self.scope)
            creds = tools.run_flow(flow, store)
        service_email = build('gmail', 'v1', http=creds.authorize(Http()))
        
        try:
            message = service_email.users().messages().get(userId=user_id, id=msg_id).execute()
            for part in message['payload'].get('parts', ''):
                if part['filename']:
                    if 'data' in part['body']:
                        data = part['body']['data']
                    else:
                        att_id = part['body']['attachmentId']
                        att = service_email.users().messages().attachments().get(userId=user_id, messageId=msg_id,
                                                                                id=att_id).execute()
                        data = att['data']
            file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
            return file_data
        except errors.HttpError as error:
            print('An error occurred: %s' % error)
