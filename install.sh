#!/usr/bin/env bash

# Clone repository to where install.sh is
git clone https://github.com/zereaykut/Hyprland-Overview.git .

# Create install directory
mkdir -p ~/.config/hyprland-overview/

# Copy required files
cp -rf ./Hyprland-Overview/* ~/.config/hyprland-overview/.

# Delete repository files
rm -rf ./Hyprland-Overview/

# Move into application directory
cd ~/.config/hyprland-overview/

# Install python packages to virtual python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

