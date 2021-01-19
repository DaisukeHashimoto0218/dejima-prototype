import json
import psycopg2
from psycopg2.extras import DictCursor
import dejimautils
import requests
import sqlparse

class Propagation(object):
    def __init__(self, peer_name, tx_management_dict, dejima_config_dict, connection_pool):
        self.peer_name = peer_name
        self.tx_management_dict = tx_management_dict
        self.dejima_config_dict = dejima_config_dict
        self.connection_pool = connection_pool

    def on_post(self, req, resp):
        print("/propagate start")
        if req.content_length:
            body = req.bounded_stream.read()
            params = json.loads(body)

        msg = {"result": "Ack"}
        BASE_TABLE = "bt"
        current_xid = "_".join(params['xid'].split("_")[0:2])

        db_conn = self.connection_pool.getconn()
        if current_xid in self.tx_management_dict.keys():
            resp.body = json.dumps({"result": "Nak"})
            return
        self.tx_management_dict[current_xid] = {'db_conn': db_conn, 'child_peer_list': []}

        print("lock phase")
        with db_conn.cursor(cursor_factory=DictCursor) as cur:
            lock_ids = []
            delta = params['delta']
            insertion_records = delta["insertions"]
            deletion_records = delta["deletions"]
            for record in insertion_records:
                lock_ids.append(record['id'])
            for record in deletion_records:
                lock_ids.append(record['id'])
            lock_ids = set(lock_ids)

            try:
                for lock_id in lock_ids:
                    cur.execute("SELECT * FROM {}_lineage WHERE id={} FOR UPDATE NOWAIT".format(BASE_TABLE, lock_id))

                print("execution phase")
                dt, stmts = dejimautils.convert_to_sql_from_json(params['delta'])
                for stmt in stmts:
                    cur.execute(stmt)
                cur.execute("SELECT {}_propagate_updates()".format(dt))
            except Exception as e:
                print(e)
                resp.body = json.dumps({"result": "Nak"})
                return

            print("propagation phase")
            dt_list = list(self.dejima_config_dict['dejima_table'].keys())
            dt_list.remove(dt)
            for dt in dt_list:
                if self.peer_name not in self.dejima_config_dict['dejima_table'][dt]: continue
                cur.execute("SELECT {}_propagate_updates_to_{}()".format(BASE_TABLE, dt))
                cur.execute("SELECT public.{}_get_detected_update_data()".format(dt))
                delta, *_ = cur.fetchone()
                if delta != None:
                    delta = json.loads(delta)
                    target_peers = list(self.dejima_config_dict['dejima_table'][dt])
                    target_peers.remove(self.peer_name)
                    self.tx_management_dict[current_xid]["child_peer_list"].extend(target_peers)
                    result = dejimautils.prop_request(target_peers, dt, delta, current_xid, self.dejima_config_dict)
                    print("prop result: ", result)
                    if result != "Ack":
                        msg = {"result": "Nak"}
                        break

        resp.body = json.dumps(msg)
        print("/propagate finish")
        return