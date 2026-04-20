build:
	cd ./daemon && go build
	-mkdir scripts
	mv ./daemon/satellite ./scripts/entrypoint
	sudo docker build --no-cache . -t realssd/anchor
build-file: build
	sudo docker save realssd/anchor -o anchor-node.tar.gz
clean:
	rm ./scripts/entrypoint
