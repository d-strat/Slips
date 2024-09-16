FROM stratosphereips/slips:latest

# use bash instead of sh
SHELL ["/bin/bash", "-c"]

# Install dependencies and add Docker repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix

# Convert line endings for files in /StratosphereLinuxIPS
RUN cd /StratosphereLinuxIPS && find . -type f -exec dos2unix {} \;

CMD ./slips.py -c ./config/slips.yaml || true && sleep 1200
