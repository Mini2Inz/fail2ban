FROM python

# Install Fail2ban-ng
COPY . /fail2ban
RUN cd /fail2ban && python setup.py install
RUN rm -rf /fail2ban

# Set loglevel to DEBUG
RUN sed -i 's/^loglevel = INFO$/loglevel = DEBUG/' /etc/fail2ban/fail2ban.conf

# Update Debian's package list
RUN apt-get update

# Install GeoIP database
RUN apt-get install geoip-database

# Start Fail2ban-ng
CMD fail2ban-server -xf start
