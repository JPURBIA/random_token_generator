# Random Token Generator and Manager

## Overview

This is a Flask-based application for managing a pool of tokens with Redis as the backend. The application supports generating, assigning, unblocking, deleting tokens, and keeping them alive using RESTful endpoints. An event listener is implemented to handle Redis key expiration events for proper token management.

## File Structure

```
.
|-- .env                     # Python virtual environment directory
|-- app
|   |-- app.py               # Main Flask application file
|   |-- config.py            # Application configuration file
|   |-- local_config.py      # Local configuration overrides
|   |-- event_listener.py    # Redis event listener for token expiration
|   |-- initial_cleanup.py   # Acquires a lock on Redis set to cleanup old stale tokens
|   |-- redis_client.py      # Redis client connection helper
|-- .gitignore               # Git ignore file
|-- README.md                # Documentation file (this file)
|-- requirements.txt         # Python dependencies file
```

## Components Description

### 1. `.env`

- Python virtual environment directory for isolating dependencies.
- Created by running `python -m venv .env` and activated before installing dependencies.

### 2. `app`

#### `app.py`

- Entry point for the Flask application.
- Implements RESTful endpoints for token pool management.

#### `config.py`

- Contains the application’s default configuration settings.
- Includes constants like `TOKEN_POOL_KEY`, `KEEP_ALIVE_INTERVAL`, `TOKEN_LIFETIME`, etc.

#### `local_config.py`

- Allows overriding default configuration for local development or specific environments.
- Useful for separating production and development settings.

#### `event_listener.py`

- Listens to Redis key expiration events.
- Handles expired tokens by removing them from the pool.
- Runs as a separate daemon thread.

#### `initial_cleanup.py`

- Acquires a lock over redis set, so that other instances don't repeat cleanup.
- Removes all the token which are not in the pool but might be there in the storage set.
- Every instance either runs the cleanup before startup or wait for the cleanup to complete before startup.

#### `redis_client.py`

- A utility file for creating and managing Redis client connections.
- Encapsulates Redis connection logic for reuse across the application.

### 3. `.gitignore`

- Specifies files and directories to be ignored by Git.
- Typically includes `__pycache__`, `.env`, and other unnecessary files.

### 4. `README.md`

- Documentation file providing an overview of the application, setup instructions, and file descriptions.

### 5. `requirements.txt`

- Contains a list of Python dependencies required by the application.
- Used for installing dependencies with `pip install -r requirements.txt`.

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Redis server installed and running
- Pipenv or pip for Python package management

### 2. Clone the Repository

```bash
git clone <repository_url>
cd <repository_folder>
```

### 3. Create and Activate Virtual Environment

```bash
python -m venv .env
source .env/bin/activate  # On Linux/MacOS
.env\Scripts\activate   # On Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the Flask Application

```bash
python3 app/main.py --host 0.0.0.0 --port 5000
```

### 6. Start the Event Listener

```bash
python3 app/event_listener.py
```

### 7. Access the API

- The application will be accessible at `http://127.0.0.1:5000` by default.

## API Endpoints

### Generate Tokens

**Endpoint:** `/generate`
**Method:** POST
**Description:** Generate tokens and add them to the pool.

### Assign Token

**Endpoint:** `/assign`
**Method:** POST
**Description:** Assign a token from the pool.

### Unblock Token

**Endpoint:** `/unblock`
**Method:** POST
**Description:** Unblock a previously assigned token and return it to the pool.

### Delete Token

**Endpoint:** `/delete`
**Method:** DELETE
**Description:** Delete a token from the pool or assigned list.

### Keep-Alive

**Endpoint:** `/keep-alive`
**Method:** POST
**Description:** Extend the lifetime of a token.

## Event Listener

The `event_listener.py` listens to Redis key expiration events for keys matching the pattern `pool:*` and `assign:*`. When a token expires, it ensures the token is removed from the pool or readded to the pool respectively.

## Logging

- The application uses simple `print` statements for debugging and monitoring.
- Consider integrating a logging library like `logging` for production use.

## Deployment

For deployment, you can use Gunicorn with Nginx:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Configure Nginx to proxy requests to the Gunicorn server.
