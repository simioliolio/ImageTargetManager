import httplib
import hashlib
import mimetypes
import hmac
import base64
import requests, json
from email.utils import formatdate
from os import listdir
import sys
from os.path import isfile, join, splitext, basename

# The hostname of the Cloud Recognition Web API
CLOUD_RECO_API_ENDPOINT = 'cloudreco.vuforia.com'
TARGET_MANAGEMENT_API_ENDPOINT = 'vws.vuforia.com'
FULL_TARGET_MANAGEMENT_API_ENDPOINT = 'https://vws.vuforia.com'

def compute_md5_hex(data):
    """Return the hex MD5 of the data"""
    h = hashlib.md5()
    h.update(data)
    return h.hexdigest()


def compute_hmac_base64(key, data):
    """Return the Base64 encoded HMAC-SHA1 using the provide key"""
    h = hmac.new(key, None, hashlib.sha1)
    h.update(data)
    return base64.b64encode(h.digest())


def authorization_header_for_request(access_key, secret_key, method, content, content_type, date, request_path):
    """Return the value of the Authorization header for the request parameters"""
    components_to_sign = list()
    components_to_sign.append(method)
    components_to_sign.append(str(compute_md5_hex(content)))
    components_to_sign.append(str(content_type))
    components_to_sign.append(str(date))
    components_to_sign.append(str(request_path))
    string_to_sign = "\n".join(components_to_sign)
    signature = compute_hmac_base64(secret_key, string_to_sign)
    auth_header = "VWS %s:%s" % (access_key, signature)
    return auth_header

def get_all_targets(access_key, secret_key):
    http_method = 'GET'
    content_type_bare = 'application/json'
    date = formatdate(None, localtime=False, usegmt=True)
    path = '/targets'
    request_body = ""
    auth_header = authorization_header_for_request(access_key, secret_key, http_method, request_body, content_type_bare, date, path)
    request_headers = {
        'Accept': 'application/json',
        'Authorization': auth_header,
        'Content-Type': 'application/json',
        'Date': date
    }
    url = FULL_TARGET_MANAGEMENT_API_ENDPOINT + path
    r = requests.get(url, headers=request_headers)
    return r

def delete_target(access_key, secret_key, target_id):
    http_method = 'DELETE'
    content_type_bare = 'application/json'
    date = formatdate(None, localtime=False, usegmt=True)
    path = '/targets/' + target_id
    request_body = ""
    auth_header = authorization_header_for_request(access_key, secret_key, http_method, request_body, content_type_bare, date, path)
    request_headers = {
        'Accept': 'application/json',
        'Authorization': auth_header,
        'Content-Type': 'application/json',
        'Date': date
    }
    url = FULL_TARGET_MANAGEMENT_API_ENDPOINT + path
    r = requests.delete(url, headers=request_headers)
    return r

def add_target_to_cloud_database(access_key, secret_key, absoluteImagePath):

    baseFileName = basename(absoluteImagePath)
    filenameWithoutExtension = splitext(baseFileName)[0]

    http_method = 'POST'
    content_type_bare = 'application/json'
    date = formatdate(None, localtime=False, usegmt=True)
    path = '/targets'
    base64String = ""
    with open(absoluteImagePath, "rb") as image_file:
        base64String = base64.b64encode(image_file.read())

    if base64String == "":
        print filename + "did not base64 encode"
        return

    # body json
    jsonDict = {
        "name": filenameWithoutExtension,
        "width": 100.0,
        "image": base64String
    }

    jsondata = json.dumps(jsonDict)
    request_body = jsondata.encode('utf-8')

    auth_header = authorization_header_for_request(access_key, secret_key, http_method, request_body, content_type_bare,
                                                   date, path)
    request_headers = {
        'Accept': 'application/json',
        'Authorization': auth_header,
        'Content-Type': 'application/json',
        'Date': date
    }


    # url = FULL_TARGET_MANAGEMENT_API_ENDPOINT + path
    # r = requests.post(url, data=request_body, headers=request_headers)
    # return r.status_code, r.content

    # Make the request over HTTPS on port 443
    http = httplib.HTTPSConnection(TARGET_MANAGEMENT_API_ENDPOINT, 443)
    http.request(http_method, path, request_body, request_headers)

    response = http.getresponse()
    response_body = response.read()
    return response.status, response_body


if __name__ == '__main__':
    print("go")
    import argparse
    parser = argparse.ArgumentParser(description='Query image')
    parser.add_argument('--access-key', required=True, type=str, help='The access key for the Cloud database')
    parser.add_argument('--secret-key', required=True, type=str, help='The secret key for the Cloud database')
    parser.add_argument('--mode', required=True, choices=['delete-all', 'add-folder'], type=str, help='The mode, either "delete-all", or "add-folder".')
    # parser.add_argument('--max-num-results', required=False, type=int,
    #                     default=10, help='The maximum number of matched targets to be returned')
    # parser.add_argument('--include-target-data', type=str, required=False,
    #                     default='top', choices=['top', 'none', 'all'],
    #                     help='Specified for which results the target metadata is included in the response')
    parser.add_argument('path', nargs=1, type=str, help='Path containing .jpg files')
    args = parser.parse_args()

    # status, query_response = send_target_query(access_key=args.access_key,
    #                          secret_key=args.secret_key,
    #                          max_num_results=str(args.max_num_results),
    #                          include_target_data=args.include_target_data,
    #                          image=args.image[0])
    print(args.mode)
    if args.mode == 'delete-all':
        # get all targets
        response = get_all_targets(args.access_key, args.secret_key)
        if response.status_code != 200:
            print("error getting targets. status: " + response.status_code + ". reponse: " + response.content)
            sys.exit(1)
        response_json = response.json()
        target_ids = response_json['results']
        print("all target ids:")
        print(target_ids)
        for target_id in target_ids:
            del_response = delete_target(args.access_key, args.secret_key, target_id)
            if del_response.status_code != 200:
                print("error getting targets. status: " + del_response.status_code + ". reponse: " + del_response.content)
                sys.exit(1)
            print("successful delete request. response: " + del_response.content)
            continue



    if args.mode == 'add-folder':
        print("args.mode == add-folder")
        imagesPath = ""
        imagesPath = args.path[0]
        if imagesPath == "":
            print("error: no path specified")
            sys.exit(0)

        files = [f for f in listdir(imagesPath) if isfile(join(imagesPath, f))]
        print("found files!...")
        print(files)
        for filename in files:
            filenameWithoutExtension = splitext(filename)[0]
            fileExtension = splitext(filename)[1]

            # must have jpg extension
            if fileExtension != ".jpg":
                print filename + "not processed, must have .jpg extension"
                continue

            absolutePathOfImage = imagesPath + "/" + filename
            print("adding " + absolutePathOfImage)
            status, query_response = add_target_to_cloud_database(args.access_key, args.secret_key, absolutePathOfImage)
            if status == 200 or 201:
                print(filename + ": " + query_response)
                continue
            else:
                print("error uploading " + filename + ". status: " + status + " response: " + query_response)
                continue


    # status, query_response = add_target_to_cloud_database(access_key=args.access_key,
    #     secret_key=args.secret_key, 
    #     absoluteImagePath=args.image[0])
    # if status == 200:
    #     print query_response
    #     sys.exit(0)
    # else:
    #     print status
    #     print query_response
    #     sys.exit(status)
