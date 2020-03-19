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

**./supportcleaner.py** _SUPPORT_ZIP_ _BASEURL_ [--delete-oldest] [--delete-largest]

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

|Search-String|Replacement|
|---|---|
|_BASEURL_|URL_CLEANED|
|userName: _NAME_WITHOUT_SPACE_|userName: USERNAME_CLEANED|

(_NAME_WITHOUT_SPACE_ matches on all not white space characters)

- remove files that are older than DELETE_AFTER_DAYS (default: 180) days (if --delete-oldest is set)

- remove files that are within the LARGEST_PERCENT of files (default: largest 10%) (if --delete-largest is set)

- creating new zip named "**cleaned.zip**" (if already existing, it will be deleted at program start)

Notes
---

Please be aware, that due to creating a new zip all original timestamps as well as file owners and permissions are lost.

Disclaimer
---

Please be aware, that this tool cannot garantee to cleanup all personal information or information related to your company.

License
---

MIT &copy; 2019-2020 //SEIBERT/MEDIA GmbH
