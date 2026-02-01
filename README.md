    $ touch docker.mkv
    $ docker run -ti --rm -v $PWD/docker.mkv:/app/out.mkv ghcr.io/ha5la/morze-gyakorlo:release
    $ ffplay docker.mkv
