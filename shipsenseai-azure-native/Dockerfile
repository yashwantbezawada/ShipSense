# Use the official Python image from the Docker Hub
FROM python:3.12-slim AS build-stage

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the necessary build tools, ODBC driver, curl, gnupg, and Ghostscript
RUN apt-get update && \
    apt-get install -y gcc build-essential unixodbc-dev apt-transport-https curl gnupg ghostscript && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Use the official Python image for the final stage
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install the necessary ODBC driver, curl, gnupg, and Ghostscript
RUN apt-get update && \
    apt-get install -y unixodbc curl gnupg ghostscript && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the installed dependencies and application code from the build stage
COPY --from=build-stage /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=build-stage /usr/local/bin /usr/local/bin
COPY --from=build-stage /app /app

# Expose the port the app runs on
EXPOSE 5000

# Set the environment variable for Flask
ENV FLASK_APP=app.py

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]
