#
# creation.py
#
# Adrian Garcia, December 2022
#
import sys

from arango import DatabaseCreateError
from django.db.backends.base.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):
    def _quote_name(self, name):
        return self.connection.ops.quote_name(name)

    def _get_database_create_suffix(self, template):
        # Pretty sure we don't need this.
        pass

    def _database_exists(self, cursor, database_name):
        return cursor._conn.has_database(database_name)

    def _execute_create_test_db(self, cursor, parameters, keepdb=False):
        try:
            if keepdb and self._database_exists(cursor, parameters["dbname"]):
                # If the database should be kept and it already exists, don't
                # try to create a new one.
                return
            else:
                cursor._conn.create_database(parameters["dbname"])
        except DatabaseCreateError as e:
            if '[ERR 1207]' not in getattr(e, "message", ""):
                # All errors except "database already exists" cancel tests.
                self.log("Got an error creating the test database: %s" % e)
                sys.exit(2)
            elif not keepdb:
                # If the database should be kept, ignore "database already
                # exists".
                raise

    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        """
        Internal implementation - create the test db tables.
        """
        test_database_name = self._get_test_db_name()
        test_db_params = {
            "dbname": self.connection.ops.quote_name(test_database_name),
            "suffix": self.sql_table_creation_suffix(),
        }
        # Create the test database and connect to it.
        with self._nodb_cursor() as cursor:
            try:
                self._execute_create_test_db(cursor, test_db_params, keepdb)
            except Exception as e:
                # if we want to keep the db, then no need to do any of the below,
                # just return and skip it all.
                if keepdb:
                    return test_database_name

                self.log("Got an error creating the test database: %s" % e)
                if not autoclobber:
                    confirm = input(
                        "Type 'yes' if you would like to try deleting the test "
                        "database '%s', or 'no' to cancel: " % test_database_name
                    )
                if autoclobber or confirm == "yes":
                    try:
                        if verbosity >= 1:
                            self.log(
                                "Destroying old test database for alias %s..."
                                % (
                                    self._get_database_display_str(
                                        verbosity, test_database_name
                                    ),
                                )
                            )
                        cursor._conn.delete_database(test_db_params["dbname"])
                        self._execute_create_test_db(cursor, test_db_params, keepdb)
                    except Exception as e:
                        self.log("Got an error recreating the test database: %s" % e)
                        sys.exit(2)
                else:
                    self.log("Tests cancelled.")
                    sys.exit(1)

        return test_database_name

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        # CREATE DATABASE ... WITH TEMPLATE ... requires closing connections
        # to the template database.
        self.connection.close()

        source_database_name = self.connection.settings_dict["NAME"]
        target_database_name = self.get_test_db_clone_settings(suffix)["NAME"]
        test_db_params = {
            "dbname": self._quote_name(target_database_name),
            "suffix": self._get_database_create_suffix(template=source_database_name),
        }
        with self._nodb_cursor() as cursor:
            try:
                self._execute_create_test_db(cursor, test_db_params, keepdb)
            except Exception:
                try:
                    if verbosity >= 1:
                        self.log(
                            "Destroying old test database for alias %s..."
                            % (
                                self._get_database_display_str(
                                    verbosity, target_database_name
                                ),
                            )
                        )
                    cursor._conn.delete_database(test_db_params["dbname"])
                    self._execute_create_test_db(cursor, test_db_params, keepdb)
                except Exception as e:
                    self.log("Got an error cloning the test database: %s" % e)
                    sys.exit(1)

# creation.py
