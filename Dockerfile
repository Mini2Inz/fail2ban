# Use lightweight imgae based on Ubuntu
FROM phusion/baseimage

# Use baseimage's init system
CMD ["/sbin/my_init"]

# Enable SSH
RUN rm -f /etc/service/sshd/down
RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

# Set random password
RUN echo "root:$(tr -dc [:alnum:] < /dev/urandom | head -c32)" | chpasswd

# Install dependencies
RUN apt-get update && \
    apt-get install --assume-yes --no-install-recommends \
        python2.7 \
        netbase \
        iptables \
        geoip-bin \
        geoip-database

# Install Fail2ban-ng
COPY . /fail2ban
RUN cd /fail2ban && python2.7 setup.py install
RUN rm -rf /fail2ban

# Set loglevel to DEBUG and dbpurgeage to 365d
RUN sed -i \
        -e 's/^loglevel = .*$/loglevel = DEBUG/' \
        -e 's/^dbpurgeage = .*$/dbpurgeage = 365d/' \
        /etc/fail2ban/fail2ban.conf

# Set list of hosts
ARG HOSTS=
# RUN sed -i "s/^sharehosts =$/sharehosts = $HOSTS/" /etc/fail2ban/fail2ban.conf
RUN for host in $HOSTS; do echo $host >> /etc/fail2ban/hosts; done

# Enable sshd jail
RUN bash -c 'echo -e "[sshd]\nenabled = true" >> /etc/fail2ban/jail.local'

# Create script to start Fail2ban-ng
RUN mkdir /etc/service/fail2ban && \
    bash -c 'echo -e "#!/bin/sh\nfail2ban-server -xf start" > /etc/service/fail2ban/run' && \
    chmod +x /etc/service/fail2ban/run

# Clean image
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
