FROM postgres:11-stretch


RUN apt-get update -y \
   && apt-get install -y \
    sudo \
    vim \
    curl \
    git \
    gcc \
    make \
    postgresql-server-dev-11 \
  && rm -rf /var/cache/apt/*

RUN git clone https://github.com/petere/plsh \
  && cd plsh && git checkout 9b108516a005a0592d9c9e145189825f92f820e1 \
  && make && make install

CMD ["postgres", "-c", "config_file=/etc/postgresql.conf"]
