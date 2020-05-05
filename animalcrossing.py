import logging

import simplejson as json
from markupsafe import escape
from flask import Flask, abort

from client import Client

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

nintendo_client = Client()


@app.route('/api/v1/verify/<dodo_code>')
def verify_dodo_code(dodo_code):
    logging.info(dodo_code.upper().strip())
    sessions = nintendo_client.get_sessions(dodo_code.upper().strip())
    if not sessions:
        logging.debug("\nNo island found for '%s'\n" %
                      dodo_code.upper().strip())
        abort(404)
    else:
        session = sessions[0]
        data = session.application_data
        logging.debug("\nFound island:")
        logging.debug("\tId: %d" % session.id)
        logging.debug("\tPlayer id: %d" % session.owner_pid)
        logging.debug("\tActive players: %s" % session.player_count)
        logging.debug("\tIsland name: %s" % data[12:32].decode("utf16"))
        logging.debug("\tPlayer name: %s" % data[40:52].decode("utf16"))

        return {
            "session_id": session.id,
            "player_id": session.owner_pid,
            "dodo_code": dodo_code,
            "active_visitors": session.player_count,
            "opened_at": session.started_time.timestamp(),
            "island_name": data[12:32].decode("utf16"),
            "player_name": data[40:52].decode("utf16"),
        }


# Disconnect from game server
# backend.close()
