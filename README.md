
# 🏸 ShuttleStep

**ShuttleStep** is an AI-powered badminton footwork analyzer designed to turn any standard phone video into actionable footwork statistics and coaching tips. 

Built for the **2026 Congressional App Challenge** (California's 14th Congressional District).

---

## 🚀 Features

- **Body & Pose Tracking:** Uses computer vision to track player movement frame-by-frame.
- **Footwork Metrics:** Calculates total distance covered, average/top moving speed, lunge count, and recovery time.
- **Visual Analytics:** Generates movement heatmaps, speed over time graphs, and skeleton video replays.
- **Coaching Tips:** Automatically provides personalized feedback based on tracked metrics.
- **Video History:** Saves analyzed match sessions in a database for easy access.

---

## 💻 Tech Stack

- **Backend:** Python, Flask
- **Computer Vision:** OpenCV, MediaPipe
- **Database:** SQLite
- **Data Visualization:** Matplotlib
- **Frontend:** HTML, CSS

---

## 🛠️ How to Run Locally

You'll need [Python 3.12 or newer](https://www.python.org/downloads/) and [VS Code](https://code.visualstudio.com/). On Windows, tick **"Add python.exe to PATH"** when installing Python.

1. **Get the code.** Either clone the repository:
   ```bash
   git clone https://github.com/GitHUBKid-cyber/ShuttleStep.git
   ```
   or click the green **Code** button on this page, choose **Download ZIP**, and unzip it.
2. **Open it in VS Code.** Go to **File → Open Folder…** and pick the `ShuttleStep` folder.
3. **Open a terminal in VS Code** with **Terminal → New Terminal**.
4. **Start ShuttleStep** by typing one of these and pressing Enter:
   - Mac: `./start-mac.command`
   - Windows: `.\start-windows.bat`

   The first start installs everything ShuttleStep needs, which takes a few minutes.
5. **Open the website** at [http://localhost:8000](http://localhost:8000) in your browser. To use it on your phone, connect the phone to the same Wi-Fi and open the address shown in the terminal (it looks like `http://192.168.x.x:8000`).
6. **To stop ShuttleStep**, click in the terminal and press **Ctrl + C**.

> **Note:** Don't use VS Code's "Go Live" button. It only shows the HTML pages and doesn't run the Python code that analyzes videos.
