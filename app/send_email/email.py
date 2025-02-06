import boto3
import json
import requests
import logging
import base64
import os

def file_to_base64(file_path):
    """Reads a file and converts it to a Base64 string."""
    with open(file_path, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode("utf-8")
    return encoded_string

def read_text_file(file_path):
    """Reads a text file and returns its content as a string."""
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def send_email_to(recipient_email, access_token, email_text_file, excel_attachment_one, excel_attachment_two):
    """
    Creates an Email instance and sends an email.

    Args:
        recipient_email (str): The recipient's email address.
        access_token (str): Microsoft Graph API access token.
        email_text_file (str): Path to the email body text file.
        excel_attachment_one (str): Path to the first Excel file.
        excel_attachment_two (str): Path to the second Excel file.
    """
    try:
        email = Email()
        email.Send_Email(
            access_token=access_token,
            to_recipients=[{"emailAddress": {"address": email}} for email in recipient_email],
            email_text_file=email_text_file,
            excel_attachment_one=excel_attachment_one,
            excel_attachment_two=excel_attachment_two
        )
        print(f"📧 Email sent successfully to {recipient_email}!")
    except Exception as e:
        print(f"❌ Failed to send email! Error: {str(e)}")

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class Email:
    """Handles email sending via Microsoft Graph API."""

    def __init__(self):
        self.to_recipients = None
        self.access_token = None        
        self.bedrock = boto3.client(service_name="bedrock-runtime", region_name="us-west-2")

    def Send_Email(self, access_token, to_recipients, email_text_file, excel_attachment_one, excel_attachment_two):
        """
        Sends an email using the Microsoft Graph API with attachments.

        Args:
            access_token (str): OAuth access token for Microsoft Graph API.
            to_recipients (list): List of recipient email addresses.
            email_text_file (str): Path to the text file for the email body.
            excel_attachment_one (str): Path to the first Excel file.
            excel_attachment_two (str): Path to the second Excel file.
        """
        endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"
        self.access_token = access_token
        self.to_recipients = to_recipients

        # Read email body from text file
        email_body = read_text_file(email_text_file)
        # Add salutation and signature
        salutation = "Dear Team,\n\n"
        signature = "\n\nBest regards,\nCompliance Team"
        
        full_email_content = f"{salutation}{email_body}{signature}"  # Combine all parts
    
        # Convert Excel files to Base64
        excel_one_base64 = file_to_base64(excel_attachment_one)
        excel_two_base64 = file_to_base64(excel_attachment_two)

        # Extract the actual filename from the file path
        excel_one_filename = os.path.basename(excel_attachment_one)
        excel_two_filename = os.path.basename(excel_attachment_two)

        # Construct the email payload
        email_msg = {
            "message": {
                "subject": "Summary of Key Regulatory Changes",
                "body": {
                    "contentType": "text",
                    "content": full_email_content  # Using text file content
                },
                "toRecipients": self.to_recipients,
                "attachments": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": excel_one_filename,
                        "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "contentBytes": excel_one_base64
                    },
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": excel_two_filename,
                        "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "contentBytes": excel_two_base64
                    }
                ]
            }
        }

        # Set headers
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        # Send email
        response = requests.post(endpoint, json=email_msg, headers=headers)

        if response.status_code == 202:
            logging.info("✅ Email sent successfully!")
        else:
            logging.error(f"❌ Failed to send email: {response.status_code}")
            logging.error(response.text)


# Function to send an email

