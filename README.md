# atlassian-support-cleaner
CLI tool to clean atlassian support.zip from various data

Description
---

Even if Atlassian cleans some data out when creating a Confluence support zip, there still remains plenty information (amongst others also personal information) about your system and users.

This tool is designed to clean out the base URL and Usernames (see **How it works** what this means exactly). 

(May work with other support zip files, but is only tested for Confluence.)

Requirements
---

Python &ge; 3.5


Usage
--- 

**./supportcleaner.py** _SUPPORT_ZIP_ _BASEURL_ [--filterfile _FILTER_FILE_]

Environment
---
**MAX_TMP_DIR_SIZE**: Set maximum allowed size in bytes of temporary directory for extraction.
**DELETE_AFTER_DAYS**: Set maximum age for files, after which they should be flagged for deletion.

Example
---
```bash
./supportcleaner.py Confluence_support_2019-02-14-11-43-28.zip my-base-url.net
```

How it works
---

This tool does cleaning the support zip by
- extracting the zip file
- replacing in files (defined via LOGDIR, default: all):

|Example|Replacement|
|---|---|
|subdomain._BASEURL_|URL_CLEANED|
|userName: _NAME_WITHOUT_SPACE_|userName: USERNAME_CLEANED|
| customer@business.com | EXTERNAL_EMAIL_SHA256:b6c4586387_CLEANED|
| employee@URL_CLEANED | INTERNAL_EMAIL_SHA256:2fdc017705_CLEANED|
| *.smhss.de | SMEDIA_DOMAIN_CLEANED|
| 127.0.0.1 | 127.0.0.IP_CLEANED|
| ----- BEGIN RSA PRIVATE KEY ----- ... | PRIVATE_KEY_CLEANED|
| ----- BEGIN CERTIFICATE ----- ... | CERTIFICATE_CLEANED|
| Big Business LLC | BUSINESS_CLEANED|
| Herr Müller | NAME_CLEANED |

- remove files that are older than DELETE_AFTER_DAYS (default: 180) days (interactive)

- remove files that are within the LARGEST_PERCENT of files (default: largest 10%) (interactive)

- you can add additional filters by using the filterfile argument, which takes a filepath:
  - each line of the file is treated as one filter
  - each filter is splitted by "||" in two parts
  - first: search pattern (Python regex), second: replacement

- creating new zip named "**cleaned.zip**" (if already existing, it will be deleted at program start)

Predefined filters
---
Several filters are already defined in the filters.txt.
These can and should be modified and extended to suit your specific needs.

As is, there are filters for cleaning:

- Usernames         (in a specific format, replacement includes truncated SHA256 hash)
- Baseurl           (including subdomains)
- Mail addresses    (differentiates between internal (contains URL_CLEANED) and external. 
                     Replacement includes truncated SHA256 hash of the local part)
- smhss.de-Domains
- IP-Addresses      (only the last byte is redacted)
- Private keys and certificates     (in a specific format)
- Business names
- Personal names in addresses   (starting with 'Frau' or 'Herr')

Examples for these filters can be seen above. 
Some extended documentation is provided with the regexes in filters.txt.

Notes
---

Please be aware, that due to creating a new zip all original timestamps as well as file owners and permissions are lost.

Disclaimer
---

Please be aware, that this tool cannot guarantee to cleanup all personal information or information related to your company.

License
---

MIT &copy; 2019-2020 //SEIBERT/MEDIA GmbH
