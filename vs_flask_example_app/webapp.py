# Entry point for the application.
from . import app  # For application discovery by the 'flask' command.

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
