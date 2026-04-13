build:
	cd ./daemon && go build
	-mkdir scripts
	mv ./daemon/user ./scripts/entrypoint
	sudo docker build . -t coderneo17/user-terminal
build-file: build
	sudo docker save coderneo17/user-terminal -o user-terminal-node.tar.gz
clean:
	rm ./scripts/entrypoint
