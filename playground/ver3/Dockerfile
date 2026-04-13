FROM build-base:latest

# Copy the firefox.tar.xz file into the container
COPY firefox.tar.xz /tmp/firefox.tar.xz

# Set DEBIAN_FRONTEND to noninteractive for package installations
ENV DEBIAN_FRONTEND=noninteractive

# Install desktop environment and XRDP
RUN apt-get install -y lubuntu-desktop xrdp && \
    adduser xrdp ssl-cert && \
    echo "Lubuntu desktop and XRDP installed"

# Create a user with sudo privileges
RUN useradd -m -s /bin/bash testuser && \
    echo "testuser:1234" | chpasswd && \
    usermod -aG sudo testuser && \
    echo "User testuser created"

# Expose port for XRDP
EXPOSE 3389

# Start services
CMD service dbus start && \
    /usr/lib/systemd/systemd-logind & \
    service xrdp start && \
    echo "Services started" && \
    /bin/bash