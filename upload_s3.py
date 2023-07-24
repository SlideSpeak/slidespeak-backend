import os
import boto3

s3 = boto3.client("s3")


def upload_file_to_s3(file_path, bucket_name, object_name=None):
    # Create an S3 client
    s3 = boto3.client("s3")

    # Specify the S3 bucket and object name
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Upload the file to S3
    try:
        s3.upload_file(file_path, bucket_name, object_name)

        # Construct the URL
        file_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
        print("File uploaded successfully.")
        print(file_url)
        return file_url
    except Exception as e:
        print("Error uploading file:", str(e))


def delete_file_by_path(filepath):
    if filepath is not None and os.path.exists(filepath):
        os.remove(filepath)
