#!/bin/bash

# e.g.  $ ./pcie_hot_reset.sh 04:00.0

DEV=$1

if [ -z "$DEV" ]; then
    echo "Error: no device specified"
    exit 1
fi

if [ ! -e "/sys/bus/pci/devices/$DEV" ]; then
    DEV="0000:$DEV"
fi

if [ ! -e "/sys/bus/pci/devices/$DEV" ]; then
    echo "Error: device $DEV not found"
    exit 1
fi

PORT=$(basename $(dirname $(readlink "/sys/bus/pci/devices/$DEV")))

if [ ! -e "/sys/bus/pci/devices/$PORT" ]; then
    echo "Error: device $PORT not found"
    exit 1
fi


echo -e "\nRemoving $DEV"

CMD="echo 1 | sudo tee /sys/bus/pci/devices/$DEV/remove"
printf "> $CMD\n"
eval $CMD


echo -e "\nPerforming hot reset of port $PORT"

CMD="setpci -s $PORT BRIDGE_CONTROL"
printf "> $CMD\n"
BR_CTRL=$(eval $CMD)

echo "Bridge control: $BR_CTRL"

CMD="sudo setpci -s $PORT BRIDGE_CONTROL=$(printf "%04x" $((0x${BR_CTRL} | 0x40)))"
printf "> $CMD\n"
eval $CMD
sleep 0.01

CMD="sudo setpci -s $PORT BRIDGE_CONTROL=$BR_CTRL"
printf "> $CMD\n"
eval $CMD
sleep 0.5


echo -e "\nRescanning bus"

CMD="echo 1 | sudo tee /sys/bus/pci/devices/$PORT/rescan"
printf "> $CMD\n"
eval $CMD