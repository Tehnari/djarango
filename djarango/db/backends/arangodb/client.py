#
# client.py
#
# Timothy Graefe, Javamata LLC, Nov 2021
#

import logging

# Django imports
from django.db.backends.base.client import BaseDatabaseClient

debug_client = True

logger = logging.getLogger('djarango.db.backends.arangodb')


class DatabaseClient(BaseDatabaseClient):
    # Use arangosh as the DB client shell.
    executable_name = 'arangosh'

    @classmethod
    def runshell_db(cls, conn_params):
        # Client invocation:
        # arangosh --server.database <dbname> --server.endpoint tcp://<host>:<port> \
        #           --server.username <username> --server.password <password>
        args = [cls.executable_name]

        host = conn_params.get('host', '')
        port = conn_params.get('port', '')
        dbname = conn_params.get('database', '')
        user = conn_params.get('user', '')
        passwd = conn_params.get('password', '')

        if not host:
            host = 'localhost'
        if not port:
            port = '8529'

        endpoint = r'tcp://{}:{}'.format(host, port)
        args += ['--server.endpoint', endpoint]

        if dbname:
            args += ['--server.database', dbname]
        if user:
            args += ['--server.username', user]
        if passwd:
            args += ['--server.password', passwd]

    def runshell(self, parameters):
        DatabaseClient.runshell_db(self.adb.get_connection_params())
