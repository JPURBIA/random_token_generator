import argparse
from app import app
from initial_cleanup import initiailize_cleanup_with_lock

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the Token Pool Management app.")
    parser.add_argument('--host', type=str, default="127.0.0.1", help="Host address to bind the application on")
    parser.add_argument('--port', type=int, default=5000, help="Port to run the application on")
    args = parser.parse_args()

    # Initialize cleaup before running the application
    initiailize_cleanup_with_lock()

    # Run the Flask app
    app.run(host=args.host, port=args.port)