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
if [[ ! `uname` =~ "darwin" ]]; then
  git config --global core.editor "subl -n -w $@ >/dev/null 2>&1"
  echo 'export BUNDLER_EDITOR="subl $@ >/dev/null 2>&1 -a"' >> zshrc
else
  git config --global core.editor "'/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl' -n -w"
  bundler_editor="'/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl'"
  echo "export BUNDLER_EDITOR=\"${bundler_editor} -a\"" >> zshrc
fi


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


zsh ~/.zshrc

echo "👌  Carry on with git setup!"
