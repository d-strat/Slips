FROM stratosphereips/slips:latest

# use bash instead of sh
SHELL ["/bin/bash", "-c"]

# Install dependencies and add Docker repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix

# Convert line endings for files in /StratosphereLinuxIPS
RUN cd /StratosphereLinuxIPS && find . -type f -exec dos2unix {} \;
RUN ./slips.py || true \
    && chmod +x /bin/sh

# Set entrypoint to bash
CMD ["bash", "-c", "while true; do sleep 1000; done"]
