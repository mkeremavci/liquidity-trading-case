#! /bin/bash
# © 2025 kerem.ai · All rights reserved.

# Get the projects root directory (absolute path)
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# Append the project root to the PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Function to run main.py
run_experiment() { 
    # Run the main.py script
    python $SCRIPT_DIR/main.py --strategy "$1" \
        --filepath "$2" \
        --latency "$3" \
        --order-cost "$4" \
        --initial-money "$5" \
        --initial-stock "$6" \
        --options "${@:7}" 
}

# Run the dummy agent to obtain Limit-Order-Book
STRAGEGY="dummy"
FILEPATH="$PROJECT_ROOT/data/AKBNK.E.csv"
LATENCY=0.0
ORDER_COST=0.0
INITIAL_MONEY=10000.0
INITIAL_STOCK=0
OPTIONS=()

run_experiment $STRAGEGY $FILEPATH $LATENCY $ORDER_COST $INITIAL_MONEY $INITIAL_STOCK "${OPTIONS[@]}"

# Run the basic-ewma agent with different options
STRAGEGY="basic-ewma"
FILEPATH="$PROJECT_ROOT/data/AKBNK.E.csv"
LATENCY=0.0
ORDER_COST=0.0
INITIAL_MONEY=10000.0
INITIAL_STOCK=0
OPTIONS=(
    "beta=0.9"
    "margin=0.0"
    "wait_time=15.0"
    "pricing=aggressive"
    "fixed_quantity=None"
    "proportional_quantity=0.20"
)

run_experiment $STRAGEGY $FILEPATH $LATENCY $ORDER_COST $INITIAL_MONEY $INITIAL_STOCK "${OPTIONS[@]}"
