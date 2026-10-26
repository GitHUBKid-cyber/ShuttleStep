**ShuttleStep**

ShuttleStep is an AI-powered badminton footwork analyzer designed to turn any standard phone video into tailored footwork statistics and coaching tips. It was built for the 2026 Congressional App Challenge(California's 14th Congressional District).

Features:
- Body & Pose Tracking: Uses MediaPipe and OpenCV computer vision to track player movement frame-by-frame.
- Footwork Metrics: Calculates total distance covered, average/top moving speed, lunge count, and recovery time.
- Visual Analytics: Generates movement heatmaps, speed over time graphs, and skeleton video replays.
- Coaching Tips: Automatically provides personalized feedback based on tracked metrics.
- Video History: Saves analyzed match sessions in a database for easy access.

Tech Stack:
-  Backend: Python, Flask
-  Computer Vision: OpenCV, MediaPipe
-  Database: SQLite
-  Data Visualization: Matplotlib
-  Frontend: HTML, CSS

How to Run Locally
1) Download the ShuttleStep Zip File
2) Extract the file and open it on VS Code
3) Go to the app.py file and on the terminal for VS Code, type 'python3 app.py'.
4) You will then be provided with a local host link that you can use.
