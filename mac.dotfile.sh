/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

### Install
# Apps
brew install --cask brave-browser spotify

# Utils
brew install --cask dockmate keybase rectangle bartender

xcode-select --install

# Coding
brew install --cask iterm2 zsh visual-studio-code git volta
brew install docker --cask

# Office
brew install slack

### Set up
# Node
volta install node@16
volta install yarn
yarn global add npm-ls-scripts
# zsh
zsh ~/.zshrc

### Create simlinks

#!/bin/zsh
backup() {
  target=$1
  if [ -e "$target" ]; then           # Does the config file already exist?
    if [ ! -L "$target" ]; then       # as a pure file?
      mv "$target" "$target.backup"   # Then backup it
      echo "-----> Moved your old $target config file to $target.backup"
    fi
  fi
}

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


mkdir -p ~/Code/CoveMB/Active
mkdir -p ~/Code/CoveMB/Archive
mkdir -p ~/Code/CoveMB/Boilerplates
mkdir -p ~/Code/CoveMB/NPM
mkdir -p ~/Code/Notebooks
mkdir -p ~/Code/Sandboxes
mkdir -p ~/Code/Softwares\&Drivers
mkdir -p ~/Code/CoveMB/Dockerfiles