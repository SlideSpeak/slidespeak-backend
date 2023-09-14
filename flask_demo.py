import time
from concurrent.futures import ThreadPoolExecutor
import json
import os
from multiprocessing.managers import BaseManager
from flask import Flask, request, jsonify, make_response, Response
from flask_cors import CORS
import uuid
from concurrent.futures import as_completed
from file_utils import document_preview, get_file_ext
from upload_s3 import upload_file_to_s3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.response_buffering = False
CORS(app)

# initialize manager connection
# TODO: you might want to handle the password in a less hardcoded way
manager = BaseManager(("", 5602), b"password")
manager.register("query_index")
manager.register("insert_into_index")
manager.register("get_documents_list")
manager.register("create_index")
manager.register("start_worker")
manager.register("initialize_index")

# Try to connect
for _ in range(10):
    try:
        manager.connect()
        break
    except ConnectionRefusedError:
        print("Connecting to index server has failed, waiting before retrying...")
        time.sleep(3)

executor = ThreadPoolExecutor()


@app.route("/stream")
def stream():
    query_text = request.args.get("text", None)
    request.args.get("doc_id", None)
    uuid_id = request.args.get("uuid", None)
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400

    if uuid_id is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    manager.initialize_index(uuid_id)
    queue = manager.start_worker(query_text, uuid_id)

    def generate():
        while True:
            response = (
                queue.get()
            )  # This will block until there is data available in the queue
            if response is None:  # If we get None, that means the stream is done
                break
            yield str(response)

    return Response(generate(), mimetype="text/event-stream")


# TODO: Can we delete this route?
@app.route("/query", methods=["GET"])
def query_index():
    global manager
    query_text = request.args.get("text", None)
    query_doc_id = request.args.get("doc_id", None)
    uuid_id = request.args.get("uuid", None)
    if query_text is None:
        return "No text found, please include a ?text=blah parameter in the URL", 400
    if uuid_id is None:
        return "No UUID found, please include a uuid in the URL", 400

    manager.initialize_index(uuid_id)
    response = manager.query_index(query_text, query_doc_id)._getvalue()
    response_json = {
        "text": str(response),
    }
    return make_response(jsonify(response_json)), 200


@app.route("/uploadFile", methods=["POST"])
def upload_file():
    global manager, executor
    if "file" not in request.files:
        return "Please send a POST request with a file", 400

    filepath = None
    try:
        generated_uuid = str(uuid.uuid4())
        uploaded_file = request.files["file"]
        ext = get_file_ext(uploaded_file.filename)
        filename = secure_filename(str(uuid.uuid4()) + ext)
        filepath = os.path.join("documents", os.path.basename(filename))

        start_time = time.time()
        uploaded_file.save(filepath)
        print('Saving the local PPT/DOC file: {:.2f}s'.format(time.time() - start_time))

        start_time = time.time()
        if request.form.get("filename_as_doc_id", None) is not None:
            manager.insert_into_index(filepath, doc_id=filename)
        else:
            manager.insert_into_index(filepath, generated_uuid)
        print('Inserting into llama index: {:.2f}s'.format(time.time() - start_time))
    except Exception as e:
        print(e)
        # cleanup temp file
        if filepath is not None and os.path.exists(filepath):
            os.remove(filepath)
        return "Error: {}".format(str(e)), 500

    # upload file to s3
    start_time = time.time()
    upload_done = executor.submit(
        upload_file_to_s3,
        filepath,
        "slidespeak-files",
        generated_uuid + os.path.splitext(filepath)[1],
    )
    print('Upload DOC/PPT to S3: {:.2f}s'.format(time.time() - start_time))

    # delete file after upload
    upload_done.add_done_callback(
        lambda _: os.remove(filepath) if os.path.exists(filepath) else None
    )

    start_time = time.time()
    preview_file_paths = document_preview(
        filepath, "preview_images/" + generated_uuid + ".jpg"
    )
    print('Generating DOC/PPT preview: {:.2f}s'.format(time.time() - start_time))

    preview_urls_dict = {}

    if len(preview_file_paths) > 0:
        # Make a list of all futures for the uploads
        future_to_preview = {
            executor.submit(
                upload_file_to_s3,
                preview_file_path,
                "slidespeak-files",
                "preview-images/" + os.path.basename(preview_file_path)
            ): preview_file_path for preview_file_path in preview_file_paths
        }

        start_time = time.time()
        for future in as_completed(future_to_preview):
            preview_file_path = future_to_preview[future]
            try:
                preview_url = future.result()
                index = preview_file_paths.index(preview_file_path)
                preview_urls_dict[index] = preview_url

                if os.path.exists(preview_file_path):
                    os.remove(preview_file_path)
            except Exception as exc:
                print(f'{preview_file_path} generated an exception: {exc}')
        print('Uploading preview images to S3: {:.2f}s'.format(time.time() - start_time))

    # Convert dict to list in correct order
    preview_urls = [preview_urls_dict[i] for i in sorted(preview_urls_dict.keys())]

    return (
        make_response(jsonify({"uuid": generated_uuid, "previewUrls": preview_urls})),
        200,
    )


@app.route("/getDocuments", methods=["GET"])
def get_documents():
    document_list = manager.get_documents_list()._getvalue()

    return make_response(jsonify(document_list)), 200


@app.route("/")
def home():
    return "Hello, World! Welcome to the llama_index docker image!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5601)
