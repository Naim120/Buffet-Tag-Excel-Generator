#!/bin/bash

# Download cloudflared
echo "Downloading cloudflared..."
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install
echo "Installing cloudflared..."
sudo dpkg -i cloudflared-linux-amd64.deb

# Cleanup
rm cloudflared-linux-amd64.deb

echo "----------------------------------------------------------------"
echo "Cloudflared installed successfully!"
echo "Please follow the instructions in 'cloudflare_tunnel_guide.md'"
echo "to authenticate and create your tunnel."
echo "----------------------------------------------------------------"
