# Must import
from slips_files.common.imports import *

from slips_files.common.parsers.config_parser import ConfigParser # solves slips_config

import os

# original module imports
import json
import sys
from dataclasses import asdict

from .evaluation.ti_evaluation import *
from .model.configuration import TrustModelConfiguration
from ..fidesModule.messaging.message_handler import MessageHandler
from ..fidesModule.messaging.network_bridge import NetworkBridge
from ..fidesModule.model.configuration import load_configuration
from ..fidesModule.model.threat_intelligence import SlipsThreatIntelligence
from ..fidesModule.protocols.alert import AlertProtocol
from ..fidesModule.protocols.initial_trusl import InitialTrustProtocol
from ..fidesModule.protocols.opinion import OpinionAggregator
from ..fidesModule.protocols.peer_list import PeerListUpdateProtocol
from ..fidesModule.protocols.recommendation import RecommendationProtocol
from ..fidesModule.protocols.threat_intelligence import ThreatIntelligenceProtocol
from ..fidesModule.utils.logger import LoggerPrintCallbacks, Logger
from ..fidesModule.messaging.queueF import RedisSimplexQueue


from ..fidesModule.persistance.threat_intelligence import SlipsThreatIntelligenceDatabase
from ..fidesModule.persistance.trust import SlipsTrustDatabase
from ..fidesModule.persistance.sqlite_db import SQLiteDB

from ..fidesModule.model.configuration import load_configuration
from slips_files.core.output import Output

from pathlib import Path

# logger = Logger("SlipsFidesModule")

class FidesModule(IModule):
    # Name: short name of the module. Do not use spaces
    name = "Fides"
    description = "Trust computation module for P2P interactions."
    authors = ['David Otta', 'Lukáš Forst']

    def init(self):
        # Process.__init__(self) done by IModule
        self.__output = self.logger

        # IModule has its own logger, no set-up
        LoggerPrintCallbacks.clear()
        LoggerPrintCallbacks.append(self.print)

        # load trust model configuration
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir / "config" / "fides.conf.yml"
        self.__trust_model_config = load_configuration(config_path.__str__())


        # prepare variables for global protocols
        self.__bridge: NetworkBridge
        self.__intelligence: ThreatIntelligenceProtocol
        self.__alerts: AlertProtocol
        self.f2n = self.db.subscribe("fides2network")
        self.n2f = self.db.subscribe("network2fides")
        self.s2f = self.db.subscribe("slips2fides")
        self.f2s = self.db.subscribe("fides2slips")
        self.channels = {
            "network2fides": self.n2f,
            "fides2network": self.f2n,
            "slips2fides": self.s2f,
            "fides2slips": self.f2s,
        }

        self.sqlite = SQLiteDB(self.logger, os.path.join(os.getcwd(), 'p2p_db.sqlite'))

    def read_configuration(self) -> bool:
        """reurns true if all necessary configs are present and read"""
        conf = ConfigParser()
        self.__slips_config = conf.export_to()

    def __setup_trust_model(self):
        # create database wrappers for Slips using Redis
        # trust_db = InMemoryTrustDatabase(self.__trust_model_config)
        # ti_db =  InMemoryThreatIntelligenceDatabase()
        trust_db = SlipsTrustDatabase(self.__trust_model_config, self.db, self.sqlite)
        ti_db = SlipsThreatIntelligenceDatabase(self.__trust_model_config, self.db, self.sqlite)

        # create queues
        # TODONE: [S] check if we need to use duplex or simplex queue for communication with network module
        network_fides_queue = RedisSimplexQueue(self.db, send_channel="fides2network", received_channel="network2fides", channels=self.channels)
        # 1 # slips_fides_queue = RedisSimplexQueue(r, send_channel='fides2slips', received_channel='slips2fides')

        bridge = NetworkBridge(network_fides_queue)

        recommendations = RecommendationProtocol(self.__trust_model_config, trust_db, bridge)
        trust = InitialTrustProtocol(trust_db, self.__trust_model_config, recommendations)
        peer_list = PeerListUpdateProtocol(trust_db, bridge, recommendations, trust)
        opinion = OpinionAggregator(self.__trust_model_config, ti_db, self.__trust_model_config.ti_aggregation_strategy)

        intelligence = ThreatIntelligenceProtocol(trust_db, ti_db, bridge, self.__trust_model_config, opinion, trust,
                                                  self.__trust_model_config.interaction_evaluation_strategy,
                                                  self.__network_opinion_callback)
        alert = AlertProtocol(trust_db, bridge, trust, self.__trust_model_config, opinion,
                              self.__network_opinion_callback)

        # TODO: [S+] add on_unknown and on_error handlers if necessary
        message_handler = MessageHandler(
            on_peer_list_update=peer_list.handle_peer_list_updated,
            on_recommendation_request=recommendations.handle_recommendation_request,
            on_recommendation_response=recommendations.handle_recommendation_response,
            on_alert=alert.handle_alert,
            on_intelligence_request=intelligence.handle_intelligence_request,
            on_intelligence_response=intelligence.handle_intelligence_response,
            on_unknown=None,
            on_error=None
        )

        # bind local vars
        self.__bridge = bridge
        self.__intelligence = intelligence
        self.__alerts = alert

        # and finally execute listener
        self.__bridge.listen(message_handler, block=False)



    def __network_opinion_callback(self, ti: SlipsThreatIntelligence):
        """This is executed every time when trust model was able to create an aggregated network opinion."""
        #logger.info(f'Callback: Target: {ti.target}, Score: {ti.score}, Confidence: {ti.confidence}.')
        # TODO: [S+] document that we're sending this type
        self.db.publish("fides2slips", json.dumps(ti.to_dict()))

    # def __format_and_print(self, level: str, msg: str):
    #     # TODO: [S+] determine correct level for trust model log levels
    #     self.__output.print(f"33|{self.name}|{level} {msg}")

    def pre_main(self):
        """
        Initializations that run only once before the main() function runs in a loop
        """

        self.__setup_trust_model()
        utils.drop_root_privs()


    def main(self):
        try:
            if msg := self.get_msg("slips2fides"):
                # if there's no string data message we can continue in waiting
                if not msg['data']:# or type(msg['data']) != str:
                    return
                data = json.loads(msg['data'])

                if data['type'] == 'alert':
                    self.__alerts.dispatch_alert(target=data['target'],
                                                    confidence=data['confidence'],
                                                    score=data['score'])
                elif data['type'] == 'intelligence_request':
                    self.__intelligence.request_data(target=data['target'])
                # else:
                    # logger.warn(f"Unhandled message! {message['data']}", message)
                    

        except KeyboardInterrupt:
            # On KeyboardInterrupt, slips.py sends a stop_process msg to all modules, so continue to receive it
            return # REPLACE old continue
        except Exception as ex:
            exception_line = sys.exc_info()[2].tb_lineno

            print(exception_line)
            # logger.error(f'Problem on the run() line {exception_line}, {ex}.')
            return True