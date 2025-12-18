--- idk what the f but this solves it for now...
local old_notify = vim.notify
vim.notify = function(msg, log_level, opts)
    if msg:match("volar is deprecated") or msg:match("vscoqtop is deprecated") then
        return
    end

    return old_notify(msg, log_level, opts)
end

require("kx0101.remap")
require("kx0101.set")
