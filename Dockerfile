# Alpine Linux as a base image
FROM alpine

# Install dependencies
RUN apk update && \
    apk add bash python2 geoip && \
    rm -rf /var/cache/apk/*

# Install Fail2ban-ng
COPY . /fail2ban
RUN cd /fail2ban && python setup.py install
RUN rm -rf /fail2ban

# Set loglevel to DEBUG
RUN sed -i 's/^loglevel = INFO$/loglevel = DEBUG/' /etc/fail2ban/fail2ban.conf

# Set list of hosts
ARG HOSTS=
# RUN sed -i "s/^sharehosts =$/sharehosts = $HOSTS/" /etc/fail2ban/fail2ban.conf
RUN for host in $HOSTS; do echo $host >> /etc/fail2ban/hosts; done

# Start Fail2ban-ng
CMD fail2ban-server -xf start
