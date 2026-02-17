# How to Host this App on PythonAnywhere

This guide explains how to host the MMData Web Sync Tool on [PythonAnywhere](https://www.pythonanywhere.com/).

Since the application is primarily a client-side web app (HTML/JS/CSS), we use a small Flask wrapper (`flask_app.py`) to serve these files.

## Prerequisites

*   A PythonAnywhere account (the free "Beginner" tier is sufficient).

## Step 1: Upload Your Code

1.  Log in to your PythonAnywhere dashboard.
2.  Go to the **Files** tab.
3.  Create a new directory for your project, for example: `mmdata_web`.
4.  Upload the following files into this directory:
    *   `flask_app.py` (This serves the app)
    *   `web_app/` (You need to create this folder and upload the contents inside it)
        *   `web_app/index.html`
        *   `web_app/style.css`
        *   `web_app/main.js`
    *   *Note:* PythonAnywhere's web interface allows uploading files one by one. For easier uploading, you can zip the `web_app` folder, upload the zip, and use the **Bash Console** to unzip it (`unzip web_app.zip`).

Your file structure on PythonAnywhere should look like this:
```
/home/yourusername/mmdata_web/
    flask_app.py
    web_app/
        index.html
        main.js
        style.css
```

## Step 2: Set Up the Web App

1.  Go to the **Web** tab.
2.  Click **Add a new web app**.
3.  Click **Next**.
4.  Select **Flask**.
5.  Select **Python 3.x** (e.g., 3.9 or newer).
6.  **Path:** It will ask for the path to your flask app. You can leave the default for now (e.g., `/home/yourusername/mysite/flask_app.py`) because we will edit the configuration file manually in the next step.
7.  Click **Next** to create the app.

## Step 3: Configure the WSGI File

1.  On the **Web** tab, scroll down to the **Code** section.
2.  Click on the link next to **WSGI configuration file** (it looks like `/var/www/yourusername_pythonanywhere_com_wsgi.py`).
3.  Delete the default content and replace it with the following code. **Make sure to replace `yourusername` and `mmdata_web` with your actual username and folder name.**

```python
import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yourusername/mmdata_web'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import the flask app
from flask_app import app as application
```

4.  Click **Save**.

## Step 4: Reload and Visit

1.  Go back to the **Web** tab.
2.  Click the big green **Reload** button at the top.
3.  Click the link to your site (e.g., `https://yourusername.pythonanywhere.com`).
4.  You should see the MMData Sync Tool loaded.

## Important Note on Browser Security

Because this application runs in the browser and accesses local files on your computer:
*   **"Open Directory"**: This feature uses the modern *File System Access API*. It works best in Chrome, Edge, and Opera.
*   **Security Context**: Some browsers restrict these APIs if the site is not served over HTTPS. PythonAnywhere provides HTTPS by default for your web app, so this should work fine.
