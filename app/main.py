from flask import Flask, request,jsonify,send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from chat.main_chatbot import *
from chat.vectordb_creation import *
from summary.summary import *
from summary.data_extraction import *
from controls_mapping.similarity import *
from controls_mapping.vectorstore import *
from send_email.email import *
from send_email.email import send_email_to
from send_email.API_CREDS import OUTLOOK_ACCESS_TOKEN

import markdown
import os
import shutil
import pandas as pd
import uuid
import time
import io

AWS_REGION='us-west-2' # Change region as per your requirement
app = Flask(__name__)
ORIGINS = ['*']
CORS(app, origins=ORIGINS)

DEMO_SESSION = "d6fccaf7-3141-4b38-8420-6a311bb73fe2"

upload_dir = os.getcwd()
app.config['UPLOAD_FOLDER'] = upload_dir

@app.route('/health', methods=['GET'])
def health():
    return {'msg': 'OK'}

@app.route('/get_sessionId', methods=['GET'])
def get_sessionId():
    return {'sessionId': str(uuid.uuid4())}
    # return {'sessionId':DEMO_SESSION}

@app.route('/upload', methods=['POST']) 
def upload(): 
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    # Get the list of files
    files = request.files.getlist("file")
    
    ###using this user session for demo purposes.
    # user_session = DEMO_SESSION
    
    user_session = request.form.get("sessionId")

    ### Create local session folders and save pdfs
    if not os.path.exists(user_session):
        os.makedirs(user_session)
    uploads_folder = f"{user_session}/uploads"
    if not os.path.exists(uploads_folder):
        os.makedirs(uploads_folder)
    # Iterate for each file in the files List, and Save them 
    for file in files: 
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], uploads_folder,file.filename)
        file.save(save_path)

    ## Uploading file to s3
    s3_folder = f"uploads/{user_session}/uploads"
    for file in files:
        if file.filename == "":
            continue
        s3_path = s3_folder + file.filename
        
        s3_client.upload_fileobj(file, 'regulatorydatabucket', s3_path)
    
    return {'msg':'Files have been uploaded','sessionId': user_session}



@app.route('/upload_controlmaps', methods=['POST']) 
def upload_controlmaps(): 
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    # Get the list of files from webpage 
    files = request.files.getlist("file")
    
    ###using this user session for demo purposes.
    # user_session = DEMO_SESSION
    user_session = request.form.get("sessionId")
    
    ### Create local session folders and save pdfs
    folder_path = f"./{user_session}/control_maps"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    # Iterate for each file in the files List, and Save them 
    for file in files: 
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_path,file.filename)
        file.save(save_path)

    ## Uploading file to s3
    s3_folder = f"uploads/{user_session}/control_maps"
    for file in files:
        if file.filename == "":
            continue
        s3_path = s3_folder + file.filename
        
        s3_client.upload_fileobj(file, 'regulatorydatabucket', s3_path)
    
    return {'msg':'Files have been uploaded'}


@app.route('/ingestion',methods=['POST'])
def ingestion():
    # user_session = DEMO_SESSION # Using this for demo purpose
    data = request.json
    user_session = data.get('sessionId')

    ### Following code was used for demo purposes
    # source = "./processed_files"
    # destination = f"./{user_session}/processed_files"
    # if not os.path.exists(destination):
    #     os.makedirs(destination)
    # # gather all files
    # allfiles = os.listdir(source)
     
    # # iterate on all files to move them to destination folder
    # for f in allfiles:
    #     src_path = os.path.join(source, f)
    #     dst_path = os.path.join(destination, f)
    #     shutil.copy(src_path, dst_path)
    
    ### Following code was commented out for demo_purpose
    #textract ingestion
    # # AWS Configuration
    AWS_REGION = "us-west-2"
    bucket = "regulatorydatabucket"
    uploads_folder = f"{user_session}/uploads"
    allfiles = os.listdir(uploads_folder)
    file_paths = [f"uploads/{user_session}/uploads/{f}" for f in allfiles]
    for f in file_paths:
        file_path = f
        output_path = f"uploads/{user_session}/textract_output/extracted_structure.xlsx"
        output_file_key = f"uploads/{user_session}/textract_output/cleaned_articles.xlsx"
        process_pdf(bucket, file_path, output_path)
        cleaned_df = merge_sub_articles(bucket, output_path, output_file_key)
        cleaned_df.to_excel(f"./{user_session}/controls_mapping/input/extracted_structure_{f}.xlsx",index=False)

    #controls mapping ingestion - config files are used for demo purpose
    create_vector_store()

    #chatbot ingestion
    chat_vectorstore = Embeddings(folder_path = uploads_folder, vectordb_folder_path = f"./chat/faiss_index" )
    chat_vectorstore.run_vectorstore()
    
    return {'msg':'Files Processed'}


