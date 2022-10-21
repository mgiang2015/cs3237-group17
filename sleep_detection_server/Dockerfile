# Tells code to run python 3
FROM python:3.7

# Install cv2 dependencies because docker doesn't for some reason
RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

# Install all needed dependencies
RUN pip install flask Pillow numpy opencv-python kaggle tensorflow gunicorn

# Copy necessary files to work directory
COPY src/ /app
WORKDIR /app

# Set PORT
ENV PORT 8080

# Run server
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app