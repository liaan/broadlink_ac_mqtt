FROM python:2

# set version label
LABEL maintainer="wjbeckett"

WORKDIR /usr/src/app

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
 cd /tmp && \
 git clone https://github.com/liaan/broadlink_ac_mqtt.git 
COPY /tmp/broadlink_ac_mqtt /config
COPY . .

CMD [ "python", "./config/monitor.py" ]

VOLUME /config