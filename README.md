# MLLO Web
MLLO Web is a web application for [MLLOS](https://github.com/hakjuoh/MLLOS).

This guide is intended for developers working on the MLLO Web project.

### Prerequisites

- Node.js and npm: Ensure both are installed.
- Virtual Environment: Recommended for managing Python dependencies and isolating them from system-wide installations.
- MOBI Server version 3.0.0: Required to handle SPARQL queries in the backend. [MOBI](https://inovexcorp.github.io/mobi-docs/latest/index.html#installing_the_docker_image) 

### Setting up the project

#### Install frontend dependencies:
```
cd mllo_web/frontend/web
npm install
cd ../../..
```

#### Install/Activate virtualenv:
```
virtualenv .venv
source .venv/bin/activate
```

#### Install backend dependencies:
```
pip install -r requirements.txt
```

### Running the Application

#### Run the frontend server for development:
```
cd mllo_web/frontend/web
npm run dev
```

### Run the backend server:
```
python -m mllo_web.app.api_app
```

### Build the frontend UI for deployment:
```
cd mllo_web/frontend/web
npm run build
cd ../../..
```

This command starts the backend server for the MLLO Web application.