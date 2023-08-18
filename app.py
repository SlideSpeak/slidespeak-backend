import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from file_utils import ppt_preview
from upload_s3 import upload_file_to_s3

from index_server import DocumentManager

app = Flask(__name__)
app.response_buffering = False
CORS(app)

document_manager = DocumentManager()
# document_manager.initialize_index()


@app.route("/stream")
def stream():
    query_text = request.args.get("text", None)
    request.args.get("doc_id", None)
    uuid_id = request.args.get("uuid", None)
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400

    if uuid_id is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    document_manager.initialize_index(uuid_id)
    answer_stream = document_manager.query_stream(query_text, uuid_id)

    return Response(answer_stream, mimetype="text/event-stream")


# TODO: Can we delete this route?
@app.route("/query", methods=["GET"])
def query_index():
    query_text = request.args.get("text", None)
    query_doc_id = request.args.get("doc_id", None)
    uuid_id = request.args.get("uuid", None)
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    if uuid_id is None:
        return "No UUID found, please include a uuid in the URL", 400

    response = document_manager.query_index(query_text, query_doc_id)._getvalue()
    response_json = {
        "text": str(response),
    }
    return make_response(jsonify(response_json)), 200


@app.route("/uploadFile", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "Please send a POST request with a file", 400

    filepath = None
    try:
        generated_uuid = str(uuid.uuid4())
        uploaded_file = request.files["file"]
        filename = secure_filename(uploaded_file.filename)
        print('filename')
        print(uploaded_file)
        filepath = os.path.join("documents", os.path.basename(filename))

        if not file_path.endswith('.pptx'):
            raise ValueError("The provided file is not a .pptx file.")

        start_time = time.time()
        uploaded_file.save(filepath)
        print("Saving the local PPT file: {:.2f}s".format(time.time() - start_time))

        start_time = time.time()
        if request.form.get("filename_as_doc_id", None) is not None:
            document_manager.insert_into_index(filepath, doc_id=filename)
        else:
            document_manager.insert_into_index(filepath, generated_uuid)
        print(
            "Inserting into llama index: {:.2f}s".format(time.time() - start_time)
        )
    except Exception as e:
        print(e)
        # cleanup temp file
        if filepath is not None and os.path.exists(filepath):
            os.remove(filepath)
        return "Error: {}".format(str(e)), 500

    # upload file to s3
    start_time = time.time()
    upload_file_to_s3(
        filepath,
        "slidespeak-files",
        generated_uuid + os.path.splitext(filepath)[1],
    )
    print("Upload PPT to S3: {:.2f}s".format(time.time() - start_time))

    # delete file after upload
    if os.path.exists(filepath):
        os.remove(filepath)

    start_time = time.time()
    preview_file_paths = ppt_preview(
        filepath, "preview_images/" + generated_uuid + ".jpg"
    )
    print("Generating PPT preview: {:.2f}s".format(time.time() - start_time))

    preview_urls_dict = {}

    if len(preview_file_paths) > 0:
        # Make a list of all futures for the uploads
        for preview_file_path in preview_file_paths:
            try:
                index = preview_file_paths.index(preview_file_path)
                preview_urls_dict[index] = upload_file_to_s3(
                    preview_file_path,
                    "slidespeak-files",
                    "preview-images/" + os.path.basename(preview_file_path)
                )
                if os.path.exists(preview_file_path):
                    os.remove(preview_file_path)
            except Exception as exc:
                print(f"{preview_file_path} generated an exception: {exc}")

    # Convert dict to list in correct order
    preview_urls = [preview_urls_dict[i] for i in sorted(preview_urls_dict.keys())]

    return (
        make_response(jsonify({"uuid": generated_uuid, "previewUrls": preview_urls})),
        200,
    )


@app.route("/")
def home():
    return "Hello, World! Welcome to the llama_index docker image!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
