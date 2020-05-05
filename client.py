import os
import logging
from datetime import datetime
from datetime import timedelta

from nintendo.baas import BAASClient
from nintendo.dauth import DAuthClient
from nintendo.aauth import AAuthClient
from nintendo.switch import ProdInfo, KeySet, TicketList
from nintendo.nex import backend, authentication, matchmaking
from nintendo.games import ACNH


class Client:
    SYSTEM_VERSION = 1002  # 10.0.2

    # You can get your user id and password from
    # su/baas/<guid>.dat in save folder 8000000000000010.

    # Bytes 0x20 - 0x28 contain the user id in reversed
    # byte order, and bytes 0x28 - 0x50 contain the
    # password in plain text.

    # Alternatively, you can set up a mitm on your Switch
    # and extract them from the request to /1.0.0/login

    HOST = "g%08x-lp1.s.n.srv.nintendo.net" % ACNH.GAME_SERVER_ID
    PORT = 443

    def __init__(self, baas_user_id=None, baas_password=None):
        if baas_user_id:
            self.BAAS_USER_ID = baas_user_id
        else:
            self.BAAS_USER_ID = int(os.environ.get(
                'BAAS_USER_ID'), 16)  # 16 hex digits
        if baas_password:
            self.BAAS_PASSWORD = baas_password
        else:
            self.BAAS_PASSWORD = os.environ.get(
                'BAAS_PASSWORD')  # Should be 40 characters

        # You can dump prod.keys with Lockpick_RCM and
        # PRODINFO from hekate (decrypt it if necessary)
        self.keys = KeySet("./switch_info/prod.keys")
        self.info = ProdInfo(self.keys, "./switch_info/PRODINFO.dec")

        # Tickets can be dumped with nxdumptool.
        # You need the base ticket, not an update ticket.
        with open("./switch_info/acnh_ticket.tik", "rb") as f:
            self.ticket = f.read()

        self.tokens_timestamp = datetime.now() - timedelta(hours=25)  # expires after 24 hours
        self.login_timestamp = datetime.now() - timedelta(hours=4)  # expires after 3 hours

        self.cert = self.info.get_ssl_cert()
        self.pkey = self.info.get_ssl_key()

        self.device_token = ""
        self.app_token = ""
        self.user_id = 0
        self.id_token = ""
        self.backend = None
        self.mm = None

        self.param = matchmaking.MatchmakeSessionSearchCriteria()
        self.param.attribs = ["", "", "", "", "", ""]
        self.param.game_mode = "2"
        self.param.min_players = "1"
        self.param.max_players = "1,8"
        self.param.matchmake_system = "1"
        self.param.vacant_only = False
        self.param.exclude_locked = True
        self.param.exclude_non_host_pid = True
        self.param.selection_method = 0
        self.param.vacant_participants = 1
        self.param.exclude_user_password = True
        self.param.exclude_system_password = True
        self.param.refer_gid = 0
        self.param.codeword = ""

    def is_tokens_timestamp_valid(self) -> bool:
        return ((datetime.now() - self.tokens_timestamp) < timedelta(hours=24))

    def is_login_timestamp_valid(self) -> bool:
        return ((datetime.now() - self.login_timestamp) < timedelta(hours=3))

    def get_tokens(self):
        # Request a dauth token - valid for 24 hours
        self.tokens_timestamp = datetime.now()

        dauth = DAuthClient(self.keys)
        dauth.set_certificate(self.cert, self.pkey)
        dauth.set_system_version(self.SYSTEM_VERSION)
        response = dauth.device_token()
        self.device_token = response["device_auth_token"]

        # Request an aauth token - valid for 24 hours
        aauth = AAuthClient()
        aauth.set_system_version(self.SYSTEM_VERSION)
        response = aauth.auth_digital(
            ACNH.TITLE_ID, ACNH.TITLE_VERSION,
            self.device_token, self.ticket
        )
        self.app_token = response["application_auth_token"]
        return

    def login(self):
        # Log in on baas server - valid for 3 hours
        self.login_timestamp = datetime.now()

        baas = BAASClient()
        baas.set_system_version(self.SYSTEM_VERSION)
        baas.authenticate(self.device_token)
        response = baas.login(
            self.BAAS_USER_ID, self.BAAS_PASSWORD, self.app_token)

        self.user_id = int(response["user"]["id"], 16)
        self.id_token = response["idToken"]
        return

    def connect(self):
        # Connect to game server
        self.backend = backend.BackEndClient("switch.cfg")
        self.backend.configure(
            ACNH.ACCESS_KEY, ACNH.NEX_VERSION, ACNH.CLIENT_VERSION)
        self.backend.connect(self.HOST, self.PORT)

        # Log in on game server
        auth_info = authentication.AuthenticationInfo()
        auth_info.token = self.id_token
        auth_info.ngs_version = 4  # Switch
        auth_info.token_type = 2
        self.backend.login(str(self.user_id), auth_info=auth_info)
        self.mm = matchmaking.MatchmakeExtensionClient(
            self.backend.secure_client)
        return

    def get_sessions(self, dodo_code):
        if not self.is_tokens_timestamp_valid():
            self.get_tokens()
            self.login()
            self.connect()
        if not self.is_login_timestamp_valid():
            self.login()
            self.connect()
        self.param.codeword = dodo_code
        return self.mm.browse_matchmake_session_no_holder_no_result_range(self.param)
