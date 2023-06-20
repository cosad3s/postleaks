#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import requests
import sys
import math

POSTMAN_HOST = "https://www.postman.com"

REQUEST_INFO_INTERESTING_DATA = ["url", "method", "auth", "queryParams", "description", "name", "events", "data", "headerData"]

RED='\033[91m'
GREEN='\033[92m'
BLUE='\033[94m'
YELLOW='\033[33m'
NOCOLOR='\033[0m'

def main():
    parser = argparse.ArgumentParser(description='Postleaks')
    parser.add_argument('-k', type=str, required=True, dest='keyword', help = "Keyword (Domain, company, etc.)")
    parser.add_argument('--extend-workspaces', action="store_true", default=False, required=False, dest='extend_workspaces', help = "Extend search to Postman workspaces linked to found requests (Warning: request consuming and risk of false positive)")
    parser.add_argument('--raw', action="store_true", default=False, required=False, dest='raw', help = "Display raw filtered results as JSON")
    args = parser.parse_args()

    search(args.keyword, args.extend_workspaces, args.raw)
    
def search(keyword: str, extend_workspaces: bool, raw: bool):
 
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

    request_infos = search_request_info_for_request_ids(request_ids)

    if raw:
        print(GREEN+str(request_infos)+NOCOLOR)
    else:
        for r in request_infos:
            if "url" in r and r["url"] is not None:
                print(GREEN+"[+] URL ("+ r["method"] +"): "+repr(r["url"]) + NOCOLOR, end = '')
                print(YELLOW, end='')
                if r["auth"] is not None:
                    print("\n - Authentication items: " + repr(r["auth"]), end='')
                
                if r["headerData"] is not None and len(r["headerData"]) != 0:
                    print("\n - Headers: ", end='')
                    for d in r["headerData"]:
                        print("[" + d["key"] + "=" + repr(d["value"]) + "]", end='')

                if r["data"] is not None and len(r["data"]) != 0:
                    print("\n - Misc. data items: ", end='')
                    for d in r["data"]:
                        if "key" in d:
                            print("[" + d["key"] + "=" + repr(d["value"]) + "]", end='')
                
                if r["queryParams"] is not None and len(r["queryParams"]) != 0:
                    print("\n - Query parameters: ", end='')
                    for d in r["queryParams"]:
                        print("[" + d["key"] + "=" + repr(d["value"]) + "]", end='')

                print(NOCOLOR)
    print(NOCOLOR)

    print(BLUE+"\n[*] "+str(len(request_infos))+" results founds. Happy (ethical) hacking!"+NOCOLOR)

def search_request_info_for_request_ids(ids: set):
    print(BLUE+"[*] Search for requests info in collection of requests"+NOCOLOR)

    GET_REQUEST_ENDPOINT="/_api/request/"

    request_infos = []

    session = requests.Session()
    for id in ids:
        response = session.get(POSTMAN_HOST+GET_REQUEST_ENDPOINT+str(id))
        
        request_info = {}

        if "data" in response.json():
            data = response.json()["data"]
            
            
            for key, value in data.items():
                if key in REQUEST_INFO_INTERESTING_DATA:
                    request_info[key] = value
        request_infos.append(request_info)
        
    return request_infos

def search_request_ids_for_workspaces_id(ids: set):
    print(BLUE+"[*] Looking for requests IDs in collection of workspaces"+NOCOLOR)

    LIST_COLLECTION_ENDPOINT="/_api/list/collection"

    request_ids = set()

    session = requests.Session()
    for id in ids:
        response = session.post(POSTMAN_HOST+LIST_COLLECTION_ENDPOINT+"?workspace="+str(id))
        request_ids = request_ids.union(parse_search_requests_from_workspace_response(response))

    return request_ids

def parse_search_requests_from_workspace_response(list_collection_response):
    json = list_collection_response.json()
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
