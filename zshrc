# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

ZSH=$HOME/.oh-my-zsh

# You can change the theme with another one:
#   https://github.com/robbyrussell/oh-my-zsh/wiki/themes
# ZSH_THEME="robbyrussell"
ZSH_THEME="powerlevel10k/powerlevel10k"

plugins=(git gitfast terraform last-working-dir common-aliases zsh-syntax-highlighting history-substring-search zsh-autosuggestions)

export ENABLE_CORRECTION="false"

# Prevent Homebrew from reporting - https://github.com/Homebrew/brew/blob/master/share/doc/homebrew/Analytics.md
export HOMEBREW_NO_ANALYTICS=1

# Terraform
# export TF_LOG=TRACE

# Actually load Oh-My-Zsh
source "${ZSH}/oh-my-zsh.sh"
unalias rm # No interactive rm by default (brought by plugins/common-aliases)

#Sonar 
export SONAR_TOKEN=664ceea5654679ad50871cc9e5d158c736c3a7ae


# Volata environment manager for node and yarn

# Android SDK
export ANDROID_HOME=$HOME/Android/Sdk
export JAVA_HOME=$HOME/code/Softwares\&Drivers/android-studio/jre
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools

# ELIXIR
# ERL_LIBS=$HOME/lib/erlang/lib
export ERL_AFLAGS="-kernel shell_history enabled"

# $(yarn global bin)
# PATH
export PATH="./bin:./node_modules/.bin:/usr/local/sbin:/home/bjmrq/.local/bin:${PATH}"
# Store your own aliases in the ~/.aliases file and load the here.
[[ -f "$HOME/.aliases" ]] && source "$HOME/.aliases"

# Encoding stuff for the terminal
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export BUNDLER_EDITOR="code $@ >/dev/null 2>&1 -a"
export BUNDLER_EDITOR="code $@ >/dev/null 2>&1 -a"
export BUNDLER_EDITOR="code $@ >/dev/null 2>&1 -a"

export RUST_BACKTRACE=1

CASE_SENSITIVE="false"

# Was needed to fix docker force recreate
export LD_LIBRARY_PATH="/usr/local/lib"

# tabtab source for packages
# uninstall by removing these lines
[[ -f ~/.config/tabtab/__tabtab.zsh ]] && . ~/.config/tabtab/__tabtab.zsh || true
# . <(denon --completion)

autoload -U +X bashcompinit && bashcompinit
complete -o nospace -C /usr/bin/terraform terraform

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

export SPOCKEE_ROOT="/home/bjmrq/code/BjMrq/Active/Spockee"
# export SPOCKEE_ROOT="/home/bjmrq/code/BjMrq/Active/spockee-install"
export SPOCKEE_TEST="/home/bjmrq/code/BjMrq/Active/spockee-install"

# ARCHIVE
#KUBCTL
# [[ /usr/local/bin/kubectl ]] && source <(kubectl completion zsh)
# export BUNDLER_EDITOR="code $@ >/dev/null 2>&1 -a"
# complete -F __start_kubectl k

#Platformsh
# BEGIN SNIPPET: Platform.sh CLI configuration
# HOME=${HOME:-'/home/bjmrq'}
# export PATH="$HOME/"'.platformsh/bin':"$PATH"
# if [ -f "$HOME/"'.platformsh/shell-config.rc' ]; then . "$HOME/"'.platformsh/shell-config.rc'; fi # END SNIPPET

# Deno
# export DENO_INSTALL="/home/bjmrq/.deno"

# Load rbenv if installed
# export PATH="${HOME}/.rbenv/bin:${PATH}"
# type -a rbenv > /dev/null && eval "$(rbenv init -)"

# Node version Manager 
# export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
# [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" # This loads nvm

export VOLTA_HOME="$HOME/.volta"
export PATH="$VOLTA_HOME/bin:$PATH"
