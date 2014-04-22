#!/bin/bash

# to make it simple we include the variables here instead of creating yet another file
export USE_MONGO=1
export MONGO_HOST='localhost'
export MONGO_PORT=27017
export MONGO_USER=
export MONGO_PASS=
export MONGO_DB=
export MONGO_BUCKET='rxnorm'

# TODO: add a Couchbase version

export DID_SOURCE_FOR_SETUP='did'

# run the setup script with these environment variables
python3 rxnorm_link_run.py
