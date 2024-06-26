#
# client.py
#
# Timothy Graefe, Javamata LLC, Nov 2021
#

import logging
from typing import ClassVar

# Arango Python driver (python-arango) imports.
from arango import ArangoClient
from arango.database import StandardDatabase
from arango.exceptions import ArangoClientError, ArangoError, ArangoServerError, DocumentCountError, ServerConnectionError
from django.core.exceptions import ImproperlyConfigured
# Django imports
from django.db.utils import DatabaseError

debug_client = True

logger = logging.getLogger('djarango.db.backends.arangodb')


#
# Create a Database class to be used as a wrapper to the ArangoDB instance.
# TODO: This could do with a rewrite to make it more robust.
class Database(object):
    DataError: ClassVar = ArangoServerError
    OperationalError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    IntegrityError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    InternalError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    ProgrammingError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    NotSupportedError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    DatabaseError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    InterfaceError: ClassVar = Exception  # TODO: implement/map this to ArangoDB errors
    Error: ClassVar = ArangoError

    # Make this class a singleton.
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Database, cls).__new__(cls)
        return cls.instance

    # aclient gets instantiated to an ArangoClient instance.
    # ArangoClient is the python driver used to invoke the ArangoDB REST API.
    aclient: ArangoClient = None

    # adb is an ArangoClient.db() instance.
    # It represents a specific database to which the ArangoClient has connected.
    adb: StandardDatabase = None

    adb_conn_params = {}
    """These are the params used to make the adb connection."""

    # List of valid configuration keywords; used for validating settings.
    client_cfgs = ['ENGINE', 'HOST', 'PORT', 'HOSTS', 'CONN_HEALTH_CHECKS']
    client_opts = ['HOST_RESOLVER', 'HTTP_CLIENT', 'SERIALIZER', 'DESERIALIZER']
    conn_cfgs = ['NAME', 'USER', 'PASSWORD']
    conn_opts = ['ATOMIC_REQUESTS', 'AUTOCOMMIT', 'CONN_MAX_AGE', 'OPTIONS',
                 'TIME_ZONE', 'USE_TZ', 'TEST']

    # Do we need @lru_cache?
    def get_connection_params(self, settings):
        # Check that parameters in settings are valid.
        errs = {}
        for setting, val in settings.items():
            if not any([setting in self.client_cfgs,
                        setting in self.client_opts,
                        setting in self.conn_cfgs,
                        setting in self.conn_opts]):
                errs[setting] = val

        if len(errs) > 0:
            raise ImproperlyConfigured(
                "settings.DATABASES has unrecognized settings: {}".format(errs))

        # Sample parameters are given below for ArangoClient.
        """
            aclient = ArangoClient(
                hosts = 'http://127.0.0.1:8529' | [ list of hosts in cluster ],
                host_resolver = 'roundrobin' | 'random',
                http_client = user-supplied HTTP client if desired,
                serializer = user-supplied callable to serialize JSON if desired,
                deserializer = user-supplied callable to deserialize JSON if desired)
        """

        # Parse the client configuration first.
        # python-arango supports a single host, or list of hosts (cluster).
        host = settings.get('HOST')
        hosts = settings.get('HOSTS')
        port = settings.get('PORT', '8529')

        if host == '':
            host = None

        if hosts is None:
            if host is None:
                raise ImproperlyConfigured("Neither 'HOST' nor 'HOSTS' configured")
            hosts = [host]
        elif host is not None:
            raise ImproperlyConfigured(
                "Both 'HOST' : '{}' and 'HOSTS' : {} configured".format(host, hosts))

        # The connection from ArangoClient is to an HTTP endpoint, not just ip:port

        # Create a properly formated list of hosts.  There will be multiple
        # hosts (multiple HTTP endpoints) in an ArangoDB cluster.
        adbhosts = []
        for host in hosts:
            adbhosts.append('http://' + host + ':' + port)

        # Build a list of keyword options that will be used in client instantiation. Throw out None values.
        adb_kwopts = {}
        for cfg in self.client_opts:
            setting = settings.get(cfg, None)
            if setting is not None:
                adb_kwopts[cfg] = setting

        # TODO: should this be moved to connect?
        self.aclient = ArangoClient(adbhosts, **adb_kwopts)
        if self.aclient is None:
            raise ArangoClientError("ArangoClient instantiation failed")

        # The client instantiation has succeeded, now get parameters for the db.
        # The db object internally maintains a connection.
        conn_params = {}
        for cfg in self.conn_cfgs:
            if cfg == 'USER':
                conn_params['username'] = settings.get(cfg, None)
            else:
                conn_params[cfg.lower()] = settings.get(cfg, None)

        # Return the connection parameters to the caller.
        return conn_params

    def connect(self, conn_params):
        # If we already have a connection made with the same parameters, just return it.
        if self.ready() and self.adb_conn_params == conn_params:
            return self.adb

        # A call to the "db()" method of the client is used to establish the connections.
        # Only name, username, and password are provided in the config.
        """
            aclient.db(
                self,
                name: str = "javamatadb",
                username: str = "root",
                password: str = "",
                verify: bool = False,
                auth_method: str = "basic",
                superuser_token: Optional[str] = None)
        """

        if debug_client:
            conn_params['verify'] = True

        self.adb = self.aclient.db(**{k: v for k, v in conn_params.items() if v is not None})
        self.adb_conn_params = conn_params

        # ArangoClient.db() returns a StandardDatabase object.
        if self.adb is None:
            raise DatabaseError("ArangoClient instantiation failed")

        return self.adb

    def ready(self) -> bool:
        return self.aclient is not None and self.adb is not None

    def verify(self) -> bool:
        if not self.ready():
            raise DatabaseError("ArangoClient Database not ready")

        try:
            self.adb._conn.ping()
        except ServerConnectionError as err:
            raise err
        except Exception as err:
            raise ServerConnectionError(f"bad connection: {err}")

        return True

    def close(self):
        if not self.ready():
            return

        self.aclient.close()

    def create_collection(self, name):
        if not self.ready():
            logger.debug("ArangoClient: create_collection() no connection to DB")
            return

        return self.adb.create_collection(name)

    def get_collections(self):
        return self.adb.collections()

    def get_collection(self, name):
        if not self.ready():
            logger.debug("ArangoClient: get_collection() no connection to DB")
            return None

        try:
            coll = self.adb[name]
        except DocumentCountError:
            logger.debug(f"get_collection() collection not found for: {name}")
            return None

        return coll

    #       collections = self.adb.collections()
    #       idx = [ x for x in range(len(collections)) if collections[x]['name'] == name ]
    #       if len(idx) == 0:
    #           return None

    #       return collections[idx[0]]

    def get_collection_docs(self, name):
        # Fetch all records from the specified table.
        if not self.ready():
            logger.debug("ArangoClient: get_collection_docs() no connection to DB")
            return None

        try:
            coll = self.adb[name]
        except DocumentCountError:
            logger.debug(f"get_collection_docs() collection not found for: {name}")
            return None

        count = coll.count()
        logger.debug(f"get_collection_docs() returning {count} documents from: {name}")
        return coll.all()

    def delete_collection(self, name):
        if not self.ready():
            logger.debug("ArangoClient: delete_collection() no connection to DB")
            return

        self.adb.delete_collection(name)

    def delete_document(self, collection, key):
        if not self.ready():
            logger.debug("ArangoClient: delete_document() no connection to DB")
            return

        coll = self.adb[collection]
        coll.delete(key)

    def get_document(self, collection, key):
        if not self.ready():
            logger.debug("ArangoClient: get_document() no connection to DB")
            return

        coll = self.adb[collection]
        return coll.get({'_key': str(key)})

    def has_graph(self, name):
        if not self.ready():
            logger.debug("ArangoClient: has_graph() no connection to DB")
            return False
        return self.adb.has_graph(name)

    def graph(self, name):
        if not self.ready():
            logger.debug("ArangoClient: graph() no connection to DB")
            return None
        return self.adb.graph(name)

    def graphs(self):
        if not self.ready():
            logger.debug("ArangoClient: graphs() no connection to DB")
            return None
        return self.adb.graphs()

    def create_graph(self, graph_name, eds):
        # Create a graph, including a list of edge definitions.
        if not self.ready():
            logger.debug("ArangoClient: create_graph() no connection to DB")
            return None
        return self.adb.create_graph(graph_name, eds)

    def create_vertex_collection(self, name):
        # Add a vertex collection to an existing graph.
        # The vertex collection will be an orphan.
        if not self.ready():
            logger.debug("ArangoClient: create_vertex_collection() no connection to DB")
            return None
        return self.adb.create_vertex_collection(name)

    def create_edge_definition(self, graph_name, edge_name, source, target):
        # Add an edge definition to an existing graph.
        if not self.ready():
            logger.debug("ArangoClient: create_edge_definition() no connection to DB")
            return None

        try:
            g = self.graph(graph_name)
        except Exception:  # HACK: Original was DoesNotExist which, ironically, doesn't exist anywhere
            logger.debug("ArangoClient: create_edge_definition({graph_name}) graph not found")
            return None

        return g.create_edge_definition(edge_name, source, target)
