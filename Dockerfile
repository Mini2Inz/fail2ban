# Alpine Linux as a base image
FROM alpine

# Install dependencies
RUN apk update && apk add bash python2 geoip

# Install Fail2ban-ng
COPY . /fail2ban
RUN cd /fail2ban && python setup.py install
RUN rm -rf /fail2ban

# Set loglevel to DEBUG
RUN sed -i 's/^loglevel = INFO$/loglevel = DEBUG/' /etc/fail2ban/fail2ban.conf

# Start Fail2ban-ng
CMD fail2ban-server -xf start
