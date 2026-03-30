from picamera2_webstream import FFmpegStream, create_ffmpeg_app

# This tells the streamer to use your USB camera at /dev/video0
stream = FFmpegStream(
    width=640,
    height=480,
    framerate=30,
    device='/dev/video0'  # Explicitly use your Microsoft LifeCam
).start()

app = create_ffmpeg_app(stream)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) # Serves stream on port 5000
