# atlassian-support-cleaner
CLI tool to clean atlassian support.zip from various data

Description
---

Even if Atlassian clears some data out when creating a Confluence support zip, there still remains plenty information (amongst others also personal information) about your system and users.

This tool is designed to clear out the base URL and Usernames (see **How it works** what this means exactly). 


Usage
--- 

**./supportcleaner** _SUPPORT_ZIP_ _BASEURL_


Example
---
```bash
./supportcleaner Confluence_support_2019-02-14-11-43-28.zip my-base-url.net
```

How it works
---

This tool does cleaning the support zip by
- extracting the zip file
- replacing:

|Search-String|Replacement|
|---|---|
|_BASEURL_|URL_CLEANED|
|userName: _NAME_WITHOUT_SPACE_|userName: USERNAME_CLEANED|

(_NAME_WITHOUT_SPACE_ matches on all not white space characters)

- creating new zip named "**cleaned.zip**"

Disclaimer
---

Please be aware, that this tool cannot garantee to cleanup all personal information or information related to your company.

License
---

MIT &copy; 2019 //SEIBERT/MEDIA GmbH