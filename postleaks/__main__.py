#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import requests
import sys
import math
import json
import os
from datetime import datetime
import whispers

#from postleaks.config.regex_config import _regex, _domain_to_delete

POSTMAN_HOST = "https://www.postman.com"

REQUEST_INFO_INTERESTING_DATA = ["id", "url", "method", "auth", "queryParams", "description", "name", "events", "data", "headerData"]
DEFAULT_OUTPUT_FOLDERNAME="results_"

ORANGE='\033[0;35m'
GREEN='\033[92m'
BLUE='\033[94m'
YELLOW='\033[33m'
BOLD='\033[1m'
NOCOLOR='\033[0m'

def main():
    parser = argparse.ArgumentParser(description=BOLD+'Postleaks 🚀💧'+NOCOLOR+" Search for sensitive data in Postman public library.")
    parser.add_argument('-k', type=str, required=True, dest='keyword', help = "Keyword (Domain, company, etc.)")
    parser.add_argument('--extend-workspaces', action="store_true", default=False, required=False, dest='extend_workspaces', help = "Extend search to Postman workspaces linked to found requests (Warning: request consuming and risk of false positive)")
    parser.add_argument('--include', type=str, required=False, dest='include', help = "URL should match this string")
    parser.add_argument('--exclude', type=str, required=False, dest='exclude', help = "URL should not match this string")
    parser.add_argument('--raw', action="store_true", default=False, required=False, dest='raw', help = "Display raw filtered results as JSON")
    parser.add_argument('--output', type=str, required=False, dest='output', help = "Store JSON in specific output folder (Default: results_<TIMESTAMP>)")
    args = parser.parse_args()

    output_folder = ""
    if args.output and len(args.output.strip()) >0:
        output_folder = args.output
    else:
        timestamp = datetime.now().timestamp()
        timestamp_str = str(int(timestamp))
        output_folder = DEFAULT_OUTPUT_FOLDERNAME + timestamp_str;

    request_infos = search(args.keyword, args.include, args.exclude, args.extend_workspaces, args.raw, output_folder)
    print(BLUE+"\n[*] "+str(len(request_infos))+" results founds. Happy (ethical) hacking!"+NOCOLOR)
    
def search(keyword: str, include_match:str, exclude_match:str, extend_workspaces: bool, raw: bool, output: str):
 
    print(BLUE+"[*] Looking for data in Postman.com")
    ids = search_requests_ids(keyword)

    request_ids = set()
    workspaces_ids = set()

    for i in ids:
        key = next(iter(i.keys()))
        request_ids.add(key)
        
        if extend_workspaces:
            current_workspaces_ids = i.get(key)
            for w in current_workspaces_ids:
                workspaces_ids.add(w)

    if extend_workspaces:
        new_request_ids = search_request_ids_for_workspaces_id(workspaces_ids)
        request_ids = request_ids.union(new_request_ids)

    return search_request_info_for_request_ids(request_ids, include_match, exclude_match, raw, output)

def display(request_info:any, raw:bool):
    if raw:
        print(GREEN+str(request_info)+NOCOLOR)
    else:
        print(GREEN+"[+] (ID:" + request_info["id"] + ") "+ request_info["method"] +": "+BOLD+repr(request_info["url"]) + NOCOLOR, end = '')
        print(YELLOW, end='')
        if request_info["auth"] is not None:
            print("\n - Authentication items: " + repr(request_info["auth"]), end='')
        
        if request_info["headerData"] is not None and len(request_info["headerData"]) != 0:
            print("\n - Headers: ", end='')
            for d in request_info["headerData"]:
                print("[" + d["key"] + "=" + repr(d["value"]) + "]", end='')

        if request_info["data"] is not None and len(request_info["data"]) != 0:
            print("\n - Misc. data items: ", end='')
            for d in request_info["data"]:
                if "key" in d:
                    print("[" + d["key"] + "=" + repr(d["value"]) + "]", end='')
        
        if request_info["queryParams"] is not None and len(request_info["queryParams"]) != 0:
            print("\n - Query parameters: ", end='')
            for d in request_info["queryParams"]:
                print("[" + d["key"] + "=" + repr(d["value"]) + "]", end='')
    print(NOCOLOR)

