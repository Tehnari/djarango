#!/bin/sh

# if there is anything in django_tests, delete everything except the .gitkeep file and the settings folder
if [ "$(ls -A django_tests)" ]; then
  printf "Cleaning up django_tests\n"
  find django_tests -type f ! -name '.gitignore' -delete
fi

# if there is anything in .temp_django, delete the folder
if [ -d ".temp_django" ]; then
  printf "Removing old .temp_django\n"
  rm -rf .temp_django
fi

printf "Cloning Django 4.1.4 source code to .temp_django\n"
git clone --single-branch -b stable/4.1.x --depth 1 https://github.com/django/django.git .temp_django

printf "Resetting to 4.1.4\n"
cd .temp_django || exit
# Django 4.1.4 commit hash
git reset --hard 2ff479f50c6266762f324c03bca4ff044c24934b

printf "Removing .git folder"
rm -rf .git

printf "Renaming requests folder to requests_test"
mv tests/requests tests/requests_test
cd ..

printf "Copying tests folder to django_tests\n"
cp -r .temp_django/tests/* django_tests

printf "Removing .temp_django\n"
rm -rf .temp_django

printf "Copying settings to django_tests\n"
cp ./settings/* django_tests

printf "Building container\n"
docker-compose -f docker-compose.yml build djarango-test