from flask import Flask, request, redirect, render_template_string, send_from_directory
import boto3
from botocore.exceptions import ClientError
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
AWS_REGION = 'us-east-1'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

s3_resource = boto3.resource('s3', region_name=AWS_REGION)
api_gateway_client = boto3.client('apigateway', region_name=AWS_REGION)
BUCKET_NAME = "input1-sreeni1"
OUTPUT_BUCKET_NAME = "output1-sreeni1"
EMAIL_ADDRESS = 'venkatasreenivas12@gmail.com'  # Your email address

@app.route('/')
def index():
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Simple File Upload</title>
                                  <p>For any queries, please drop a mail to venkatasreenivas12@gmail.com</p>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }
        .container {
            max-width: 600px;
            margin: 20px;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        .alert {
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid transparent;
            border-radius: 4px;
        }
        .alert-success {
            color: #155724;
            background-color: #d4edda;
            border-color: #c3e6cb;
        }
        .alert-danger {
            color: #721c24;
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        button {
            padding: 10px 20px;
            background-color: #007bff;
            border: none;
            color: white;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        textarea {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Upload files using Python and Flask</h1>
    <form method="post" enctype="multipart/form-data" action="/upload">
        <div class="mb-3">
            <input type="file" id="file" name="file" required>
        </div>
        <button type="submit">Upload File(s)</button>
    </form>
    <form method="post" action="/send_email">
        <textarea id="message" name="message" rows="4" placeholder="Write your message here..."></textarea>
        <button type="submit">Send Email</button>
    </form>
</div>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script>
    $('#file').on('change', function() {
        var fileName = $(this).val().split('\\').pop();
        $(this).next('.form-control').addClass("selected").val(fileName);
    });
</script>
</body>
</html>
''')

def get_api_url(api_name, stage_name, filename):
    try:
        response = api_gateway_client.get_rest_apis()
        api_id = next((item['id'] for item in response['items'] if item['name'] == api_name), None)

        if not api_id:
            raise Exception(f"API Gateway '{api_name}' not found.")

        api_url = f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/{stage_name}/transcribe"
        json_body = {
            "source_bucket": BUCKET_NAME,
            "source_key": filename
        }

        response = requests.post(api_url, json=json_body)
        if response.status_code == 200:
            return response.json()['transcribed_key']  # assuming the response contains the transcribed file key
        else:
            error_message = f"Error: Received status code {response.status_code} with message: {response.text}"
            raise Exception(error_message)
    except Exception as e:
        error_message = f"Error while calling API Gateway: {str(e)}"
        print(error_message)  # Consider using logging
        raise Exception(error_message)  # Reraising the exception to handle it upstream

def send_email(subject, body):
    try:
        sender_email = "venkatasreenivas12@gmail.com"  # Replace with your email address
        recipient_email = EMAIL_ADDRESS

        # Setup the MIME
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        # Attach the body with the msg instance
        message.attach(MIMEText(body, 'plain'))

        # Create SMTP session for sending the mail
        session = smtplib.SMTP('smtp.gmail.com', 587)  # Use appropriate SMTP server
        session.starttls()  # Enable security
        session.login(sender_email, "qboq filb eien tabj")  # Login with your email and password
        text = message.as_string()
        session.sendmail(sender_email, recipient_email, text)
        session.quit()

        print('Mail Sent')
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

@app.route('/send_email', methods=['POST'])
def send_email_route():
    message = request.form['message']
    if message:
        try:
            send_email("New Message from Flask App", message)
            return render_template_string('''<div class="container">
                                                <div class="alert alert-success" role="alert">
                                                    Your message was sent successfully.
                                                </div>
                                                <a href="/" class="btn btn-primary mt-2">Back to Home</a>
                                            </div>''')
        except Exception as e:
            return render_template_string(f'''<div class="container">
                                                <div class="alert alert-danger" role="alert">
                                                    Failed to send message. Error: {str(e)}
                                                </div>
                                                <a href="/" class="btn btn-primary mt-2">Back to Home</a>
                                            </div>''')
    else:
        return redirect('/')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        app.logger.error("No file part in the request")
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        app.logger.error("No selected file")
        return redirect(request.url)
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        app.logger.info(f"File saved to {filepath}")

        try:
            s3_resource.Bucket(BUCKET_NAME).upload_file(filepath, file.filename)
            app.logger.info("File uploaded to S3")
            transcribed_key = get_api_url('MyApiGateway', 'prod', file.filename)
            app.logger.info("API URL fetched")

            transcribed_filename = transcribed_key.split('/')[-1]
            download_path = os.path.join(app.config['UPLOAD_FOLDER'], transcribed_filename)
            s3_resource.Bucket(OUTPUT_BUCKET_NAME).download_file(transcribed_key, download_path)
            app.logger.info("Transcribed file downloaded")

            return render_template_string(f'''<div class="container">
                                                <div class="alert alert-success" role="alert">
                                                    File "{file.filename}" uploaded successfully and Text is extracted successfully!!! <br>
                                                    
                                                </div>
                                                <a href="/" class="btn btn-primary mt-2">Upload Another File</a>
                                            </div>''')
        except Exception as e:
            return render_template_string(f'''<div class="container">
                                                <div class="alert alert-success" role="alert">
                                                    File "{file.filename}" uploaded successfully and Text is extracted successfully!!! <br>
                                                </div>
                                                <a href="/" class="btn btn-primary mt-2">Upload Another File</a>
                                            </div>''')



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5080, debug=True)
