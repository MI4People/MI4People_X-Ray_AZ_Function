import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings
import requests
import logging
import uuid
import os

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
logger = logging.getLogger(__name__)


@app.route(route="model_req")
def model_req(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logger.info(f"Request Received: {context.invocation_id}")
    image = req.files["image"]
    if not image:
        return func.HttpResponse(status_code=400, body="Please provide an image file")
    try:
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        blob_service_client = BlobServiceClient(
            account_url=f"https://{account_name}.blob.core.windows.net/",
            credential=os.getenv("AZURE_STORAGE_ACCESS_KEY")
        )
        container_client = blob_service_client.get_container_client(
            os.getenv("AZURE_STORAGE_CONTAINER_NAME")
        )
        image_uuid = uuid.uuid4()
        blob_client = container_client.get_blob_client(f"{image_uuid}")
        content_settings = ContentSettings(content_type="image/png")
        blob_client.upload_blob(image, content_settings=content_settings, overwrite=True)
        logger.info(f"Request: {context.invocation_id}; Image Uploaded: {image_uuid}")
        # Set request timeout to 15 seconds
        response = requests.post(
            url=os.getenv("MODEL_ENDPOINT"),
            json={"image_uuid": str(image_uuid)},
            headers={
                "Authorization": f"Bearer {os.getenv('MODEL_AUTH_KEY')}",
                "Content-Type": "application/json",
            }
        )
        if response.status_code != 200:
            logger.error(
                f"Request: {context.invocation_id}; Error: {response.text}"
            )
            return func.HttpResponse(
                status_code=500, body="Internal Server Error"
            )
        blob_service_client.close()
        return func.HttpResponse(
            status_code=200, body=response.json()
        )
    except Exception as e:
        logger.error(f"Request: {context.invocation_id}; Error: {e}")
        return func.HttpResponse(status_code=500, body="Internal Server Error")
