---
title: ShuttleStep
emoji: 🏸
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# ShuttleStep

Upload a badminton video and get data-driven feedback on your footwork. ShuttleStep uses MediaPipe pose tracking to follow the player's body, then turns that movement into stats.

## Run it on your computer

1. Install Python 3.12 or newer from https://www.python.org/downloads/ (on Windows, tick "Add python.exe to PATH").
2. Download this project (green **Code** button, then **Download ZIP**) and unzip it.
3. Double-click `start-mac.command` on a Mac or `start-windows.bat` on Windows. The first start installs everything and takes a few minutes.
4. Open http://localhost:8000 in your browser. To use it on your phone, connect the phone to the same Wi-Fi and open the address the start window shows (it looks like `http://192.168.x.x:8000`).

The pose model lives in `models/pose_landmarker_full.task` (from Google's MediaPipe model page).

## Built with

Python, Flask, MediaPipe, OpenCV, HTML and CSS.

## Turn on "Sign in with Google" (optional)

Without this, ShuttleStep still works: everyone is a guest and their videos are saved in their own browser.

1. Go to https://console.cloud.google.com, sign in, and create a project called **ShuttleStep**.
2. Open **Google Auth Platform** (search for it in the top bar) and click **Get started**. Enter the app name **ShuttleStep** and your email, choose **External**, and finish.
3. Under **Audience → Test users**, add the Gmail addresses that should be able to sign in (including your own).
4. Under **Clients**, click **Create client**, choose **Web application**, and add this under **Authorized redirect URIs**: `http://localhost:8000/auth/callback`. Click **Create**.
5. Click **Download JSON**, rename the file to `client_secret.json`, and put it in the ShuttleStep folder next to `app.py`. Never share or upload this file.
6. Restart ShuttleStep. A **Sign in with Google** button appears at the top.

Sign-in works on the laptop at http://localhost:8000. Google doesn't allow it on Wi-Fi addresses like `192.168.x.x`, so phones use ShuttleStep as a guest.
