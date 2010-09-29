#!/bin/bash
#
# shot : Screenshot uploader for Aljoscha Krettek
# Version: 0.1
# (c) by Aljoscha Krettek

# NOTE:
#       requirements:
#	- scrot
#	- xclip
#	- xdialog

#### CONFIG ####
  SERVER="http://shots.netflux.org"
  #SERVER="http://127.0.0.1:5000"
  USERNAME="aljoscha"
  PASSWORD="indra7"
  UPLOAD_SCRIPT=/home/aljoscha/.apps/upload_screenshot.py
  FILENAME="`date +%y%m%d-%H%M%S`.jpg"
  TMPPATH=/tmp
  LOGFILE=/var/log/shot
  QUALITY=100
  MODUS=2
  LOGGING=0
  LINK="$SERVER/$USERNAME/shot/%s"
  OBROWSER="google-chrome -remote $LINK"
#### FUNCTIONS ####

check() {
  if [ $? ]; then
    out 2 "$1              [ DONE ]"
  else
    out 3 "Error: $1 failed!"
    exit
  fi
}

# $1	=	[Welcome=0|Notice=1|Spam=2|Error=3]
# $2	=	Message

out() {
  case "$MODUS" in
  0) echo $2;;
  1)
    case "$1" in
    0 | 3) echo -e "\033[1;31m" $2 "\033[0m";;
    1 | 2) echo -e "\033[1;32m" $2 "\033[0m";;
    *)     echo "eh?" && exit;;
    esac
    ;;
  2)
    if [ "$1" -eq 1 ]; then
      kdialog --title shot.sh --msgbox "$2" 8 30
    elif [ "$1" -eq 3 ]; then
      kdialog --title shot.sh --error "$2" 8 30
    fi
    ;;
  *) echo "eh?" && exit;;
  esac
}

#### CODE ####
  out 0 "shot : (c) Aljoscha Krettek"
  out 0 "#################################################"


# Taking the Screenshot
  scrot $1 --quality $QUALITY $TMPPATH/$FILENAME
  check "screenshot"
# Logging
  if [ $LOGGING == "1" ]; then 
    echo "$(date +"%m.%d.%y - %H:%M:%S"): $(whoami)" >> LOGFILE
  fi
# send it to the host
  $UPLOAD_SCRIPT $SERVER/upload $TMPPATH/$FILENAME $USERNAME $PASSWORD
  check "upload"
# remove the tmp file
  rm $TMPPATH/$FILENAME 
  check "removing temp file"
# opening browser
  if [[ ! -z "$OBROWSER" ]];then
    OBROWSER=$(printf "$OBROWSER" $FILENAME)
    $OBROWSER
	LINK=$(printf "$LINK" $FILENAME)
	echo -n $LINK | xclip -i
  fi
  out 1 "shot uploaded"
