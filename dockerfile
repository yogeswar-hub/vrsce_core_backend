FROM public.ecr.aws/lambda/python:3.12

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy source code and requirements
COPY ./com ./com
COPY requirements.txt .

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path to include LAMBDA_TASK_ROOT for imports
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Define the Lambda handler function path
CMD ["com.dimcon.vrse_app.handlers.lambda_entry_point.lambda_handler"]
