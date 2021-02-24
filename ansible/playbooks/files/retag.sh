#!/bin/bash

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

NONE_LATEST_FABRIC_IMAGES=$(docker images | grep "hyperledger/fabric" | grep -v latest | awk '{print $1":"$2}')

if [ ! "$NONE_LATEST_FABRIC_IMAGES" = "" ];then
	for IMG in $NONE_LATEST_FABRIC_IMAGES
	do
		docker tag $IMG "${IMG%:*}:latest"
	done
fi
