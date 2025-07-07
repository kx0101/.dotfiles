return {
    {
        "neovim/nvim-lspconfig",
        opts = {
            servers = {
                move_analyzer = {
                    cmd = { os.getenv("HOME") .. "/.cargo/bin/move-analyzer" },
                    filetypes = { "move" },
                    root_dir = require("lspconfig.util").root_pattern("Move.toml", ".git"),
                },
            },
        },
    },
    {
        "yanganto/move.vim",
        branch = "sui-move",
    },
}
