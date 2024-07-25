from flask import Flask, request, redirect, render_template_string, send_from_directory
import boto3
from botocore.exceptions import ClientError
import os
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

@app.route('/')
def index():
    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet">
    <title>Enhanced File Upload to S3</title>
    <style>
        body, html { 
            height: 100%;
            margin: 0;
            font-family: 'Nunito', sans-serif;
            background: linear-gradient(#0000FF, #FFFF00, #FFA500);
            background-size: 400% 400%;
            animation: AnimationName 2s ease infinite;
        }

        @keyframes AnimationName { 
            0%{background-position:0% 50%}
            50%{background-position:100% 50%}
            100%{background-position:0% 50%}
        }

        .text-left {
            text-align: left;
        }

        .text-center {
            text-align: center;
        }

        .container { 
            background: white; 
            border-radius: 10px; 
            padding: 20px; 
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2); 
            max-width: 600px; 
            margin: 50px auto; 
            opacity: 0.95;
        }
        .btn-custom { 
            background-color: #007bff; 
            color: white; 
            border: none;
        }
        .btn-custom:hover { 
            background-color: #0056b3; 
            color: white; 
        }
        .navbar, .footer { 
            background-color: #007bff; 
            color: white; 
        }
        .footer { 
            padding: 10px 0; 
            text-align: center; 
        }
        input[type="file"] {
            cursor: pointer;
        }
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container">
        <a class="navbar-brand" href="#" style="color: black; padding-left: 100px ;text-align: 200 px left; font-weight: bold; display: block;">CSCI 5409 - CLOUD TERM ASSIGNMENT </a>
    </div>
</nav>

<div class="container">
    <h1 class="text-center mb-4" style="color: #333;">Upload an Audio File</h1>
    <form method="post" enctype="multipart/form-data" action="/upload">
        <div class="mb-3">
            <input type="file" class="form-control" id="file" name="file" required>
        </div>
        <button type="submit" class="btn btn-custom btn-block">Upload</button>
    </form>
</div>

<footer class="footer">
    <div class="container">
        <p style="color: black; font-weight: bold; display: block;">ABOUT THE AWS PROJECT: </p>
        <p style="color: black;  display: block;"> <b>1)</b> Upload the audio file </p>
        <p style="color: black;  display: block;"><b>2)</b> AWS Lambda will fetch the user submitted document from S3 Bucket</p>
        <p style="color: black;  display: block;"><b>3)</b> Post fetching the document, using AWS Transcribe, it will transcribe the audio file to text </p>
        <p style="color: black;  display: block;"><b>4)</b> The transcribed text will be stored back in another S3 bucket</p>
        <p style="color: black;  display: block;"><b>5)</b> The end user will be able to download the final transcribed text!!!</p>
    </div>
    <div class="container">
        <p style="color: black; padding-left: -100 px ; font-weight: bold; display: block;">DONE BY:<br></p>
        <p style="color: black; padding-left: 0px ;  display: block;"><b>NAME:</b> Venkata Sreenivas Prasad Kasibhatla</p>
        <p style="color: black; padding-left: 0px ; display: block;"><b>BANNED ID:</b> B00972626</p>
        <a class="navbar-brand" href="#" style="color: black; padding-left: 40px ;text-align: 200 px left; font-weight: bold; display: block;"> © 2024 File Uploader. All rights reserved.</a>
    </div>
</footer>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
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
    response = api_gateway_client.get_rest_apis()
    api_id = None
    for item in response['items']:
        if item['name'] == api_name:
            api_id = item['id']
            break

    if not api_id:
        raise Exception(f"API Gateway '{api_name}' not found.")

    api_url = f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/{stage_name}/transcribe"
    json_body = {
        "source_bucket": BUCKET_NAME,
        "source_key": filename
    }

    try:
        response = requests.post(api_url, json=json_body)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Error: Received status code {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        try:
            s3_resource.Bucket(BUCKET_NAME).upload_file(filepath, file.filename)
            response = get_api_url('MyApiGateway', 'prod', file.filename)

            transcribed_filename = 'transcribed_' + file.filename.split('.')[0] + '.json'
            download_path = os.path.join(app.config['UPLOAD_FOLDER'], transcribed_filename)
            s3_resource.Bucket(OUTPUT_BUCKET_NAME).download_file(transcribed_filename, download_path)

            return render_template_string(f'''<div class="container mt-5">
                                                <div class="alert alert-success" role="alert">
                                                    File "{file.filename}" uploaded and transcribed successfully! <br>
                                                    Download the transcribed text: <a href="/download/{transcribed_filename}" download>Download</a>
                                                </div>
                                                <a href="/" class="btn btn-primary">Upload Another File</a>
                                            </div>''')
        except ClientError as e:
            return render_template_string(f'''<div class="container mt-5">
                                                <div class="alert alert-success" role="alert">
                                                    File "{file.filename}" uploaded and transcribed successfully! <br>
                                                    Download the transcribed text: <a href="/download/{transcribed_filename}" download>Download</a>
                                                </div>
                                                <a href="/" class="btn btn-primary">Upload Another File</a>
                                            </div>''')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
