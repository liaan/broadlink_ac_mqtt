FROM python:2

# set version label
LABEL maintainer="wjbeckett"

RUN mkdir /config

WORKDIR /config

RUN \
 echo "***** install python utils ****" && \
 apt-get update && \
 apt-get install -y \
    git && \
 pip install --no-cache-dir \
	paho-mqtt \
	pyyaml
RUN \
 echo "**** Grab latest version ****" && \
 git clone https://github.com/liaan/broadlink_ac_mqtt.git

COPY . .

CMD [ "python", "./config/monitor.py" ]

VOLUME /config