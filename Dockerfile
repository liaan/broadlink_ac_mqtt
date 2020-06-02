FROM lsiobase/ubuntu:bionic

# set version label
LABEL maintainer="wjbeckett"

# environment settings
ENV HOME="/config" \
PYTHONIOENCODING=utf-8

RUN \
 echo "***** install python utils ****" && \
 apt-get update && \
 apt-get install -y \
    git \
    python \
	python-pip \
	python3-pip \
	python3 \
 pip install --no-cache-dir \
	paho-mqtt && \
 pip3 install --no-cache-dir \
    paho-mqtt
RUN \
 echo "**** Grab latest version ****" && \
 git clone "https://github.com/liaan/broadlink_ac_mqtt.git" /config
RUN \
 echo "**** cleanup ****" && \
 apt-get purge --auto-remove -y \
	python-pip \
	python3-pip && \
 apt-get clean && \
 rm -rf \
	/tmp/* \
	/var/lib/apt/lists/* \
	/var/tmp/*
# ports and volumes
# EXPOSE 8080
VOLUME /config
