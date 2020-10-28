sudo apt install -y git zsh curl jq 
apt-transport-https
sudo snap install hub --classic

mkdir -p ~/.ssh && ssh-keygen -t ed25519 -o -a 100 -f ~/.ssh/id_ed25519 -C "bmarquiscom@gmail.com"

echo "Add the following to github ssh keys"
cat ~/.ssh/id_ed25519.pub

echo "Type in your first and last name (no accent or special characters - e.g. 'ç'): "
read full_name

echo "Type in your email address (the one used for your GitHub account): "
read email

git config --global user.email $email
git config --global user.name $full_name
git config --global init.defaultBranch main

git add .
git commit --message "My identity for @lewagon in the gitconfig"
git push origin master

git remote add upstream git@github.com:lewagon/dotfiles.git

echo "👌 Awesome, all set."
