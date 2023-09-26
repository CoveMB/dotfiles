# Some deps
sudo apt install -y curl jq xclip gnome-tweaks

# Install Volta that will install and manage node and yarn and their versions
curl https://get.volta.sh | bash
volta install node
volta install yarn

sudo apt-get install build-essential
sudo npm install -g node-gyp
sudo apt install shotwell



backup() {
  target=$1
  if [ -e "$target" ]; then           # Does the config file already exist?
    if [ ! -L "$target" ]; then       # as a pure file?
      mv "$target" "$target.backup"   # Then backup it
      echo "-----> Moved your old $target config file to $target.backup"
    fi
  fi
}

# Create simlinks

#!/bin/zsh
for name in *; do
  if [ ! -d "$name" ]; then
    target="$HOME/.$name"
    if [[ ! "$name" =~ '\.sh$' ]] && [[ "$name" != 'README.md' ]]; then
      backup $target

      echo $target
      if [ ! -e "$target" ]; then
        echo "-----> Symlinking your new $target"
        ln -s "$PWD/$name" "$target"
      fi
    fi
  fi
done

ln -s "$PWD/.p10k.zsh" "~/"

# REGULAR="\\033[0;39m"
# YELLOW="\\033[1;33m"
# GREEN="\\033[1;32m"

# setopt nocasematch


# ZSH
sudo apt install -y zsh
chsh -s $(which zsh)
zsh ~/.zshrc

CURRENT_DIR=`pwd`
ZSH_PLUGINS_DIR="$HOME/.oh-my-zsh/custom/plugins"
ZSH_THEMES_DIR="$HOME/.oh-my-zsh/custom/themes"
mkdir -p "$ZSH_PLUGINS_DIR" && mkdir -p "$ZSH_THEMES_DIR" 
if [ ! -d "$ZSH_PLUGINS_DIR/zsh-syntax-highlighting" ]; then
  cd "$ZSH_PLUGINS_DIR"
  echo "-----> Installing zsh plugin 'zsh-syntax-highlighting'..."
  git clone git://github.com/zsh-users/zsh-syntax-highlighting.git
  cd "$HOME"
fi
if [ ! -d "$ZSH_PLUGINS_DIR/zsh-autosuggestions" ]; then
  cd "$ZSH_PLUGINS_DIR"
  echo "-----> Installing zsh plugin 'zsh-autosuggestions'..."
  git clone git://github.com/zsh-users/zsh-autosuggestions.git
  cd "$HOME"
fi
if [ ! -d "$ZSH_THEMES_DIR/powerlevel10k" ]; then
  echo "-----> Installing zsh plugin 'powerlevel10k'..."
  git clone --depth=1 https://github.com/romkatv/powerlevel10k.git
  cd "$HOME"
fi



# Install Fira Code font
fonts_dir="${HOME}/.local/share/fonts"
if [ ! -d "${fonts_dir}" ]; then
    echo "mkdir -p $fonts_dir"
    mkdir -p "${fonts_dir}"
else
    echo "Found fonts dir $fonts_dir"
fi

for type in Bold Light Medium Regular Retina; do
    file_path="${HOME}/.local/share/fonts/FiraCode-${type}.ttf"
    file_url="https://github.com/tonsky/FiraCode/blob/master/distr/ttf/FiraCode-${type}.ttf?raw=true"
    if [ ! -e "${file_path}" ]; then
        echo "wget -O $file_path $file_url"
        curl -O "${file_path}" "${file_url}"
    else
  echo "Found existing file $file_path"
    fi;
done

# echo "fc-cache -f"
# fc-cache -f

# Docker
# curl -fsSL https://get.docker.com -o get-docker.sh | sh get-docker.sh

# # Docker-compose
# curl -L "https://github.com/docker/compose/releases/download/1.26.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
# chmod +x /usr/local/bin/docker-compose
# usermod -aG docker ${USER}
# su -s ${USER}
# curl -L https://raw.githubusercontent.com/docker/compose/1.26.0/contrib/completion/bash/docker-compose -o /etc/bash_completion.d/docker-compose

# Folder structure
mkdir -p ~/Code/CoveMB/Active
mkdir -p ~/Code/CoveMB/Archive
mkdir -p ~/Code/CoveMB/Boilerplates
mkdir -p ~/Code/CoveMB/NPM
mkdir -p ~/Code/Notebooks
mkdir -p ~/Code/Sandboxes
mkdir -p ~/Code/Softwares\&Drivers
mkdir -p ~/Code/CoveMB/Dockerfiles

echo "👌  Carry on with git setup!"


# # ARCHIVE 
# # Google Cloud
# # echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
# # sudo apt-get install apt-transport-https ca-certificates gnupg
# # sudo apt-get update && sudo apt-get install google-cloud-sdk
# # sudo apt-get install google-cloud-sdk-app-engine-java
# # gcloud init
# # gcloud components install kubectl
# # source <(kubectl completion zsh)
# # echo 'alias k=kubectl' >>~/.zshrc
# # echo 'complete -F __start_kubectl k' >>~/.zshrc

# # # Node Version Manager
# # curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.36.0/install.sh | bash
# # nvm install node

# # Yarn
# # curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
# # echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
# # sudo apt update && sudo apt install --no-install-recommends yarn