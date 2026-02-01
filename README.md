    $ docker build -tx .
    $ touch docker.mkv
    $ time docker run -ti --rm -v $PWD/docker.mkv:/app/out.mkv x
    $ ffplay docker.mkv
