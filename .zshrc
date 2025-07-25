export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"
plugins=(git)

source $ZSH/oh-my-zsh.sh

alias vim='nvim'
alias dr='dotnet run'
alias db='dotnet build'
alias gs='git status'
alias gd="git diff --output-indicator-new=' ' --output-indicator-old=' '"
alias gl='git log --graph --all --pretty=format:"%C(magenta)%h %C(white) %an  %ar%C(blue)  %D%n%s%n"'
alias tmux-sessionizer="~/personal/.dotfiles/scripts/tmux-sessionizer"
alias luamake='~/lua-language-server/3rd/luamake/luamake'
alias dotfiles="cd ~/personal/.dotfiles"

# Environment Variables

# Set up tool-specific roots
export GOROOT="/usr/local/go"
export GOPATH="$HOME/go"

# Prepend development tool paths
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:/usr/local/bin/node:$GOROOT/bin:$GOPATH/bin:$PATH"
export PATH=/opt/zig:$PATH
export PATH="$PATH:/home/elijahkx/.dotnet/tools"
export PATH="$HOME/vcpkg:$PATH"
export VCPKG_ROOT="$HOME/vcpkg"
export DOTNET_ROOT=$HOME/.dotnet
export PATH=$HOME/.dotnet:$PATH

export http_proxy=http://192.168.1.6:808
export https_proxy=http://192.168.1.6:808
