import subprocess


def main():
    server = subprocess.Popen(["python3", "index_server.py"])
    flask_demo = subprocess.Popen(["python3", "flask_demo.py"])

    try:
        # Wait for both subprocesses to finish
        server.communicate()
        flask_demo.communicate()
    except KeyboardInterrupt:
        # If the user presses CTRL+C, terminate both subprocesses
        server.terminate()
        flask_demo.terminate()


if __name__ == "__main__":
    main()