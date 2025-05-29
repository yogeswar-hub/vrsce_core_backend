FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy everything except venv
COPY ./com ./com
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Add working directory to PYTHONPATH so package modules can be found
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Lambda entry point: change this to match your actual file + function
CMD ["com.dimcon.vrse_app.handlers.lambda_entry_point.lambda_handler"]