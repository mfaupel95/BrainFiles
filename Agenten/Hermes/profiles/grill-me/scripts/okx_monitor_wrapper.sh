#!/bin/bash
# Load environment variables from .env file if they are not already set
if [ -f "../.env" ]; then
  export $(grep -v '^#' ../.env | xargs)
fi
/c/Users/faupe/Documents/BrainFiles/Agenten/Hermes/installs/bf59c98340a908a8/environments/b84713cbd02542089090760cbc7696ae/venv/Scripts/python "$(dirname "$0")/okx_monitor.py"
