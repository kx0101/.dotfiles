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

# Key bindings
# Ctrl+W deletes the previous word (word-by-word)
bindkey '^W' backward-kill-word

# Environment Variables

export GOOSE_PROVIDER="ollama"
export GOOSE_MODEL="qwen3-coder:30b"
export GOOSE_TELEMETRY_ENABLED="false"
export GOOSE_CLI_THEME="dark"
export GOOSE_MOIM_MESSAGE_TEXT="For normal chat responses, use plain text only. Never use Markdown formatting. Do not use headings, bullets, numbered lists, bold text, tables, or fenced code blocks unless I explicitly ask for Markdown or source code requires it. Do not start response lines with #, -, *, or numbered-list markers. Prefer short plain paragraphs."

# Cross-platform tool roots and paths
export GOPATH="$HOME/go"
export VCPKG_ROOT="$HOME/vcpkg"
export DOTNET_ROOT="$HOME/.dotnet"

export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$HOME/.local/npm/bin:$GOPATH/bin:$PATH"
export PATH="$HOME/vcpkg:$PATH"
export PATH="$HOME/.dotnet:$HOME/.dotnet/tools:$PATH"

case "$(uname -s)" in
    Darwin)
        # Homebrew (Apple Silicon) puts go/node/zig and friends on PATH
        if [ -x /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        # postgresql@16 is keg-only; put psql/pg_ctl on PATH when present
        if [ -d /opt/homebrew/opt/postgresql@16/bin ]; then
            export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
        fi
        ;;
    *)
        # Linux
        export GOROOT="/usr/local/go"
        export PATH="$GOROOT/bin:/usr/local/bin/node:/opt/zig:$PATH"

        # Home/work network proxy (Linux box only)
        export http_proxy=http://192.168.1.6:808
        export https_proxy=http://192.168.1.6:808
        ;;
esac
