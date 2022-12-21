FROM python:3.11-alpine as builder

# Install g++ to build numpy and libmemcached-dev and zlib-dev to build pylibmc
RUN apk add --no-cache --upgrade g++ libmemcached-dev zlib-dev

# Copy and build the Django test requirements file
COPY ./tests/django_tests/requirements/py3.txt .
RUN pip wheel --no-cache-dir -r ./py3.txt

# Copy and build our requirements file
COPY ./tests/test_requirements.txt .
RUN pip wheel --no-cache-dir -r test_requirements.txt

# These requirements files are build seperately because the Django test requirements take **forever** to build

FROM python:3.11-alpine

# Set environment variables
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WHEELS=/wheels

# Install GeoDjango dependencies
RUN apk add --no-cache binutils geos==3.11.1-r0 gdal==3.5.3-r2 proj==9.1.0-r0

# copy wheels from builder
RUN mkdir $WHEELS
COPY --from=builder *.whl $WHEELS

# Install our requirements and the Django Test requirements
RUN pip install --no-cache-dir $WHEELS/*.whl

# copy project
COPY ./ /app

# Install Djarango from source
RUN pip install -e ./

# chmod the entrypoint script
RUN chmod 777 /app/tests/entrypoint.sh

# run entrypoint.sh
ENTRYPOINT ["/app/tests/entrypoint.sh"]