def search_request_info_for_request_ids(ids: set, include_match:str, exclude_match:str, raw: bool, output: str):
    print(BLUE+"[*] Search for requests info in collection of requests"+NOCOLOR)

    os.makedirs(output)

    GET_REQUEST_ENDPOINT="/_api/request/"

    request_infos = []

    session = requests.Session()
    for id in ids:
        response = session.get(POSTMAN_HOST+GET_REQUEST_ENDPOINT+str(id))
        
        request_info = {}

        if "data" in response.json():
            data = response.json()["data"]

            try:
                for key, value in data.items():
                    if key in REQUEST_INFO_INTERESTING_DATA:
                        # URL filtering
                        if key == "url" and value is not None and len(value) > 0 and (include_match is not None or exclude_match is not None):
                            if (include_match is not None and include_match.lower() not in value.lower()):
                                raise StopIteration
                            if (exclude_match is not None and exclude_match.lower() in value.lower()):
                                raise StopIteration
                        request_info[key] = value
            except StopIteration:
                continue
            else:
                if "url" in request_info:
                    request_infos.append(request_info)
                    display(request_info, raw)
                    f = store(request_info, output)
                    identify_secrets(f)
        
    return request_infos

def identify_secrets(file_path: any):
    config_path = os.path.join(os.path.dirname(__file__), 'config.yml')
    for secret in whispers.secrets(f"-c {config_path} {file_path}"):
        secret_str = str(secret).split(']', 1)[1].strip()
        print(ORANGE+" > Potential secret found: " + secret_str + NOCOLOR)

def store(request_info: any, output: str):
    file_path = output + "/" + request_info["id"] + ".json"
    json_string = json.dumps(request_info)
    with open(file_path, 'w') as file:
        file.write(json_string)
    return file_path

def search_request_ids_for_workspaces_id(ids: set):
    print(BLUE+"[*] Looking for requests IDs in collection of workspaces"+NOCOLOR)

    LIST_COLLECTION_ENDPOINT="/_api/list/collection"

    request_ids = set()

    session = requests.Session()
    for id in ids:
        response = session.post(POSTMAN_HOST+LIST_COLLECTION_ENDPOINT+"?workspace="+str(id))
        new_request_ids = parse_search_requests_from_workspace_response(response)
        if new_request_ids is not None:
            request_ids = request_ids.union(new_request_ids)

    return request_ids

def parse_search_requests_from_workspace_response(list_collection_response):
    json = list_collection_response.json()
    if "data" in json:
        data = json["data"]
        
        request_ids = set()
        for d in data:
            requests_raw = d["requests"]
            for r in requests_raw:
                request_ids.add(r["id"])

        return request_ids

def search_requests_ids(keyword: str):
    print(BLUE+"[*] Searching for requests IDs"+NOCOLOR)

    MAX_SEARCH_RESULTS = 100
    GLOBAL_SEARCH_ENDPOINT="/_api/ws/proxy"

    session = requests.Session()
    response = session.post(POSTMAN_HOST+GLOBAL_SEARCH_ENDPOINT, json=format_search_request_body(keyword, 0, MAX_SEARCH_RESULTS))
    count = response.json()["meta"]["total"]["request"]
    
    ids = parse_search_response(response)

    if count > MAX_SEARCH_RESULTS:
        max_requests = math.trunc(count / MAX_SEARCH_RESULTS)
        for i in range(1, max_requests+1):
            offset = i*MAX_SEARCH_RESULTS
            r = session.post(POSTMAN_HOST+GLOBAL_SEARCH_ENDPOINT, json=format_search_request_body(keyword, offset, MAX_SEARCH_RESULTS))
            parsed = parse_search_response(r)
            ids.extend(parsed)
    return ids

def parse_search_response(search_response):

    json = search_response.json()
    
    if "data" not in json:
        fail("No data found")
    
    data = json["data"]

    # List composed of {"<requestId>":["workspaceId", ...]}
    ids = []
    for d in data:
        
        request_item = {}

        request_id = d["document"]["id"]
        workspaces_raw = d["document"]["workspaces"]
        workspace_ids = []
        for w in workspaces_raw:
            workspace_ids.append(w["id"])
        
        request_item[request_id] = workspace_ids

        ids.append(request_item)
        
    return ids

def format_search_request_body(keyword: str, offset: int, size: int):
    return {
        "service":"search",
        "method":"POST",
        "path":"/search-all",
        "body":{
            "queryIndices":["runtime.request"],
            "queryText": keyword,
            "size": size,
            "from": offset,
            "requestOrigin":"srp",
            "mergeEntities":"true",
            "nonNestedRequests":"true"
            }
        }

def fail(msg):
    print(RED+"[-] Error: "+msg+NOCOLOR)
    sys.exit()

if __name__ == '__main__':
    main()
