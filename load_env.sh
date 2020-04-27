#!/bin/bash
set -e
set -o pipefail


bsd() {
	export $(grep -v '^#' .env | xargs -0)
	echo "loaded environment variables for bsd"
}

gnu() {
	export $(grep -v '^#' .env | xargs -d '\n')
	echo "loaded environment variables for gnu"
}


usage() {
	echo -e "load_env.sh\\n\\tThis script loads environment variables\\n"
	echo "Usage:"
	echo "  bsd                           - OSx"
	echo "  gnu                           - Linux"
}

main() {
	if [[ ! -f ".env" ]]; then
		echo "Missing .env file"
		exit 1
	fi

	local cmd=$1

	if [[ -z "$cmd" ]]; then
		usage
		exit 1
	fi

	if [[ $cmd == "bsd" ]]; then
		bsd
	elif [[ $cmd == "gnu" ]]; then
		gnu
	else
		usage
	fi
}

main "$@"