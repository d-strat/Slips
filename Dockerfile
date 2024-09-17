FROM stratosphereips/slips:latest

# use bash instead of sh
SHELL ["/bin/bash", "-c"]

# Install dependencies and add Docker repositories
RUN apt-get update && apt-get install -y --no-install-recommends \
    dos2unix

# Convert line endings for files in /StratosphereLinuxIPS
RUN cd /StratosphereLinuxIPS && find . -type f -exec dos2unix {} \;


COPY ./fides /StratosphereLinuxIPS/fides
WORKDIR /StratosphereLinuxIPS/fides
# Step 4: Install the dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /StratosphereLinuxIPS
CMD ./slips.py -c ./config/slips.yaml || true && sleep 1200
