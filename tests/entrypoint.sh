#!/bin/sh

# if DEBUG=1, then run $@, which is the command passed by the IDE
if [ "$DEBUG" = "1" ]
then
  echo "Starting in debug mode"
  exec "$@"
else
  cd /app/tests/django_tests || exit
  echo "Running tests"
  exec python runtests.py --noinput --settings test_arangodb
fi

