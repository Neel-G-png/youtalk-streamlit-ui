import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

class API():
    def __init__(self):
        self.baseurl = os.getenv("API_BASE_URL")
    
    def get_all_user_sessions(self,params):
        url = f"{self.baseurl}/get_all_user_sessions/"
        response = requests.get(
            url,
            params=params,
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Failed to fetch user sessions"
            }
        
        return {
            "status": "success",
            "data": response.json()
        }
    
    def stream_response(self, params, followup=True):
        if followup:
            url = f"{self.baseurl}/followup_stream_response/"
        else:
            url = f"{self.baseurl}/stream_response/"
        response = requests.get(
            url,
            json=params,
            stream=True
        )
        
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if chunk.startswith("data:"):
                json_data = chunk[5:].strip()
                event = json.loads(json_data)
                yield event['data']

    def get_chat_history(self, params):
        url = f"{self.baseurl}/get_chat_history/"
        response = requests.get(
            url,
            json=params,
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Failed to fetch chat history"
            }
        
        return {
            "status": "success",
            "data": response.json()
        }
    
    def process_video(self, params):
        url = f"{self.baseurl}/process_video/"
        response = requests.post(
            url,
            json=params,
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Failed to process video"
            }
        
        return {
            "status": "success",
            "data": response.json()
        }
    
    def insert_message(self, params):
        url = f"{self.baseurl}/insert_message/"
        response = requests.post(
            url,
            json=params,
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Failed to insert message but you can still chat!"
            }