@app.route('/chat',methods=['POST'])
def chat():
    data = request.json
    user_query = data.get('query')
    # user_session = data.get('sessionId')
    user_session = DEMO_SESSION
    chatbot = ChatBot()
    response = chatbot.main(user_query)
    return {'msg':response}


@app.route('/summary',methods=['POST'])
def summ():
    data = request.json
    user_session = data.get('sessionId')
    # user_session = DEMO_SESSION
    
    ### commented out for demo purpose
    old_excel_path = f"./{user_session}/processed_files/proposal.xlsx"
    new_excel_path= f"./{user_session}/processed_files/DORA_New_Structured_ygt.xlsx"

    ### The following 2 lines used for demo purpose
    # old_excel_path = "dummy_string"
    # new_excel_path = "dummy_string"
    summary_response = get_summary(old_excel_path=old_excel_path,new_excel_path=new_excel_path,user_session=user_session)
    # time.sleep(20) # For demo purpose. Actual process may take much longer.
    return summary_response
    

@app.route('/controls',methods=['POST'])
def controls():
    data = request.json
    user_session = data.get('sessionId')
    # user_session = DEMO_SESSION
    control_type = data.get('control_type')
    # control_type = "CSTP.1" used for demo purpose

    ### Commented out for demo purpose
    df_output=get_controls(user_session=user_session,control_filter=[control_type])

    # Used for demo purpose
    # df_output = pd.read_csv('./controls_mapping/output/output_filter.csv')
    
    data_dict = dict()
    for col in df_output.columns:
        data_dict[col] = df_output[col].values.tolist()

    time.sleep(10)
    return jsonify(data_dict)



@app.route('/send_email',methods=['POST'])
def email_notif():
    data=request.json
    recipient_email = data.get('recipient_email')
    user_session = data.get('sessionId')
    # user_session = DEMO_SESSION

    ###Commented out for demo purpose
    folder_path = f"./{user_session}/comparison_output"
    # folder_path = "./summary/comparison_output" # Used for demo purpose
    
    sub_theme_output_path = os.path.join(folder_path, "sub_theme_level.xlsx")
    theme_level_output_path = os.path.join(folder_path, "theme_level.xlsx")
    email_text_file = os.path.join(folder_path, "document_level.txt")
    
    send_email_to(
    recipient_email=recipient_email, 
    access_token=OUTLOOK_ACCESS_TOKEN,
    email_text_file=email_text_file, 
    excel_attachment_one=sub_theme_output_path, 
    excel_attachment_two=theme_level_output_path)

    print("Email Sent")
    return {'msg':'Email sent'}

@app.route('/download_comparison',methods=['POST'])
def donwload_comp():
    data = request.json
    # user_session = data.get('sessionId')
    user_session = DEMO_SESSION
    
    ### Commented out for demo purpose
    folder_path = f"{user_session}/comparison_output"
    
    if not os.path.exists(user_session):
        os.makedirs(folder_path)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer, pd.ExcelWriter(os.path.join(folder_path, 'consolidated_output.xlsx'), engine="openpyxl") as local_writer:
    for filename in ["sub_theme_level.xlsx", "theme_level.xlsx", "document_level.txt"]:
        file_path = os.path.join(folder_path, filename)
        if os.path.exists(file_path):
            if filename.endswith(".xlsx"):
                df = pd.read_excel(file_path)
            else:
                with open(file_path, "r") as txt_file:
                    df = pd.DataFrame(txt_file.readlines(), columns=["Text"])
            df.to_excel(writer, sheet_name=os.path.splitext(filename)[0], index=False)
            df.to_excel(local_writer, sheet_name=os.path.splitext(filename)[0], index=False)

    ### Commented code used for demo purposes
    # folder_path = "./summary/comparison_output"
 
    # excel_buffer = io.BytesIO()
    # with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer, pd.ExcelWriter(os.path.join(folder_path, 'consolidated_output.xlsx'), engine="openpyxl") as local_writer:
    #     for filename in ["sub_theme_level.xlsx", "theme_level.xlsx", "document_level.txt"]:
    #         file_path = os.path.join(folder_path, filename)
    #         if os.path.exists(file_path):
    #             if filename.endswith(".xlsx"):
    #                 df = pd.read_excel(file_path)
    #             else:
    #                 with open(file_path, "r") as txt_file:
    #                     df = pd.DataFrame(txt_file.readlines(), columns=["Text"])
    #             df.to_excel(writer, sheet_name=os.path.splitext(filename)[0], index=False)
    #             df.to_excel(local_writer, sheet_name=os.path.splitext(filename)[0], index=False)
            
    excel_buffer.seek(0)
    print("File downloaded")
    return send_file(excel_buffer, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="comparison_output.xlsx")


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
    