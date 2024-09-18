FROM stratosphereips/slips:latest

# use bash instead of sh
SHELL ["/bin/bash", "-c"]

# Install dependencies and add Docker repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix \
    redis-tools

# Convert line endings for files in /StratosphereLinuxIPS
RUN cd /StratosphereLinuxIPS && find . -type f -exec dos2unix {} \;

CMD ./slips.py -c ./config/slips.yaml || true
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD redis-cli ping || exit 1
