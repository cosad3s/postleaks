# Postleaks

![](assets/postleaks-50.png)

## Description

[Postman](https://www.postman.com/home) is an awesome platform to build and use APIs, used by millions developers.  
It proposes also public API assets built by them which can contains custom endpoints and data. Unfortunately, these items can leak sensitive data about private websites and companies.  
This script is aimed to search for these pieces of information in Postman public library.

## Usage

```bash
❯ python3 ./postleaks.py -h
usage: postleaks.py [-h] -k KEYWORD [--extend-workspaces] [--include INCLUDE] [--exclude EXCLUDE] [--raw]

Postleaks

options:
  -h, --help           show this help message and exit
  -k KEYWORD           Keyword (Domain, company, etc.)
  --extend-workspaces  Extend search to Postman workspaces linked to found requests (Warning: request consuming and risk of false positive)
  --include INCLUDE    URL should match this string
  --exclude EXCLUDE    URL should not match this string
  --raw                Display raw filtered results as JSON
```

## Example

![](assets/example.png)
