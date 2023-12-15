FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the necessary files and modules
COPY Diets/requirements.txt .
COPY Diets/diets-service.py .
COPY Libraries/ Libraries/

# Install the dependencies
RUN pip install -r requirements.txt

# Define an argument for DIETS_PORT
ARG DIETS_PORT

# Expose the specified port
EXPOSE ${DIETS_PORT}

# Set the entry point
CMD [ "python", "diets-service.py" ]