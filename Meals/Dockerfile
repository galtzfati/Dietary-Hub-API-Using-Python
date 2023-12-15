FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the necessary files and modules
COPY Meals/requirements.txt .
COPY Meals/meals-service.py .
COPY Libraries/ Libraries/

# Install the dependencies
RUN pip install -r requirements.txt

# Define an argument for MEALS_PORT
ARG MEALS_PORT

# Expose the specified port
EXPOSE ${MEALS_PORT}

# Set the entry point
CMD [ "python", "meals-service.py" ]