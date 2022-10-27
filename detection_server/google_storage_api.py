import io
import zipfile
import os
from google.cloud import storage
    
CLOUD_STORAGE_BUCKET = os.environ['CLOUD_STORAGE_BUCKET']

def download_blob(bucket_name, source_blob_name, destination_file_name):
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Downloaded storage object {} from bucket {} to local file {}.".format(
            source_blob_name, bucket_name, destination_file_name
        )
    )

def download_zip_and_unzip(bucket_name, source_blob_name, destination_folder_name):
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    object_bytes = blob.download_as_bytes()

    zip_archive = zipfile.ZipFile(io.BytesIO(object_bytes))
    zip_archive.extractall(destination_folder_name)
    zip_archive.close()

    print(
        "Downloaded zip object {} from bucket {} and unzipped to {}".format(
            source_blob_name, bucket_name, destination_folder_name
        )
    )
