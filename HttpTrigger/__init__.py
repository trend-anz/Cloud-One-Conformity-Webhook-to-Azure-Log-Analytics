import logging
import json
import requests
import datetime
import hashlib
import hmac
import base64
import os
import azure.functions as func

customer_id = os.environ["azcustomerid"]
shared_key = os.environ["azsharedkey"]
log_type = os.environ.get("azlogtype", "TMConformity")


def build_signature(
    customer_id, shared_key, date, content_length, method, content_type, resource
):
    x_headers = "x-ms-date:" + date
    string_to_hash = (
        method
        + "\n"
        + str(content_length)
        + "\n"
        + content_type
        + "\n"
        + x_headers
        + "\n"
        + resource
    )
    bytes_to_hash = bytes(string_to_hash, encoding="utf-8")
    decoded_key = base64.b64decode(shared_key)
    encoded_hash = base64.b64encode(
        hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()
    ).decode()
    authorization = "SharedKey {}:{}".format(customer_id, encoded_hash)
    return authorization


def post_data(customer_id, shared_key, body, log_type):
    method = "POST"
    content_type = "application/json"
    resource = "/api/logs"
    rfc1123date = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    content_length = len(body)
    signature = build_signature(
        customer_id,
        shared_key,
        rfc1123date,
        content_length,
        method,
        content_type,
        resource,
    )
    uri = (
        "https://"
        + customer_id
        + ".ods.opinsights.azure.com"
        + resource
        + "?api-version=2016-04-01"
    )

    headers = {
        "content-type": content_type,
        "Authorization": signature,
        "Log-Type": log_type,
        "x-ms-date": rfc1123date,
    }

    response = requests.post(uri, data=body, headers=headers)
    return response.status_code


def main(req: func.HttpRequest):
    logging.info("Python HTTP trigger function processed a request.")
    req_body = req.get_json()
    epoch = req_body["lastModifiedDate"] / 1000
    YmdHMStime = datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
    req_body["timestamp"] = YmdHMStime
    body = json.dumps(req_body)
    resp = post_data(customer_id, shared_key, body, log_type)
    return func.HttpResponse(f"Log Analytics Response: {resp}", status_code=resp)