import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleDrive:
    def __init__(self, google_credentials_path, google_token_path):
        '''
        Initializes the GoogleServiceUtilities class with the provided credentials paths.

        Parameters:
        google_credentials_path (str): The path to the Google credentials JSON file.
        google_token_path (str): The path to the token file where the access token will be stored.
        '''
        self.google_credentials_path = google_credentials_path
        self.google_token_path = google_token_path
        self.scope = ['https://www.googleapis.com/auth/drive']
        
        self.credentials = Credentials.from_authorized_user_file(self.google_token_path, self.scope)
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.google_credentials_path, self.scope)
                self.credentials = flow.run_local_server(port=0)
                
                with open(self.google_token_path, 'w') as token:
                    token.write(self.credentials.to_json())
        
        self.gdrive = build('drive', 'v3', credentials=self.credentials)
        self.googledrive_auth = GoogleAuth()
        self.googledrive_auth.credentials = self.credentials
        self.pydrive = GoogleDrive(self.googledrive_auth)
    
    #-- This will upload file to Google Drive --#
    def upload_file_gdrive(self, parent_id, mime_type, filename):
        '''
        Uploads a file to Google Drive.

        Parameters:
        parent_id (str): The ID of the parent folder in Google Drive where the file will be uploaded.
        mime_type (str): The MIME type of the file being uploaded (e.g. 'application/pdf' for PDF files, 'image/jpeg' for JPEG images, or 'text/csv' for CSV files).
        filename (str): The name of the file to be uploaded.

        Returns:
        str: The ID of the uploaded file.
        '''
        media_body = MediaFileUpload(filename, mimetype=mime_type, resumable=True)
        body = {'name': filename, 'mimeType': mime_type, 'parents': [parent_id]}

        file = self.gdrive.files().create(
            body=body,
            media_body=media_body, fields='id', supportsAllDrives=True).execute()
        print('File ID: %s' % file['id'])
        return file['id']

    #-- This will move file in Google Drive --#
    def move_file_gdrive(self, fileId, newParentId):
        '''
        Moves a file to a new parent folder in Google Drive.

        Parameters:
        fileId (str): The ID of the file to be moved.
        newParentId (str): The ID of the new parent folder.

        Returns:
        dict: The updated file metadata.
        '''
        files = self.pydrive.auth.service.files()
        file = files.get(fileId=fileId, fields='parents').execute()
        prev_parents = ','.join(p['id'] for p in file.get('parents'))
        file = files.update(fileId=fileId,
                             addParents=newParentId,
                             removeParents=prev_parents,
                             fields='id, parents',
                             ).execute()
        return file

    #-- This will create folder in Google Drive --#
    def create_folder_gdrive(self, folderName, parentID=None):
        '''
        Creates a new folder in Google Drive.

        Parameters:
        folderName (str): The name of the folder to be created.
        parentID (str, optional): The ID of the parent folder. If None, the folder will be created in the root.

        Returns:
        str: The ID of the created folder.
        '''
        body = {
            'name': folderName,
            'mimeType': "application/vnd.google-apps.folder"
        }
        if parentID:
            body['parents'] = [parentID]
        root_folder = self.gdrive.files().create(body=body).execute()
        return root_folder['id']

    #-- This will download file from Google Drive --#
    def download_file_gdrive(self, file_id):
        '''
        Downloads a file from Google Drive.

        Parameters:
        file_id (str): The ID of the file to be downloaded.

        Returns:
        str: The name of the downloaded file.
        '''
        file = self.pydrive.CreateFile({'id': file_id})
        file_name = self.gdrive.files().get(fileId=file_id, fields='*').execute()['name']
        file.GetContentFile(file_name)
        print('File Name :' + file_name)
        return file_name

    #-- This will list files in Google Drive --#
    def list_file_gdrive(self, parent_id, query=None):
        '''
        Lists files in a specified Google Drive folder.

        Parameters:
        parent_id (str): The ID of the parent folder to list files from.
        query (str, optional): Additional query to filter the files.

        Returns:
        DataFrame: A pandas DataFrame containing the list of files.
        '''
        if query is None:
            query = f"parents = '{parent_id}'"
        else:
            query = f"parents = '{parent_id}' AND {query}"
        try:
            response = self.gdrive.files().list(supportsAllDrives=True, includeItemsFromAllDrives=True, q=query).execute()
            files = response.get('files')
            nextPageToken = response.get('nextPageToken')

            while nextPageToken:
                response = self.gdrive.files().list(supportsAllDrives=True, includeItemsFromAllDrives=True, q=query).execute()
                files = response.get('files')
                nextPageToken = response.get('nextPageToken')

            df_list_file = pd.DataFrame(files)
            return df_list_file
        except Exception as err:
            raise Exception(f'Error to get list file. {err}')