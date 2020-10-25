sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"

# Node
curl -sL https://deb.nodesource.com/setup_14.x | sudo -E bash -
sudo apt-get install -y nodejs

# Yarn
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list
sudo apt update && sudo apt install yarn

#Global eslint
yarn global add eslint

backup() {
  target=$1
  if [ -e "$target" ]; then           # Does the config file already exist?
    if [ ! -L "$target" ]; then       # as a pure file?
      mv "$target" "$target.backup"   # Then backup it
      echo "-----> Moved your old $target config file to $target.backup"
    fi
  fi
}

#!/bin/zsh
for name in *; do
  if [ ! -d "$name" ]; then
    target="$HOME/.$name"
    if [[ ! "$name" =~ '\.sh$' ]] && [ "$name" != 'README.md' ] && [[ ! "$name" =~ '\.sublime-settings$' ]]; then
      backup $target

      if [ ! -e "$target" ]; then
        echo "-----> Symlinking your new $target"
        ln -s "$PWD/$name" "$target"
      fi
    fi
  fi
done

REGULAR="\\033[0;39m"
YELLOW="\\033[1;33m"
GREEN="\\033[1;32m"

# zsh plugins
CURRENT_DIR=`pwd`
ZSH_PLUGINS_DIR="$HOME/.oh-my-zsh/custom/plugins"
mkdir -p "$ZSH_PLUGINS_DIR" && cd "$ZSH_PLUGINS_DIR"
if [ ! -d "$ZSH_PLUGINS_DIR/zsh-syntax-highlighting" ]; then
  echo "-----> Installing zsh plugin 'zsh-syntax-highlighting'..."
  git clone git://github.com/zsh-users/zsh-syntax-highlighting.git
fi
cd "$CURRENT_DIR"

setopt nocasematch

git config --global core.editor "code --wait"

zsh ~/.zshrc

git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions


# Install Fira Code font
fonts_dir="${HOME}/.local/share/fonts"
if [ ! -d "${fonts_dir}" ]; then
    echo "mkdir -p $fonts_dir"
    mkdir -p "${fonts_dir}"
else
    echo "Found fonts dir $fonts_dir"
fi

# install xclip
apt-get install xclip

for type in Bold Light Medium Regular Retina; do
    file_path="${HOME}/.local/share/fonts/FiraCode-${type}.ttf"
    file_url="https://github.com/tonsky/FiraCode/blob/master/distr/ttf/FiraCode-${type}.ttf?raw=true"
    if [ ! -e "${file_path}" ]; then
        echo "wget -O $file_path $file_url"
        wget -O "${file_path}" "${file_url}"
    else
  echo "Found existing file $file_path"
    fi;
done

echo "fc-cache -f"
fc-cache -f

# Sublime Text
# if [[ ! `uname` =~ "darwin" ]]; then
#   SUBL_PATH=~/.config/sublime-text-3
# else
#   SUBL_PATH=~/Library/Application\ Support/Sublime\ Text\ 3
# fi
# mkdir -p $SUBL_PATH/Packages/User $SUBL_PATH/Installed\ Packages
# backup "$SUBL_PATH/Packages/User/Preferences.sublime-settings"
# curl -k https://sublime.wbond.net/Package%20Control.sublime-package > $SUBL_PATH/Installed\ Packages/Package\ Control.sublime-package
# ln -s $PWD/Preferences.sublime-settings $SUBL_PATH/Packages/User/Preferences.sublime-settings
# ln -s $PWD/Package\ Control.sublime-settings $SUBL_PATH/Packages/User/Package\ Control.sublime-settings
# ln -s $PWD/SublimeLinter.sublime-settings $SUBL_PATH/Packages/User/SublimeLinter.sublime-settings

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
# Docker-compose
curl -L "https://github.com/docker/compose/releases/download/1.25.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
sudo usermod -aG docker ${USER}
su -s ${USER}
sudo curl -L https://raw.githubusercontent.com/docker/compose/1.26.0/contrib/completion/bash/docker-compose -o /etc/bash_completion.d/docker-compose



# Google Cloud
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get install apt-transport-https ca-certificates gnupg
sudo apt-get update && sudo apt-get install google-cloud-sdk
sudo apt-get install google-cloud-sdk-app-engine-java
gcloud init
gcloud components install kubectl
source <(kubectl completion zsh)
echo 'alias k=kubectl' >>~/.zshrc
echo 'complete -F __start_kubectl k' >>~/.zshrc

# # Folder structure
mkdir -p ~/Code/BjMrq/Active
mkdir -p ~/Code/BjMrq/Archive
mkdir -p ~/Code/BjMrq/Boilerplates
mkdir -p ~/Code/BjMrq/NPM
mkdir -p ~/Code/Notebooks
mkdir -p ~/Code/Sandboxes
mkdir -p ~/Code/Softwares\&Drivers
mkdir -p ~/Code/BjMrq/Dockerfiles

echo "👌  Carry on with git setup!"
