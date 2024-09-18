# Ths is a template module for you to copy and create your own slips module
# Instructions
# 1. Create a new folder on ./modules with the name of your template. Example:
#    mkdir modules/anomaly_detector
# 2. Copy this template file in that folder.
#    cp modules/template/template.py modules/anomaly_detector/anomaly_detector.py
# 3. Make it a module
#    touch modules/template/__init__.py
# 4. Change the name of the class, the module name, description and author in the variables
# 5. The file name of the python file (template.py) MUST be the same as the name of the folder (template)
# 6. The variable 'name' MUST have the public name of this module. This is used to be able to disable the module later

# Must imports
from slips_files.common.imports import *
import subprocess
import os
import signal

class Template(IModule):
    # Name: short name of the module. Do not use spaces
    name = "Fimos"
    description = "Module that starts Fides and Iris"
    authors = ["David Otta"]

    def init(self):
        # To which channels do you wnat to subscribe? When a message
        # arrives on the channel the module will wakeup
        # The options change, so the last list is on the
        # slips/core/database.py file. However common options are:
        # - new_ip
        # - tw_modified
        # - evidence_added
        # Remember to subscribe to this channel in database.py
        self.c1 = self.db.subscribe("new_ip")
        self.channels = {
            "new_ip": self.c1,
        }

        # build docker
        #subprocess.run(["docker", "build", "--tag", "'iris'", "../../iris/"])
        # start container
        #subprocess.run(["docker", "run", "--detach", "iris"])
        print("Fimos is OK init()")


    def pre_main(self):
        """
        Initializations that run only once before the main() function runs in a loop
        utils.drop_root_privs()
        """
        print("Fimos is pre_main()")
        try:
            self.fides_process = subprocess.Popen(['python3', '/StratosphereLinuxIPS/fides/slips/module.py'])
        except Exception as e:
            print(f"An error occurred: {e}")
        print("Fimos is OK pre_main()")


    def main(self):
        """Main loop function"""
        if msg := self.get_msg("new_ip"):
            # Example of printing the number of profiles in the
            # Database every second
            data = len(self.db.getProfiles())
            self.print(f"Amount of profiles: {data}", 3, 0)
    
    def shutdown_gracefully(self):
        os.kill(self.fides_process.pid, signal.SIGKILL)#SIGTERM)
        self.fides_process.wait()
        # Optionally, call the parent's (IModule) shutdown_gracefully method if needed
        super().shutdown_gracefully()
