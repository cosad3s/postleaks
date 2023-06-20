#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import requests
import sys
import math

POSTMAN_HOST="https://www.postman.com"

def main():
    parser = argparse.ArgumentParser(description='Postleaks')
    parser.add_argument('-k', type=str, required=True, dest='keyword', help = "Keyword (Domain, company, etc.)")
    args = parser.parse_args()

    # TODO: extend to workspaces
    # TODO: filter request_info

    search(args.keyword)
    
def search(keyword):
 
    
    

    #workspaces_id = search_workspaces_id(keyword)
    
    # mock
    #workspaces_id = set({'10e7fc57-7f03-4553-9e58-2cd120cb16c8', 'f21c2968-b83d-485e-9360-21fc4de72be3'})

    #print(search_request_ids_for_workspaces_id(workspaces_id))

    # mock
    request_ids = set({'1559645-b966328d-124f-4a05-9da1-6e8326f31aac'})
    print(search_request_info_for_request_ids(request_ids))


    return ""    



def search_request_info_for_request_ids(ids: set):
    GET_REQUEST_ENDPOINT="/_api/request/"

    request_infos = []

    session = requests.Session()
    for id in ids:
        print(POSTMAN_HOST+GET_REQUEST_ENDPOINT+str(id))
        response = session.get(POSTMAN_HOST+GET_REQUEST_ENDPOINT+str(id))
        print(response.json())
        data = response.json()["data"]
        
        request_infos.append(data)
        #request_info["url"] = data["url"]
        #request_info["method"] = data["method"]
        #request_info["auth"] = data["auth"]
        #request_info["pathVariables"] = data["pathVariables"]
        #request_info["queryParams"] = data["queryParams"]
        #request_info["headers"] = data["headers"]
        
        

    return request_infos

def search_request_ids_for_workspaces_id(ids: set):
    LIST_COLLECTION_ENDPOINT="/_api/list/collection"

    request_ids = set()

    session = requests.Session()
    for id in ids:
        response = session.post(POSTMAN_HOST+LIST_COLLECTION_ENDPOINT+"?workspace="+str(id))
        request_ids = request_ids.union(get_request_ids(response))

    return request_ids

def get_request_ids(list_collection_response):
    json = list_collection_response.json()
    data = json["data"]
    
    request_ids = set()
    for d in data:
        requests_raw = d["requests"]
        for r in requests_raw:
            request_ids.add(r["id"])

    return request_ids

def search_workspaces_id(keyword: str):
    MAX_SEARCH_RESULTS = 100
    GLOBAL_SEARCH_ENDPOINT="/_api/ws/proxy"

    workspaces_id = set()

    session = requests.Session()
    response = session.post(POSTMAN_HOST+GLOBAL_SEARCH_ENDPOINT, json=format_search_request_body(keyword, 0, MAX_SEARCH_RESULTS))
    count = response.json()["meta"]["total"]["request"]
    workspaces_id = get_workspaces_ids(response)
    
    if count > MAX_SEARCH_RESULTS:
        max_requests = math.trunc(count / MAX_SEARCH_RESULTS)
        for i in range(max_requests):
            offset = i*MAX_SEARCH_RESULTS
            r = session.post(POSTMAN_HOST+GLOBAL_SEARCH_ENDPOINT, json=format_search_request_body(keyword, offset, MAX_SEARCH_RESULTS))
            workspaces_id = workspaces_id.union(get_workspaces_ids(r))
    
    return workspaces_id

def get_workspaces_ids(search_response):
    json = search_response.json()
    data = json["data"]

    workspaces_id = set()
    for d in data:
        workspaces_raw = d["document"]["workspaces"]
        for w in workspaces_raw:
            workspaces_id.add(w["id"])
    return workspaces_id

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
    print("[-] Error: "+msg)
    sys.exit()

if __name__ == '__main__':
    main()
